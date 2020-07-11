import mysql.connector
from majavahbot.api.consts import JOB_STATUS_RUNNING
from majavahbot.config import analytics_db_hostname, analytics_db_option_file, analytics_db_port, \
    own_db_hostname, own_db_option_file, own_db_database
from datetime import datetime


class BaseDatabase:
    def __init__(self, host, port, option_files, database):
        self.open = 0
        self.database = mysql.connector.connect(
            host=host,
            port=port,
            option_files=option_files,
            database=database
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

    def run(self, sql: str, values=(), get_id=False):
        last_row_id = None
        self.request()
        cursor = self.database.cursor(buffered=True)
        cursor.execute(sql, values)
        if get_id:
            last_row_id = cursor.lastrowid
        cursor.close()
        self.commit()
        self.close()
        return last_row_id

    def get_one(self, sql: str, values=()):
        self.request()
        cursor = self.database.cursor(buffered=True)
        cursor.execute(sql, values)
        results = cursor.fetchone()
        cursor.close()
        self.commit()
        self.close()
        return results

    def get_all(self, sql: str, values=()):
        self.request()
        cursor = self.database.cursor(buffered=True)
        cursor.execute(sql, values)
        results = cursor.fetchall()
        cursor.close()
        self.commit()
        self.close()
        return results


class ReplicaDatabase(BaseDatabase):
    def __init__(self, db):
        super().__init__(
            host=analytics_db_hostname.replace("{DB}", db),
            port=analytics_db_port,
            option_files=analytics_db_option_file,
            database=db + "_p"
        )


class TaskDatabase(BaseDatabase):
    def __init__(self):
        super().__init__(
            host=own_db_hostname,
            port=3306,
            option_files=own_db_option_file,
            database=own_db_database
        )

    def init(self):
        self.request()

        self.run("create table if not exists tasks (id integer primary key not null, name varchar(255) not null,"
                 "approved tinyint(1) default 0 not null);")
        self.run("create table if not exists task_trials (id integer primary key auto_increment not null,"
                 "task_id integer not null, created_at timestamp default current_timestamp not null,"
                 "max_days integer default 0 not null, max_edits integer default 0 not null,"
                 "edits_done integer default 0 not null, closed tinyint(1) default 0 not null);")
        self.run("create table if not exists jobs (id integer primary key auto_increment not null,"
                 "status varchar(16) not null, job_name varchar(64) not null,"
                 "task_id integer not null, task_wiki varchar(16) not null,"
                 "started_at timestamp not null default now(), ended_at timestamp default null);")

        self.close()

    def insert_task(self, number, name):
        self.run("insert into tasks(id, name) values (%s, %s) on duplicate key update name = %s;",
                 (number, name, name))

    def is_approved(self, number):
        results = self.get_one("select approved from tasks where id = %s limit 1;", (number,))
        return bool(results[0])

    def get_trial(self, number):
        results = self.get_one("select * from task_trials where task_id = %s "
                               "order by created_at desc limit 1", (number,))

        if results is None:
            return None

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
        self.run("update task_trials set edits_done = edits_done + 1 where id = %s;", (trial_id,))

    def start_job(self, job_name: str, task_id: int, task_wiki: str):
        return self.run("insert into jobs (job_name, task_id, task_wiki, status, started_at)"
                        "values (%s, %s, %s, %s, CURRENT_TIMESTAMP())",
                        (job_name, task_id, task_wiki, JOB_STATUS_RUNNING,), True)

    def stop_job(self, job_id: str, status: str):
        self.run("update jobs set ended_at=current_timestamp(), status = %s where id = %s", (status, job_id,))


task_database = TaskDatabase()
