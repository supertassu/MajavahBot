from majavahbot.api.database import ReplicaDatabase
from majavahbot.api.manual_run import confirm_edit
from majavahbot.tasks import Task, task_registry
from pywikibot import Page, PageRelatedError
from functools import lru_cache
import mwparserfromhell
import traceback
import datetime
import re


MOVED_REGEX = re.compile(r"(?:[a-zA-Z0-9 .]+ )?moved (?:page )?\[\[([^]]+)]] to \[\[([^]]+)]]")


QUERY = """
select
    page_id,
    page_title
from page
where
    page_namespace = 1
    and page_title not in (
        select pl_title
        from pagelinks
        where pl_from = 65539331 -- User:MajavahBot/DYK blurb not found
        and pl_namespace = 1
    )
    and exists (
        select 1
        from categorylinks
        where cl_from = page_id
        and cl_to = "Pages_with_a_missing_DYK_entry"
    )
    and exists (
        select 1
        from templatelinks
        where tl_from = page_id
    )
order by page_title
limit 100;
"""


class DykEntryTalkTask(Task):
    def __init__(self, number, name, site, family):
        super().__init__(number, name, site, family)
        self.supports_manual_run = True
        self.register_task_configuration("User:MajavahBot/DYK options")

    @lru_cache()
    def get_archive_page(self, year, month):
        archive_page_name = "Wikipedia:Recent additions/" + str(year) + "/" + str(month)
        try:
            return self.get_mediawiki_api().get_page(archive_page_name).get()
        except PageRelatedError:
            print("Failed getting for page", year, month)
            traceback.print_exc()
            return ''

    def get_entry_for_page(self, year, month, day, page: Page):
        # for weird syntax
        if month.endswith(','):
            month = month[:-1]
        if day.endswith(','):
            day = day[:-1]
        if str(month).isdecimal() and not str(day).isdecimal():
            # swap out month and day if necessary
            month, day = day, month
        if day > 2000:
            day, year = year, day

        search_entries = ["'''[[" + page.title(with_ns=False).lower()]

        for revision in page.revisions():
            result = MOVED_REGEX.match(revision.comment)
            if result is not None:
                page_name = result.group(1)
                this_page = self.get_mediawiki_api().get_page(page_name)
                search_entries.append("'''[[" + this_page.title(with_ns=False).lower())
        print(search_entries)

        archive_text = self.get_archive_page(year, month)
        parsed_archive = mwparserfromhell.parse(archive_text)
        archive_sections = parsed_archive.get_sections(levels=[3])

        for section in archive_sections:
            for row in str(section).split("\n"):
                row_lower = row.lower()
                for search_entry in search_entries:
                    if search_entry in row_lower:
                        text = row[1:]  # remove * from beginning
                        # you could check dates here, if wanted - please don't for now, see BRFA for more details
                        return text
        return False

    def process_page(self, page: Page):
        page_text = page.get(force=True)
        parsed = mwparserfromhell.parse(page_text)

        year = None
        month = None
        day = None
        entry = None

        for template in parsed.filter_templates():
            if (template.name.matches("Dyktalk") or template.name.matches("DYK talk")) and not template.has('entry'):
                if year is None:
                    if (not template.has(1)) or (not template.has(2)):
                        print("Skipping {{DYK talk}} page", page, ", no date found")
                        continue

                    print("*", page.title(), template.get(2), template.get(1))
                    year = template.get(2).value.strip()
                    day, month = template.get(1).value.strip().split(" ")

                if entry is None:
                    entry = self.get_entry_for_page(year, month, day, page)

                if entry:
                    print("Adding entry", entry, "to {{DYK talk}}")
                    template.add("entry", entry)
            elif (template.name.matches('ArticleHistory') or template.name.matches('Article history')) and not template.has('dykentry'):
                if year is None:
                    if not template.has('dykdate'):
                        print("Skipping {{ArticleHistory}} on page", page, ", no date found")
                        continue
                    date = template.get('dykdate').value.strip()
                    print("*", page.title(), date)

                    if ' ' in date:
                        # monthName YYYY
                        if date.count(' ') == 1:
                            date = '1 ' + date
                        day, month, year = date.split(' ')[:3]
                    elif '-' in date:
                        year, month, day = date.split('-')[:3]
                        month = datetime.date(1900, int(month), 1).strftime('%B')
                    else:
                        print("Skipping {{ArticleHistory}} on page", page, ", can't parse date", date)
                        continue
                print(page.title(), year, month, day)

                if entry is None:
                    entry = self.get_entry_for_page(year, month, day, page)

                if entry:
                    print("Adding entry", entry, "to {{ArticleHistory}}")
                    template.add("dykentry", entry, before="dykdate")

        if entry:
            new_text = str(parsed)
            if new_text != page.text and self.should_edit() and (not self.is_manual_run or confirm_edit()):
                self.get_mediawiki_api().get_site().login()
                page.text = str(parsed)

                page.save(self.get_task_configuration('missing_blurb_edit_summary'), botflag=self.should_use_bot_flag())
                self.record_trial_edit()
                return True
        return False

    def run(self):
        self.merge_task_configuration(
            missing_blurb_enable=True,

            missing_blurb_edit_summary="[[WP:Bots/Requests for approval/MajavahBot 4|Bot]]: Fill missing DYK blurb",

            missing_blurb_log_page="User:MajavahBot/DYK blurb not found",
            missing_blurb_log_summary="[[WP:Bots/Requests for approval/MajavahBot 4|Bot]]: Update log for DYK blurbs that were not found"
        )

        if self.get_task_configuration("missing_blurb_enable") is not True:
            print("Disabled in configuration")
            return

        api = self.get_mediawiki_api()
        site = api.get_site()

        log_page = api.get_page(self.get_task_configuration("missing_blurb_log_page"))
        log_counter = 0

        replicadb = ReplicaDatabase(site.dbName())

        replag = replicadb.get_replag()
        if replag > 10:
            print("Replag is over 10 seconds, not processing! (" + str(replag) + ")")
            return

        results = replicadb.get_all(QUERY)
        print("-- Got %s pages" % (str(len(results))))
        for page_from_db in results:
            if not self.should_edit():
                print("Can't edit anymore, done")
                break

            page_id = page_from_db[0]
            page_name = page_from_db[1].decode('utf-8')

            page = api.get_page("Talk:" + page_name)
            assert page.pageid == page_id

            if self.process_page(page):
                continue
            # :( not found :(

            if page.title(as_link=True) in log_page.text:
                print("found; ", page.title())
                continue

            # print("\n* " + page.title(as_link=True) + ". Checked ~~~~~")
            log_page.text += "\n* " + page.title(as_link=True) + ". Checked ~~~~~"

            log_counter += 1
            if log_counter > 25:
                log_page.save(self.get_task_configuration("missing_blurb_log_summary"), botflag=self.should_use_bot_flag())
                log_counter = 0
        if log_counter > 0:
            log_page.save(self.get_task_configuration("missing_blurb_log_summary"), botflag=self.should_use_bot_flag())


task_registry.add_task(DykEntryTalkTask(6, "DYK entry filler", "en", "wikipedia"))
