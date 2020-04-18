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
        print(f"Task {task.number:d} ({task.name}) on wiki {task.site} | Approved: {str(task.approved)} | Trial: {str(task.trial)} | Bot flag: {str(task.should_use_bot_flag())} | Supports manual run: {str(task.supports_manual_run)}")


def cli_task(number: int, run: bool, manual: bool, config: bool):
    task = task_registry.get_task_by_number(number)
    if task is None:
        print("Task not found")
        exit(1)

    if config:
        print("Task configuration for task", task.number)
        print(task.get_task_configuration())
        exit(0)
        return

    if not task.should_edit():
        print("Task is not approved")
        exit(1)
        return

    elif run:
        print("Starting task", task.number)
        task.run()
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

    task_parser = subparsers.add_parser('task')
    task_parser.add_argument(
        'number', metavar='number', help='Task number', type=int)
    task_parser.add_argument(
        '--run', dest='run', type=str2bool, nargs='?', const=True, default=False, help='Run the task')
    task_parser.add_argument(
        '--manual', dest='manual', type=str2bool, nargs='?', const=True, default=False, help='Manually runs the task')
    task_parser.add_argument(
        '--config', dest='config', type=str2bool, nargs='?', const=True, default=False, help='Shows the task configuration')

    kwargs = vars(parser.parse_args())
    subparser = kwargs.pop('subparser')

    if subparser is None:
        print("Unknown subcommand, use --help for help")
        exit(1)

    globals()['cli_' + subparser](**kwargs)
