from majavahbot.api.manual_run import confirm_edit
from majavahbot.tasks import Task, task_registry
from pywikibot import Page, Category, pagegenerators
import mwparserfromhell


class DykEntryTalkTask(Task):
    def __init__(self, number, name, site, family):
        super().__init__(number, name, site, family)
        self.supports_manual_run = True
        self.register_task_configuration("User:MajavahBot/DYK options")

    def get_archive_page(self, year, month):
        archive_page_name = "Wikipedia:Recent additions/" + str(year) + "/" + str(month)
        return self.get_mediawiki_api().get_page(archive_page_name)

    def get_archive_section(self, year, month, day):
        search_heading = str(day) + " " + str(month) + " " + str(year)

        page = self.get_archive_page(year, month)
        archive_text = page.get()
        parsed_archive = mwparserfromhell.parse(archive_text)
        archive_sections = parsed_archive.get_sections(levels=[3])

        for section in archive_sections:
            header = section.filter_headings()[0]
            if search_heading in header:
                return section

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
                section = self.get_archive_section(year, month, day)

                entry = self.get_entry(section, page)
                if entry:
                    template.add("entry", entry[1:])

                    if self.should_edit() and (not self.is_manual_run or confirm_edit()):
                        self.get_mediawiki_api().get_site().login()
                        page.text = str(parsed)

                        # page.save(self.get_task_configuration("missing_blurb_edit_summary"), botflag=self.should_use_bot_flag())
                        self.record_trial_edit()
                        return True
        return False

    def run(self):
        self.merge_task_configuration(
            missing_blurb_enable=True,

            missing_blurb_category="Pages using DYK talk with a missing entry",
            missing_blurb_edit_summary="Bot: Fill missing DYK blurb",

            missing_blurb_log_page="User:MajavahBot/DYK blurb not found",
            missing_blurb_log_summary="Bot: Update log for DYK blurbs that were not found"
        )

        if self.get_task_configuration("missing_blurb_enable") is not True:
            print("Disabled in configuration")
            return

        site = self.get_mediawiki_api().get_site()

        log_page = self.get_mediawiki_api().get_page(self.get_task_configuration("missing_blurb_log_page"))
        log_counter = 0

        category = Category(site, self.get_task_configuration("missing_blurb_category"))
        pages = category.articles()
        for page in pagegenerators.PreloadingGenerator(pages, 20):
            if self.process_page(page):
                continue
            # :( not found :(

            if page.title() in log_page.text:
                continue

            log_page.text += "\n* " + page.title(as_link=True) + ". Checked ~~~~~"

            log_counter += 1
            if log_counter > 25:
                # page.save(self.get_task_configuration("missing_blurb_log_summary"), botflag=self.should_use_bot_flag())
                log_counter = 0


task_registry.add_task(DykEntryTalkTask(6, "DYK entry filler", "en", "wikipedia"))
