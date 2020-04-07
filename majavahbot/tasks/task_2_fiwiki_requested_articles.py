from majavahbot.api import MediawikiApi, ReplicaDatabase
from majavahbot.tasks import Task, task_registry
from re import compile


ENTRY_REGEX = compile(r"\n:*\*+ ?([^\n]+)")
LOCAL_LINK_REGEX = compile(r"\[\[([^\:\]]+)\]\]")
EXISTING_PAGE_QUERY = "SELECT page_title FROM page WHERE page_namespace = 0 AND page_is_redirect = 0 AND page_title IN (%s)"

# todo: add rest and move to config page
PAGES = ['Wikipedia:Artikkelitoiveet/Tekniikka']

# todo: move to a config page
BLACKLISTED_TERMS = [
    "<!-- keep -->",
    "luettelo",
    "punaiset linkit"
]


class FiwikiRequestedArticlesTask(Task):
    def process_page(self, page: str, api: MediawikiApi, replica: ReplicaDatabase):
        page = api.get_page(page)
        text = page.text
        entries = list(ENTRY_REGEX.finditer(text))
        requests = {}

        for entry in entries:
            entry_text = entry.group(1)
            first_link = LOCAL_LINK_REGEX.match(entry_text)
            if first_link and not any(term.lower() in entry_text.lower() for term in BLACKLISTED_TERMS):
                requests[first_link.group(1).replace(" ", "_")] = entry.group(0)

        page_titles = requests.keys()
        format_strings = ','.join(['%s'] * len(page_titles))
        existing_pages = replica.execute(EXISTING_PAGE_QUERY % format_strings, tuple(page_titles))

        removed_entries = []
        new_text = text

        for existing_page in existing_pages:
            existing_page = existing_page[0].decode('utf-8')
            existing_page_entry = requests[existing_page]
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
            # TODO: save

    def run(self):
        replicadb = ReplicaDatabase("fiwiki")
        replicadb.request()

        api = self.get_mediawiki_api()

        for page in PAGES:
            print("Processing page", page)
            self.process_page(page, api, replicadb)

        replicadb.close()


task_registry.add_task(FiwikiRequestedArticlesTask(2, 'Requested articles clerk', 'fi'))
