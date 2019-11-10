from majavahbot.api import MediawikiApi, get_mediawiki_api
from majavahbot.tasks import Task, task_registry
from majavahbot.config import effpr_page_name, effpr_filter_log_format, effpr_section_header_regex, \
    effpr_page_title_regex, effpr_page_title_wrong_format_regexes, effpr_closed_strings
from dateutil import parser
from re import search, sub, compile
import datetime


class EffpTask(Task):
    """
    Task 1 patrols the Edit Filter false positive report page.

    Subtasks are:
     a) If page name is missing, fill it in if possible, notify otherwise
     b) If page name is wrong in a very obvious way (eg. lowercase), correct it
     c) If filter is private, add a notification about that
     d) If user is blocked, add a notification about that
    """

    def locate_page_name(self, section):
        """Used to locate page name from a section"""
        results = search(section, effpr_page_title_regex)

        if results is None:
            return None

        page_name = results.group(1)

        if page_name == 'Page not specified':
            return None
        return page_name

    def is_closed(self, section):
        return any(string.lower() in section.lower() for string in effpr_closed_strings)

    def process_new_report(self, section: str, user_name: str, api: MediawikiApi):
        """Used to process a new section added to the page"""
        page_title = self.locate_page_name(section)

        if not section.endswith("\n"):
            section += "\n"

        new_section = section
        edit_summary = []

        last_hit = api.get_last_abuse_filter_trigger(user_name)

        if last_hit is None:
            new_section += ":{{EFFP|n}} No filters triggered. ~~~~\n"
            edit_summary.append("Notify that no filters were triggered (task 1a)")

        # If filter was triggered more than 2 hours ago, assume it is not the one being reported
        if last_hit is not None:
            last_hit_timestamp = last_hit['timestamp']
            last_hit_datetime = parser.parse(last_hit_timestamp)
            if (datetime.datetime.now(tz=datetime.timezone.utc) - last_hit_datetime).total_seconds() > 3600 * 2:
                last_hit = None

        if last_hit is not None:
            last_hit_filter_id = last_hit['filter_id']
            last_hit_page_title = last_hit['title']

            # subtask a: if page title is missing, add it
            # subtask b: correct very obvious spelling mistakes in page titles (currently only case)
            page_title_missing = page_title is None
            page_title_obviously_wrong = False

            if last_hit_page_title != page_title and not page_title_missing:
                if last_hit_page_title is not None and page_title is not None:
                    if last_hit_page_title.lower() == page_title.lower():
                        page_title_obviously_wrong = True

                wrong_spelling = search(effpr_page_title_wrong_format_regexes, page_title)
                if wrong_spelling is not None:
                    if wrong_spelling.group(1).lower() == last_hit_page_title.lower():
                        page_title_obviously_wrong = True

            if page_title_missing or page_title_obviously_wrong:
                last_hit_filter_log = effpr_filter_log_format % api.get_page(last_hit_page_title).title(as_url=True)

                new_section = sub(
                    effpr_page_title_regex,
                    ";Page you were editing\n: [[" + last_hit_page_title + "]] (<span class=\"plainlinks\">[" +
                    last_hit_filter_log + " filter log]</span>)\n",
                    new_section
                )

                if page_title_missing:
                    new_section += ":{{EFFP|n}} No affected page was specified, bot added last triggered page. ~~~~\n"
                    edit_summary.append("Add affected page name (task 1a)")
                elif page_title_obviously_wrong:
                    new_section += ":{{EFFP|n}} Bot corrected spelling or formatting of affected page title ~~~~\n"
                    edit_summary.append("Fix affected page name (task 1b)")
                else:
                    raise Exception

            # subtask c: notify if filter is private
            if api.is_filter_private(last_hit_filter_id):
                new_section += ":{{EFFP|p}} ~~~~\n"
                edit_summary.append("Add private filter notice (task 1c)")
        elif page_title is None:
            new_section += ":{{EFFP|n}} No filters triggered, page title not specified. ~~~~\n"
            edit_summary.append("Notify that no filters were triggered when a page title is not specified. (task 1a)")

        if new_section != section:
            return new_section, edit_summary
        return section, []

    def process_existing_report(self, section: str, user_name: str, api: MediawikiApi):
        """Used to process an existing section"""
        if not section.endswith("\n"):
            section += "\n"

        new_section = section
        edit_summary = []

        user = api.get_user(user_name)

        # subtask d: notify if blocked
        if user.isBlocked():
            blocked_by = user.getprops()['blockedby']
            new_section += ":{{EFFP|b|%s|%s}} ~~~~\n" % (user.username, blocked_by)
            edit_summary.append("Notify if user is blocked. (task 1d)")

        if new_section != section:
            return new_section, edit_summary
        return section, []

    def get_sections(self, page: str) -> tuple:
        """Parses a page and returns all sections in it"""
        section_header_pattern = compile(effpr_section_header_regex)
        sections = []

        matches = list(section_header_pattern.finditer(page))

        if len(matches) == 0:
            return '', []

        for i in range(len(matches)):
            match = matches[i]
            end = matches[i + 1].start() - 1 if i < (len(matches) - 1) else len(page)
            sections.append((match.group(1), page[match.start():end]))

        return page[:matches[0].start() - 1], sections

    def process_page(self, page: str, api: MediawikiApi):
        """Processes the EFFPR page"""
        page = api.get_page(page)
        page.get(force=True)

        rev_iterator = page.revisions(content=True, total=2)
        current_text = next(rev_iterator)['text']
        old_text = next(rev_iterator)['text']

        old_preface, old_sections = self.get_sections(old_text)
        current_preface, current_sections = self.get_sections(current_text)

        if len(old_sections) > len(current_sections):
            # assuming something was just archived or un-done, not doing anything
            return

        save = False
        summary = ''

        section_texts = []

        for i in range(len(current_sections)):
            section_user = current_sections[i][0]
            section_text = current_sections[i][1]

            if not self.is_closed(section_text):
                print("Processing section by", section_user)

                new_text = section_text
                new_summaries = []
                if i >= len(old_sections):
                    new_text, new_summaries = self.process_new_report(new_text, section_user, api)
                new_text, existing_summaries = self.process_existing_report(new_text, section_user, api)

                if new_text != section_text:
                    section_texts.append(new_text)
                    summary += section_user + ": " + ', '.join(new_summaries + existing_summaries) + ". "
                    save = True
            else:
                section_texts.append(section_text)

        if save:
            new_text = current_preface + "".join(section_texts)
            page.text = new_text
            page.save(summary)

    def run(self):
        api = get_mediawiki_api()

        # if change streams are available for that page, use it; otherwise just process it once
        try:
            stream = api.get_page_change_stream(effpr_page_name)
        except:
            self.process_page(effpr_page_name, api)
            return

        for _ in stream:
            self.process_page(effpr_page_name, api)
        print("the end")


task_registry.add_task(EffpTask(1, 'EFFP helper'))
