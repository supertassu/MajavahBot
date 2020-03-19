from majavahbot.api import task_database, get_mediawiki_api
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
        print("Task %i (%s) on wiki %s | Approved: %s | Trial: %s | Bot flag: %s" % (task.number, task.name, task.site, str(task.approved), str(task.trial), str(task.should_use_bot_flag())))


def cli_task(number: int, run: bool):
    task = task_registry.get_task_by_number(number)
    if task is None:
        print("Task not found")
        exit(1)

    if not task.should_edit():
        print("Task is not approved")
        exit(1)
        return

    if run:
        print("Starting task", task.number)
        task.run()
    else:
        print("Unknown action")
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    whoami_parser = subparsers.add_parser('whoami')
    task_list_parser = subparsers.add_parser('task_list')

    task_parser = subparsers.add_parser('task')
    task_parser.add_argument(
        'number', metavar='number', help='Task number', type=int)
    task_parser.add_argument(
        '--run', dest='run', type=str2bool, nargs='?', const=True, default=False, help='Run the task')

    kwargs = vars(parser.parse_args())
    subparser = kwargs.pop('subparser')

    if subparser is None:
        print("Unknown subcommand, use --help for help")
        exit(1)

    globals()['cli_' + subparser](**kwargs)
