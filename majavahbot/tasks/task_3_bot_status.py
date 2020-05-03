from pywikibot.data.api import QueryGenerator
from majavahbot.tasks import Task, task_registry
from majavahbot.api.consts import MEDIAWIKI_DATE_FORMAT, HUMAN_DATE_FORMAT
from majavahbot.api.utils import create_delay
from datetime import datetime
import mwparserfromhell
import sys

STANDARD_GROUPS = ['bot', '*', 'user', 'autoconfirmed', 'extendedconfirmed']

TABLE_ROW_FORMAT = """
|-
| {{no ping|%s}}
| %s
| %s
| %s
| %s
| %s
| %s
| %s
"""


class BotStatusData:
    def __init__(self, name, operators, last_edit_timestamp, last_log_timestamp, edit_count, groups, block_data):
        self.name = name
        self.operators = set(operators)

        self.last_edit_timestamp = None
        self.last_log_timestamp = None
        self.last_activity_timestamp = None

        if last_edit_timestamp is not None:
            self.last_edit_timestamp = self.parse_date(last_edit_timestamp)
            self.last_activity_timestamp = self.last_edit_timestamp

        if last_log_timestamp is not None:
            self.last_log_timestamp = self.parse_date(last_log_timestamp)
            if self.last_edit_timestamp is None:
                self.last_activity_timestamp = self.last_log_timestamp
            else:
                self.last_activity_timestamp = max(self.last_log_timestamp, self.last_edit_timestamp)

        self.edit_count = edit_count
        self.groups = list(filter(lambda x: x not in STANDARD_GROUPS, groups))
        self.block_data = block_data

    def format_number(self, number, sortkey=True):
        if sortkey:
            return 'class="nowrap" data-sort-value={} | {:,}'.format(number, number)
        return '{:,}'.format(number)

    def parse_date(self, string):
        if string is None:
            return None
        return datetime.strptime(string, MEDIAWIKI_DATE_FORMAT)

    def format_date(self, date, sortkey=True):
        if date is None:
            return 'class="center" | —'

        if sortkey:
            return 'class="nowrap" data-sort-value={} | {}'.format(date.strftime(MEDIAWIKI_DATE_FORMAT), date.strftime(HUMAN_DATE_FORMAT))

        return date.strftime(HUMAN_DATE_FORMAT)

    def format_block_reason(self):
        return self.block_data['reason']\
            .replace('[[Category:', '[[:Category:')\
            .replace('[[category:', '[[:category:')\
            .replace('{', '&#123;')\
            .replace('<', '&lt;')\
            .replace('>', '&gt;')

    def format_block(self):
        return "%s by {{no ping|%s}} on %s to expire at %s.<br/>Block reason is '%s'" % (
            'Partially blocked' if self.block_data['partial'] else 'Blocked',
            self.block_data['by'],
            self.format_date(self.parse_date(self.block_data['at']), sortkey=False),
            self.block_data['expiry'],
            self.format_block_reason())

    def to_table_row(self):
        return TABLE_ROW_FORMAT % (
            self.name,
            self.format_operators(),
            self.format_number(self.edit_count),
            self.format_date(self.last_activity_timestamp),
            self.format_date(self.last_edit_timestamp),
            self.format_date(self.last_log_timestamp),
            ', '.join(self.groups),
            self.format_block() if self.block_data is not None else ''
        )

    def format_operators(self):
        if len(self.operators) == 0:
            return 'class="center" | —'
        return '{{no ping|' + '}}, {{no ping|'.join(self.operators) + '}}'


class BotStatusTask(Task):
    def __init__(self, number, name, site):
        super().__init__(number, name, site)

    def get_bot_data(self, username):
        # get all data needed with one big query
        data = QueryGenerator(site=self.get_mediawiki_api().get_site(),
                              prop="revisions",
                              list="users|usercontribs|logevents",

                              # for prop=revisions
                              titles="User:" + username, redirects=True,
                              rvprop="content", rvslots="main", rvlimit="1",

                              # for list=usercontribs
                              uclimit=1, ucuser=username, ucdir="older",

                              # for list=users
                              usprop="blockinfo|groups|editcount", ususers=username,

                              # for list=logevents
                              lelimit=1, leuser=username, ledir="older"
                              ).request.submit()
        if 'query' in data:
            data = data['query']

            block = None
            if 'blockid' in data['users'][0]:
                block = {
                    'id': data['users'][0]['blockid'],
                    'by': data['users'][0]['blockedby'],
                    'reason': data['users'][0]['blockreason'],
                    'at': data['users'][0]['blockedtimestamp'],
                    'expiry': data['users'][0]['blockexpiry'],
                    'partial': 'blockpartial' in data['users'][0],
                }

            operators = []
            for page_id in data['pages']:
                if page_id == "-1":
                    continue
                page = data['pages'][page_id]
                if page['title'] == "User:" + username and 'missing' not in page:
                    page_text = page['revisions'][0]['slots']['main']['*']
                    parsed = mwparserfromhell.parse(page_text)
                    for template in parsed.filter_templates():
                        if template.name.matches('Bot') or template.name.matches('Bot2'):
                            for param in template.params:
                                if not param.can_hide_key(param.name):
                                    continue
                                param_text = param.value.strip_code()
                                if len(param_text) == 0:
                                    continue
                                operators.append(param_text)

            return BotStatusData(
                name=data['users'][0]['name'],
                operators=operators,
                last_edit_timestamp=None if len(data['usercontribs']) == 0 else data['usercontribs'][0]['timestamp'],
                last_log_timestamp=None if len(data['logevents']) == 0 else data['logevents'][0]['timestamp'],
                edit_count=data['users'][0]['editcount'],
                groups=data['users'][0]['groups'],
                block_data=block,
            )
        # TODO: make better error handling
        raise Exception("Failed loading bot data for " + username + ": " + str(data))

#    def run(self):
#        print(self.get_bot_data("CactusBot").to_table_row())

    def run(self):
        api = self.get_mediawiki_api()

        table = """
{| class="wikitable sortable"
|-
! Bot account
! Operator(s)
! Total edits
! Last activity (UTC)
! Last edit (UTC)
! Last logged action (UTC)
! Groups
! Block
        """

        for user in api.get_site().allusers(group='bot'):
            delay = create_delay(10)  # to not create unnecessary lag
            username = user['name']
            print("Loading data for bot", username)
            try:
                data = self.get_bot_data(username)
                table += data.to_table_row()
            except Exception as e:
                print(e, file=sys.stderr)
            # delay.wait()

        table += "|}"

        with open('tmp.txt', 'w', encoding="utf-8", errors="ignore") as file:
            file.write(table)


task_registry.add_task(BotStatusTask(3, 'Bot status report', 'en'))
