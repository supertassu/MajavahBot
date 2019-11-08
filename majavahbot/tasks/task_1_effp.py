from majavahbot.api import get_mediawiki_api
from majavahbot.tasks import Task, task_registry
from majavahbot.config import effpr_page_name


class EffpTask(Task):
    def run(self):
        api = get_mediawiki_api()
        page = api.get_page(effpr_page_name)
        stream = api.get_page_change_stream(effpr_page_name)
        if not page.exists():
            print("Page does not exist")
            return
        print(stream)
        for change in stream:
            # refresh page data
            page.get(force=True)

            print("change       ", change)
            print("new wiki text", page.text)
            print("")
        print("the end")


task_registry.add_task(EffpTask(1, 'EFFP helper'))
