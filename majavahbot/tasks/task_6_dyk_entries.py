from majavahbot.api.database import ReplicaDatabase
from majavahbot.api.manual_run import confirm_edit
from majavahbot.tasks import Task, task_registry
from pywikibot import Page, Category, pagegenerators
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
        and cl_to = "Pages_using_DYK_talk_with_a_missing_entry"
    )
limit 50;
"""


class DykEntryTalkTask(Task):
    def __init__(self, number, name, site, family):
        super().__init__(number, name, site, family)
        self.supports_manual_run = True
        self.register_task_configuration("User:MajavahBot/DYK options")

    def get_archive_page(self, year, month):
        archive_page_name = "Wikipedia:Recent additions/" + str(year) + "/" + str(month)
        return self.get_mediawiki_api().get_page(archive_page_name)

    def get_archive_section(self, year, month, day, page: Page):
        search_heading = str(day) + " " + str(month) + " " + str(year)
        search_entry = "'''[[" + page.title(with_ns=False)

        page = self.get_archive_page(year, month)
        archive_text = page.get()
        parsed_archive = mwparserfromhell.parse(archive_text)
        archive_sections = parsed_archive.get_sections(levels=[3])

        for section in archive_sections:
            header = section.filter_headings()[0]

            if len(section.filter_headings()) != 1:
                raise Exception(page.title() + " has weird syntax: " + str(section.filter_headings()) + " in one section")

            for row in str(section).split("\n"):
                if search_entry in row:
                    text = row[1:]  # remove * from beginning

                    if search_heading in header:
                        return text, None

                    date_match = DATE_REGEX.search(str(header))
                    print(date_match, str(header))
                    if date_match:
                        return text, date_match.group(1)

                    return text, None

    def get_entry(self, section, page: Page):
        looking_for = "'''[[" + page.title(with_ns=False)
        for row in str(section).split("\n"):
            if looking_for in row:
                return row[1:]  # remove * from beginning

    def process_page(self, page: Page):
        page_text = page.get(force=True)
        parsed = mwparserfromhell.parse(page_text)
        for template in parsed.filter_templates():
            if template.name.matches("Dyktalk") or template.name.matches("DYK talk"):
                year = template.get(2)
                day, month = template.get(1).split(" ")
                entry_data = self.get_archive_section(year, month, day, page)

                if entry_data:
                    summary = "missing_blurb_edit_summary"
                    entry, date = entry_data
                    template.add("entry", entry)

                    if date:
                        template.add(1, date)
                        summary = "missing_blurb_corrected_date_edit_summary"
                    print(page.title(as_link=True), str(template))

                    if self.should_edit() and (not self.is_manual_run or confirm_edit()):
                        self.get_mediawiki_api().get_site().login()
                        page.text = str(parsed)

                        page.save(self.get_task_configuration(summary), botflag=self.should_use_bot_flag())
                        self.record_trial_edit()
                        return True
        return False

    def run(self):
        self.merge_task_configuration(
            missing_blurb_enable=True,

            missing_blurb_category="Pages using DYK talk with a missing entry",
            missing_blurb_edit_summary="Bot: Fill missing DYK blurb",
            missing_blurb_corrected_date_edit_summary="Bot: Correct DYK appearance date and fill out blurb",

            missing_blurb_log_page="User:MajavahBot/DYK blurb not found",
            missing_blurb_log_summary="Bot: Update log for DYK blurbs that were not found"
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
