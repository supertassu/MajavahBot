from importlib import import_module
import os


class Task:
    def __init__(self, number, name):
        self.number = number
        self.name = name

    def __repr__(self):
        return "Task(number=" + str(self.number) + ",name=" + self.name + ")"

    def run(self):
        raise Exception("Not implemented yet")


class TaskRegistry:
    def __init__(self):
        self.tasks = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks

    def add_all_tasks(self):
        for module in os.listdir(os.path.dirname(__file__)):
            if module == '__init__.py' or module == 'task.py' or module[-3:] != '.py':
                continue
            name = 'majavahbot.tasks.' + module[:-3]
            print("Importing task", name)
            import_module(name)


task_registry = TaskRegistry()
