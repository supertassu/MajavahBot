from majavahbot.api.database import task_database
from majavahbot.api.utils import get_revision
from majavahbot.api.consts import *
from majavahbot.tasks import task_registry
from flask import Flask, render_template
app = Flask(__name__, template_folder='majavahbot/web/templates')


# utils to be used in tempale
def get_badge_color_for_status(status):
    return {
        JOB_STATUS_RUNNING: 'badge-info',
        JOB_STATUS_DONE: 'badge-success',
        JOB_STATUS_FAIL: 'badge-danger',
    }[status]


def format_duration(job):
    started_at = job[5]
    ended_at = job[6]
    duration = ended_at - started_at
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours, minutes, seconds)


@app.context_processor
def inject_base_variables():
    return {
        "revision": get_revision(),
    }


@app.route('/')
def index():
    task_database.request()
    task_database.init()
    task_registry.add_all_tasks()
    jobs = task_database.get_all("select id, status, job_name, task_id, task_wiki, started_at, ended_at from jobs order by `started_at` desc limit 20;")
    tasks = task_registry.get_tasks()
    task_database.close()

    return render_template('index.html',
                           jobs=jobs,
                           tasks=tasks,
                           get_badge_color_for_status=get_badge_color_for_status,
                           format_duration=format_duration,
                           )


if __name__ == '__main__':
    app.run()
