from majavahbot.tasks import task_registry

task_registry.add_all_tasks()
print(task_registry.get_tasks())

for task in task_registry.get_tasks():
    task.run()
