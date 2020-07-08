from majavahbot.api import manual_run, utils
from majavahbot.api.mediawiki import MediawikiApi
from majavahbot.api.utils import remove_empty_lines_before_replies
from majavahbot.config import steward_request_bot_config_page
from majavahbot.tasks import Task, task_registry
from pywikibot.data.api import QueryGenerator
import mwparserfromhell


class StewardRequestTask(Task):
    def __init__(self, number, name, site, family):
        super().__init__(number, name, site, family)
        self.register_task_configuration(steward_request_bot_config_page)
        self.supports_manual_run = True

    def get_steward_who_gblocked_ip(self, api: MediawikiApi, ip_or_range):
        data = QueryGenerator(site=api.get_site(),
                              list="globalblocks",
                              bgip=ip_or_range,
                              ).request.submit()['query']['globalblocks']
        if len(data) == 0:
            return None

        if not utils.was_enough_time_ago(data[0]['timestamp'], self.get_task_configuration('time_min')):
            return None

        return data[0]['by']

    def get_steward_who_locked_account(self, api: MediawikiApi, account_name):
        data = QueryGenerator(site=api.get_site(),
                              list="logevents",
                              letype="globalauth",
                              letitle="User:" + account_name + "@global"
                              ).request.submit()['query']['logevents']

        if len(data) == 0 or "locked" not in data[0]['params']['0']:
            return None

        if not utils.was_enough_time_ago(data[0]['timestamp'], self.get_task_configuration('time_min')):
            return None

        return data[0]['user']

    def run(self):
        self.merge_task_configuration(
            run=True,
            page="Steward requests/Global",
            summary="BOT: Marking done requests as done",
            time_min=5*60
        )

        if self.get_task_configuration("run") is not True:
            print("Disabled in configuration")
            return

        api = self.get_mediawiki_api()
        page = api.get_page(self.get_task_configuration('page'))
        parsed = mwparserfromhell.parse(page.get())
        sections = parsed.get_sections(levels=[3])

        for section in sections:
            status = None

            accounts = []
            ips = []

            awesome_people = []

            for template in section.filter_templates():
                if template.name.matches('status'):
                    status = template
                elif template.name.matches('LockHide') or template.name.matches('MultiLock'):
                    for param in template.params:
                        if not param.can_hide_key(param.name):
                            continue
                        param_text = param.value.strip_code()
                        if len(param_text) == 0:
                            continue
                        accounts.append(param_text)
                elif template.name.matches('Luxotool'):
                    for param in template.params:
                        if not param.can_hide_key(param.name):
                            continue
                        param_text = param.value.strip_code()
                        if len(param_text) == 0:
                            continue
                        ips.append(param_text)

            # status already has a value, assuming this has already been processed
            if not status or status.has(1):
                continue

            mark_done = True

            for ip in ips:
                steward = self.get_steward_who_gblocked_ip(api, ip)
                if steward is None:
                    mark_done = False
                else:
                    awesome_people.append(steward)

            for account in accounts:
                steward = self.get_steward_who_locked_account(api, account)
                if steward is None:
                    mark_done = False
                else:
                    awesome_people.append(steward)

            if not mark_done or len(awesome_people) == 0:
                continue

            # remove duplicates
            awesome_people = ", ".join(list(dict.fromkeys(awesome_people)))

            if mark_done:
                status.add(1, 'done')
                section.append(": '''Robot clerk note:''' {{done}} by " + awesome_people + " ~~~~\n")
                print("Marking as done", awesome_people, status, ips, accounts)

        new_text = str(parsed)
        new_text = remove_empty_lines_before_replies(new_text)

        if new_text != page.get() and self.should_edit() and (not self.is_manual_run or manual_run.confirm_edit()):
            api.site.login()
            page.text = new_text
            page.save(self.get_task_configuration("summary"), botflag=self.should_use_bot_flag())
            self.record_trial_edit()


task_registry.add_task(StewardRequestTask(5, 'Steward request bot', 'meta', 'meta'))
