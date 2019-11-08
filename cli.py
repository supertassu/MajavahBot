from majavahbot.tasks import task_registry
from majavahbot.api import get_mediawiki_api

task_registry.add_all_tasks()
print(get_mediawiki_api())

for task in task_registry.get_tasks():
    task.run()
