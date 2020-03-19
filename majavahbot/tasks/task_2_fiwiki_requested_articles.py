from majavahbot.api import MediawikiApi, ReplicaDatabase
from majavahbot.tasks import Task, task_registry
from re import compile


ENTRY_REGEX = compile(r"\n:*\*+ ?([^\n]+)")
LOCAL_LINK_REGEX = compile(r"\[\[([^\:\]]+)\]\]")
EXISTING_PAGE_QUERY = "SELECT page_title FROM page WHERE page_namespace = 0 AND page_is_redirect = 0 AND page_title IN (%s)"


class FiwikiRequestedArticlesTask(Task):
    def process_page(self, page: str, api: MediawikiApi, replica: ReplicaDatabase):
        page = api.get_page(page)
        text = page.text
        entries = list(ENTRY_REGEX.finditer(text))
        requests = {}

        for entry in entries:
            entry_text = entry.group(1)
            first_link = LOCAL_LINK_REGEX.match(entry_text)
            if first_link:
                requests[first_link.group(1).replace(" ", "_")] = entry.span()

        page_titles = requests.keys()
        format_strings = ','.join(['%s'] * len(page_titles))
        existing_pages = replica.execute(EXISTING_PAGE_QUERY % format_strings, tuple(requests.keys()))

        print(existing_pages)

    def run(self):
        replicadb = ReplicaDatabase("fiwiki")
        replicadb.request()

        api = self.get_mediawiki_api()
        self.process_page('Wikipedia:Artikkelitoiveet/Tekniikka', api, replicadb)

        replicadb.close()


# task_registry.add_task(FiwikiRequestedArticlesTask(2, 'Requested articles clerk', 'fi'))
