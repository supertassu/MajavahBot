from majavahbot.api import task_database, get_mediawiki_api, MediawikiApi
from importlib import import_module
from datetime import datetime
from typing import Optional
import json
import os
import re


class Task:
    def __init__(self, number, name, site, family):
        self.number = number
        self.name = name
        self.site = site
        self.family = family

        self.is_continuous = False
        self.supports_manual_run = False
        self.is_manual_run = False

        self.task_configuration = {}
        self.task_configuration_page = None
        self.task_configuration_last_loaded = None

        task_database.insert_task(self.number, self.name)
        self.approved = task_database.is_approved(self.number)
        self.trial = task_database.get_trial(self.number)

    def __repr__(self):
        return "Task(number=" + str(self.number) + ",name=" + self.name + ")"

    def run(self):
        raise Exception("Not implemented yet")

    def do_manual_run(self):
        self.is_manual_run = True

        if self.supports_manual_run:
            self.run()
            return
        raise Exception("This task does not support manual runs")

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
            return

        self.trial['edits_done'] += 1
        task_database.record_trial_edit(self.trial['id'])

    def get_mediawiki_api(self) -> MediawikiApi:
        return get_mediawiki_api(self.site, self.family)

    def task_configuration_reloaded(self, old, new):
        pass

    def _load_task_configuration(self, contents: str):
        config_text = re.sub(r"[\n ]//.*", "", contents, flags=re.MULTILINE)
        config = json.loads(config_text)
        self.task_configuration_reloaded(self.task_configuration, config)
        self.task_configuration = config
        self.task_configuration_last_loaded = datetime.now()

    def register_task_configuration(self, config_page_name: str):
        self.task_configuration_page = config_page_name

    def get_task_configuration(self, key: str = ""):
        if self.task_configuration_last_loaded is None \
                or (datetime.now() - self.task_configuration_last_loaded).total_seconds() > 60 * 15:
            api = self.get_mediawiki_api()
            page = api.get_page(self.task_configuration_page)
            self._load_task_configuration(page.text)

        if len(key) == 0:
            return self.task_configuration

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
            import_module(name)


task_registry = TaskRegistry()
