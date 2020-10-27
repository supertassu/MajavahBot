from majavahbot.api.database import ReplicaDatabase
from majavahbot.api.manual_run import confirm_edit
from majavahbot.tasks import Task, task_registry
from functools import lru_cache
from pywikibot import Page
import mwparserfromhell
import re


DATE_REGEX = re.compile(r"(\d+ [a-zA-Z]+) \d{4}")


QUERY = """
select
    page_id,
    page_title
from page
where
    page_namespace = 1
    and page_title not in (
        select 1
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
    and exists (
        select 1
        from templatelinks
        where tl_from = page_id
        and tl_namespace = 10
        and (tl_title = 'ArticleHistory' or tl_title = 'Article history')
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
        return self.get_mediawiki_api().get_page(archive_page_name).get()

    def get_entry_for_page(self, year, month, day, page: Page):
        search_entry = "'''[[" + page.title(with_ns=False)

        archive_text = self.get_archive_page(year, month)
        parsed_archive = mwparserfromhell.parse(archive_text)
        archive_sections = parsed_archive.get_sections(levels=[3])

        for section in archive_sections:
            for row in str(section).split("\n"):
                if search_entry in row:
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
            if template.name.matches("Dyktalk") or template.name.matches("DYK talk"):
                if year is None:
                    if not template.has(1):
                        print("Skipping {{DYK talk}} page", page, ", no date found")
                        continue

                    year = template.get(2)
                    day, month = template.get(1).split(" ")
                    if str(month).isdecimal() and not str(day).isdecimal():
                        # swap out month and day if necessary
                        month, day = day, month

                print(page.title(), year, month, day)

                if entry is None:
                    entry = self.get_entry_for_page(year, month, day, page)

                if entry:
                    template.add("entry", entry)
            elif template.name.matches('ArticleHistory') or template.name.matches('Article history'):
                if year is None:
                    if not template.has('dykdate'):
                        print("Skipping {{ArticleHistory}} on page", page, ", no date found")
                        continue
                    day, month, year = template.get('dykdate').split(' ')

                if entry is None:
                    entry = self.get_entry_for_page(day, month, year, page)

                if entry:
                    template.add("dykentry", entry)

        if entry:
            if self.should_edit() and (not self.is_manual_run or confirm_edit()):
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

            if page.title() in log_page.text:
                continue

            log_page.text += "\n* " + page.title(as_link=True) + ". Checked ~~~~~"

            log_counter += 1
            if log_counter > 25:
                log_page.save(self.get_task_configuration("missing_blurb_log_summary"), botflag=self.should_use_bot_flag())
                log_counter = 0
        if log_counter > 0:
            log_page.save(self.get_task_configuration("missing_blurb_log_summary"), botflag=self.should_use_bot_flag())


task_registry.add_task(DykEntryTalkTask(6, "DYK entry filler", "en", "wikipedia"))
