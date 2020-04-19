from majavahbot.api import MediawikiApi, ReplicaDatabase, manual_run, get_mediawiki_api
from majavahbot.config import requested_articles_config_page
from majavahbot.tasks import Task, task_registry
from pywikibot import Page
from re import compile


ENTRY_REGEX = compile(r"\n:*\*+ ?([^\n]+)")
LOCAL_LINK_REGEX = compile(r"\[\[([^\:\]]+)\]\]")
OTHER_WIKI_LINK_REGEX = compile(r"\[\[:?([a-z]{2,3}):([^\:|\]]+)(\|[^:\]]+)?\]\]")

EXISTING_PAGE_QUERY = """
SELECT page_title FROM page
WHERE page_namespace = 0
AND page_is_redirect = 0
AND page_title IN (%s)
AND NOT EXISTS (SELECT cl_from FROM categorylinks WHERE cl_from = page.page_id AND cl_to = "Täsmennyssivut")
"""


class FiwikiRequestedArticlesTask(Task):
    def __init__(self, number, name, site):
        super().__init__(number, name, site)
        self.register_task_configuration(requested_articles_config_page)
        self.supports_manual_run = True

    def compare_wikidata_qs(self, page: Page, api: MediawikiApi, other_links: list):
        try:
            local_wikidata_id = api.get_wikidata_id(page)
            found_wikidata_ids = set()
            found_wikidata_ids.add(str(local_wikidata_id))

            for other_link in other_links:
                other_site = get_mediawiki_api(other_link.group(1), api.get_site().family)
                if not other_site:
                    continue
                other_page = other_site.get_page(other_link.group(2))
                if not other_page:
                    continue

                other_wikidata_id = other_site.get_wikidata_id(other_page)
                found_wikidata_ids.add(str(other_wikidata_id))

            if len(found_wikidata_ids) != 1:
                print("Found %s different Wikidata Q's: %s" % (len(found_wikidata_ids), ', '.join(found_wikidata_ids)))
                return False
            return True
        except TimeoutError:
            pass  # ignore; will return false

        return False

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
            print("- Request %s (%s)" % (existing_page, existing_page_entry.replace("\n", "")))

            other_links = list(OTHER_WIKI_LINK_REGEX.finditer(existing_page_entry))

            if len(other_links) >= 1:
                print("Found at least 1 link to other wiki, comparing Wikidata Q's...")
                page = api.get_page(existing_page)
                if not self.compare_wikidata_qs(page, api, other_links):
                    continue

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
