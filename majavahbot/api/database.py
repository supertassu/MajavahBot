import mysql.connector
from majavahbot.config import own_db_hostname, own_db_option_file, own_db_database
from datetime import datetime


class TaskDatabase:
    def __init__(self):
        self.open = 0
        self.database = mysql.connector.connect(
            host=own_db_hostname,
            option_files=own_db_option_file,
            database=own_db_database
        )

    def request(self):
        if self.open < 1:
            self.database.connect()
        self.open += 1

    def close(self):
        self.open -= 1
        if self.open < 1:
            self.database.disconnect()

    def commit(self):
        self.database.commit()

    def execute(self, sql: str, values: tuple = ()):
        self.request()
        cursor = self.database.cursor()
        cursor.execute(sql, values)
        results = cursor.fetchone()
        cursor.close()
        self.commit()
        self.close()
        return results

    def init(self):
        self.request()
        self.execute("create table if not exists tasks (id integer primary key not null, name varchar(255) not null,"
                     + "approved tinyint(1) default 0 not null);")
        self.execute("create table if not exists task_trials (id integer primary key auto_increment not null," 
                     "task_id integer not null, created_at timestamp default current_timestamp not null,"
                     "max_days integer default 0 not null, max_edits integer default 0 not null,"
                     "edits_done integer default 0 not null, closed tinyint(1) default 0 not null);")
        self.close()

    def insert_task(self, number, name):
        self.execute("insert into tasks(id, name) values (%s, %s) on duplicate key update name = %s;",
                     (number, name, name))

    def is_approved(self, number):
        results = self.execute("select approved from tasks where id = %s;", (number, ))
        return bool(results[0])

    def get_trial(self, number):
        results = self.execute("select * from task_trials where task_id = %s "
                               "order by created_at desc limit 1", (number, ))
        results = {
            'id': results[0],
            'task_id': results[1],
            'created_at': results[2],
            'max_days': results[3],
            'max_edits': results[4],
            'edits_done': results[5],
            'closed': bool(results[6]),
        }

        if results['max_days'] >= 0 and (datetime.now() - results['created_at']).total_seconds() \
                > (results['max_days'] * 86400):
            return None

        if results['max_edits'] and results['edits_done'] >= results['max_edits']:
            return None

        return results

    def record_trial_edit(self, trial_id: int):
        self.execute("update task_trials set edits_done = edits_done + 1 where id = %s;", (trial_id, ))


task_database = TaskDatabase()
