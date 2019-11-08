from majavahbot.api import get_mediawiki_api
from majavahbot.tasks import Task, task_registry


class EffpTask(Task):
    def run(self):
        api = get_mediawiki_api()
        page = api.get_page('Wikipedia:Edit filter/False Positives/Reports')
        if not page.exists():
            return


print("Registering task 1")
task_registry.add_task(EffpTask(1, 'EFFP helper'))
