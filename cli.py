from majavahbot.api import task_database
from majavahbot.tasks import task_registry

task_database.request()
task_registry.add_all_tasks()
task_database.init()
task_database.close()

for task in task_registry.get_tasks():
    pass
    # task.run()
