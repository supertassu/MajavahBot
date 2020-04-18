from majavahbot.api import MediawikiApi, ReplicaDatabase, manual_run
from majavahbot.config import requested_articles_config_page
from majavahbot.tasks import Task, task_registry
from re import compile


ENTRY_REGEX = compile(r"\n:*\*+ ?([^\n]+)")
LOCAL_LINK_REGEX = compile(r"\[\[([^\:\]]+)\]\]")
EXISTING_PAGE_QUERY = "SELECT page_title FROM page WHERE page_namespace = 0 AND page_is_redirect = 0 AND page_title IN (%s)"


class FiwikiRequestedArticlesTask(Task):
    def __init__(self, number, name, site):
        super().__init__(number, name, site)
        self.register_task_configuration(requested_articles_config_page)
        self.supports_manual_run = True

    def process_page(self, page: str, api: MediawikiApi, replica: ReplicaDatabase):
        page = api.get_page(page)
        text = page.text
        entries = list(ENTRY_REGEX.finditer(text))
        requests = {}

        for entry in entries:
            entry_text = entry.group(1)
            first_link = LOCAL_LINK_REGEX.match(entry_text)

            entry_text_lower = entry_text.lower()
            if first_link and not any(term.lower() in entry_text_lower for term in self.get_task_configuration('keep_terms')):
                request_text = first_link.group(1).replace(" ", "_")
                if len(request_text) > 0:
                    request_text = request_text[0].capitalize() + request_text[1:]
                    requests[request_text] = entry.group(0)

        page_titles = requests.keys()
        format_strings = ','.join(['%s'] * len(page_titles))
        existing_pages = replica.execute(EXISTING_PAGE_QUERY % format_strings, tuple(page_titles))

        removed_entries = []
        new_text = text

        print("-- Found %s filled requests" % (str(len(existing_pages))))
        for existing_page in existing_pages:
            existing_page = existing_page[0].decode('utf-8')
            existing_page_entry = requests[existing_page]
            print("Request %s (%s)" % (existing_page, existing_page_entry.replace("\n", "")))
            if not self.is_manual_run or manual_run.confirm_with_enter():
                new_text = new_text.replace(existing_page_entry, '')
                removed_entries.append(existing_page)

        if len(removed_entries) > 0 and self.should_edit():
            removed_length = len(removed_entries)
            if text == new_text:
                raise RuntimeError("text == new_text but at least one entry should be removed")
            summary = 'Botti poisti ' + (
                (str(removed_length) + ' täytettyä artikkelitoivetta') if removed_length > 3 else
                ('seuraavat täytetyt artikkelitoiveet: [[' + ']], [['.join(removed_entries) + ']]')
            )

            print("Poistetaan %s toivetta sivulta %s" % (str(removed_length), page.title(as_link=True)))
            if self.should_edit() and not self.is_manual_run or manual_run.confirm_edit():
                page.text = new_text
                page.save(summary, botflag=self.should_use_bot_flag())
                self.record_trial_edit()

    def run(self):
        replicadb = ReplicaDatabase("fiwiki")
        replicadb.request()

        api = self.get_mediawiki_api()

        if self.get_task_configuration("run") is not True:
            print("Disabled in configuration")
            return

        for page in self.get_task_configuration('pages'):
            print()
            print("--- Processing page", page)
            self.process_page(page, api, replicadb)

        replicadb.close()


task_registry.add_task(FiwikiRequestedArticlesTask(2, 'Requested articles clerk', 'fi'))
