from majavahbot.api import task_database, get_mediawiki_api
from importlib import import_module
from datetime import datetime
from typing import Optional
import json
import os
import re


class Task:
    def __init__(self, number, name):
        self.number = number
        self.name = name
        self.task_configuration = {}
        task_database.insert_task(self.number, self.name)
        self.approved = task_database.is_approved(self.number)
        self.trial = task_database.get_trial(self.number)

    def __repr__(self):
        return "Task(number=" + str(self.number) + ",name=" + self.name + ")"

    def run(self):
        raise Exception("Not implemented yet")

    def should_use_bot_flag(self):
        return self.approved

    def should_edit(self):
        if self.trial is not None:
            if self.trial['max_edits'] and self.trial['edits_done'] >= self.trial['max_edits']:
                self.trial = None
                print("DEBUG: Trial was completed; max edit count reached")
                return False
            if self.trial['max_days'] >= 0 and (datetime.now() - self.trial['created_at']).total_seconds() \
                    > (self.trial['max_days'] * 86400):
                self.trial = None
                print("DEBUG: Trial was completed; time ran out")
                return False
            return True
            
        return self.approved

    def record_trial_edit(self):
        if self.trial is None:
            raise

        self.trial['edits_done'] += 1
        task_database.record_trial_edit(self.trial['id'])
        
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

    def get_task_by_number(self, number: int) -> Optional[Task]:
        for task in self.get_tasks():
            if task.number == number:
                return task
        return None

    def add_all_tasks(self):
        for module in os.listdir(os.path.dirname(__file__)):
            if module == '__init__.py' or module == 'task.py' or module[-3:] != '.py':
                continue
            name = 'majavahbot.tasks.' + module[:-3]
            print("Importing task", name)
            import_module(name)


task_registry = TaskRegistry()
