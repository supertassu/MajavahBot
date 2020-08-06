from majavahbot.api import task_database, get_mediawiki_api, ReplicaDatabase
from majavahbot.api.consts import JOB_STATUS_FAIL, JOB_STATUS_DONE
from majavahbot.tasks import task_registry
import argparse
from sys import exit

task_database.request()
task_database.init()
task_registry.add_all_tasks()
task_database.close()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def cli_whoami():
    api = get_mediawiki_api()
    print("I am %s" % api)


def cli_task_list():
    for task in task_registry.get_tasks():
        print("Task %i (%s) on wiki %s | Approved: %s | Trial: %s | Bot flag: %s | Supports manual run: %s"
              % (task.number, task.name, task.site, str(task.approved), str(task.trial),
                 str(task.should_use_bot_flag()), str(task.supports_manual_run)))


def cli_check_replica(name: str):
    db = ReplicaDatabase(name)
    print("Successfully connected to " + db.db_name + ". Replication lag is " + str(db.get_replag()) + " seconds.")


def cli_task(number: int, run: bool, manual: bool, config: bool, job_name="cronjob", param=""):
    task = task_registry.get_task_by_number(number)
    if task is None:
        print("Task not found")
        exit(1)

    task.param = param

    if config:
        print("Task configuration for task", task.number)
        print(task.get_task_configuration())
        exit(0)
        return

    if not task.should_edit():
        print("Task is not approved")
        exit(1)
        return

    if run:
        print("Starting task", task.number)

        if task.is_continuous:
            task.run()
        else:
            job_id = task_database.start_job(job_name, task.number, task.get_mediawiki_api().get_site().dbName())
            try:
                task.run()
                task_database.stop_job(job_id, JOB_STATUS_DONE)
            except Exception as e:
                task_database.stop_job(job_id, JOB_STATUS_FAIL)
                raise e
            except KeyboardInterrupt as e:
                task_database.stop_job(job_id, JOB_STATUS_FAIL)
                raise e
    elif manual:
        print("Manually running task", task.number)
        task.do_manual_run()
    else:
        print("Unknown action")
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    whoami_parser = subparsers.add_parser('whoami')
    task_list_parser = subparsers.add_parser('task_list')

    replica_parser = subparsers.add_parser('check_replica')
    replica_parser.add_argument('name', metavar="name", help="Database name to check connectivity to", type=str)

    task_parser = subparsers.add_parser('task')
    task_parser.add_argument(
        'number', metavar='number', help='Task number', type=int)
    task_parser.add_argument(
        '--run', dest='run', type=str2bool, nargs='?', const=True, default=False, help='Run the task')
    task_parser.add_argument(
        '--manual', dest='manual', type=str2bool, nargs='?', const=True, default=False, help='Manually runs the task')
    task_parser.add_argument(
        '--config', dest='config', type=str2bool, nargs='?', const=True, default=False, help='Shows the task configuration')
    task_parser.add_argument(
        '--job-name', dest='job_name', type=str, nargs='?', default="cronjob", help='Job name to record to database')
    task_parser.add_argument(
        '--param', dest='param', type=str, nargs='?', default="", help='Additional param passed to the job')

    kwargs = vars(parser.parse_args())
    subparser = kwargs.pop('subparser')

    if subparser is None:
        print("Unknown subcommand, use --help for help")
        exit(1)

    globals()['cli_' + subparser](**kwargs)
