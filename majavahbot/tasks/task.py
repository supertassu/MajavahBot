from majavahbot.api import task_database, get_mediawiki_api
from importlib import import_module
import json
import os
import re


class Task:
    def __init__(self, number, name):
        self.number = number
        self.name = name
        self.task_configuration = {}
        task_database.insert_task(self.number, self.name)

    def __repr__(self):
        return "Task(number=" + str(self.number) + ",name=" + self.name + ")"

    def run(self):
        raise Exception("Not implemented yet")

    def task_configuration_reloaded(self, old, new):
        pass

    def _load_task_configuration(self, contents: str):
        config = json.loads(re.sub("//.*", "", contents, flags=re.MULTILINE))
        self.task_configuration_reloaded(self.task_configuration, config)
        self.task_configuration = config

    def register_task_configuration(self, config_page_name: str):
        api = get_mediawiki_api()
        page = api.get_page(config_page_name)
        self._load_task_configuration(page.text)

        try:
            stream = api.get_page_change_stream(page, True)
            for _ in stream:
                page.get(force=True)
                self._load_task_configuration(page.text)
        except:
            print("Task configuration can't be reloaded")

    def get_task_configuration(self, key: str):
        # TODO: support for nested keys
        return self.task_configuration[key]


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
