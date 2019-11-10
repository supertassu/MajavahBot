import mysql.connector
from majavahbot.config import own_db_hostname, own_db_option_file, own_db_database


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

    def execute(self, sql: str, values=()):
        self.request()
        cursor = self.database.cursor()
        cursor.execute(sql, values)
        cursor.close()
        self.commit()
        self.close()

    def init(self):
        self.request()
        self.execute("create table if not exists tasks (id integer primary key not null, name varchar(255) not null,"
                     + "approved tinyint(1) default 0 not null);")
        self.close()

    def insert_task(self, number, name):
        self.request()
        self.execute("insert into tasks(id, name) values (%s, %s) on duplicate key update name = %s;", (number, name, name))
        self.close()


task_database = TaskDatabase()
