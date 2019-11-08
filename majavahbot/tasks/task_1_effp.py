from majavahbot.api import MediawikiApi, get_mediawiki_api
from majavahbot.tasks import Task, task_registry
from majavahbot.config import effpr_page_name, effpr_filter_log_format, effpr_page_title_regex
from dateutil import parser
from re import search, sub
import datetime


class EffpTask(Task):
    """
    Task 1 patrols the Edit Filter false positive report page.

    Subtasks are:
     a) If page name is missing, fill it in if possible, notify otherwise
     b) If filter is private, add a notification about that
    """

    """Used to locate page name from """

    def locate_page_name(self, section):
        results = search(section, effpr_page_title_regex)

        if results is None:
            return None

        page_name = results.group(1)

        if page_name == 'Page not specified':
            return None
        return results

    """Used to overall process a new section added to the page"""

    def process_new_report(self, section: str, user_name: str, api: MediawikiApi):
        page_title = self.locate_page_name(section)

        if not section.endswith("\n"):
            section += "\n"

        new_section = section
        edit_summary = []

        user = api.get_user(user_name)

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

            # subtask a: if page title is missing, add it
            if page_title is None:
                last_hit_page_title = last_hit['title']
                last_hit_filter_log = effpr_filter_log_format % api.get_page(last_hit_page_title).title(as_url=True)

                new_section = sub(
                    effpr_page_title_regex,
                    ";Page you were editing\n: [[" + last_hit_page_title + "]] (<span class=\"plainlinks\">[" +
                    last_hit_filter_log + " filter log]</span>)\n",
                    new_section
                )
                new_section += ":{{EFFP|n}} No affected page was specified, bot added last triggered page. ~~~~\n"
                edit_summary.append("Add affected page name (task 1a)")

            # subtask b: notify if filter is private
            if api.is_filter_private(last_hit_filter_id):
                new_section += ":{{EFFP|p}} ~~~~\n"
                edit_summary.append("Add private filter notice (task 1b)")
        elif page_title is None:
            new_section += ":{{EFFP|n}} No filters triggered, page title not specified. ~~~~\n"
            edit_summary.append("Notify that no filters were triggered when a page title is not specified. (task 1a)")

        if new_section != section:
            print("updating")
            # print("old section ", section)
            print("new section ", new_section)
            print("edit summary", ', '.join(edit_summary))
            return new_section, ', '.join(edit_summary)

        return None

    def run(self):
        api = get_mediawiki_api()

        # print(api.get_last_abuse_filter_trigger("Admin"))
        print(api.get_last_abuse_filter_trigger("Tyyppi"))

        sample_report = """
==Tyyppi==
;Username
: [[User:Tyyppi|Tyyppi]] ([[User talk:Tyyppi|talk]] '''·''' [[Special:Contribs/Tyyppi|contribs]]) (<span class="plainlinks">[//en.wikipedia.org/wiki/Special:AbuseLog?title=Special:AbuseLog&wpSearchUser=Tyyppi filter log]</span>)
;Page you were editing
: Page not specified
;Description
: 
;Date and time
: 14:34, 6 November 2019 (UTC)
;Comments
<!-- Please leave this area blank for now, but be prepared to answer questions left by reviewing editors. Thanks! -->
"""

        print(sample_report)
        print(self.process_new_report(sample_report, "Tyyppi", api))

        # foo bar
        if True:
            return

        page = api.get_page(effpr_page_name)
        stream = api.get_page_change_stream(effpr_page_name)
        if not page.exists():
            print("Page does not exist")
            return
        for change in stream:
            # refresh page data
            new_revision_id = change['revision']['new']
            user = change['user']
            page.get(force=True)
            print("change       ", change)
            print("change id    ", new_revision_id)
            print("new wiki text", page.text)
            print("revision     ", page.latest_revision)
            print("")
        print("the end")


task_registry.add_task(EffpTask(1, 'EFFP helper'))
