from pywikibot.data.api import QueryGenerator
from majavahbot.tasks import Task, task_registry
from majavahbot.api.consts import MEDIAWIKI_DATE_FORMAT
from datetime import datetime
import sys

STANDARD_GROUPS = ['bot', '*', 'user', 'autoconfirmed', 'extendedconfirmed']

TABLE_ROW_FORMAT = """
|-
| {{no ping|%s}}
| %s
| %s
| %s
| data-sort-value=%s | %s
| %s
| %s
"""


class BotStatusData:
    def __init__(self, name, last_edit_timestamp, last_log_timestamp, edit_count, groups, block_data):
        self.name = name

        self.last_edit_timestamp = None
        self.last_log_timestamp = None
        self.last_activity_timestamp = None

        if last_edit_timestamp is not None:
            self.last_edit_timestamp = datetime.strptime(last_edit_timestamp, MEDIAWIKI_DATE_FORMAT)
            self.last_activity_timestamp = self.last_edit_timestamp

        if last_log_timestamp is not None:
            self.last_log_timestamp = datetime.strptime(last_log_timestamp, MEDIAWIKI_DATE_FORMAT)
            if self.last_edit_timestamp is None:
                self.last_activity_timestamp = self.last_log_timestamp
            else:
                self.last_activity_timestamp = max(self.last_log_timestamp, self.last_edit_timestamp)

        self.edit_count = edit_count
        self.groups = list(filter(lambda x: x not in STANDARD_GROUPS, groups))
        self.block_data = block_data

    def format_date(self, date, sortkey=True):
        if date is None:
            return "-"

        if sortkey:
            return 'data-sort-value=' + date.strftime(MEDIAWIKI_DATE_FORMAT) + ' | ' + date.strftime('%d&nbsp;%b&nbsp;%Y&nbsp;%H:%M:%S') + '&nbsp;(UTC)'

        return date.strftime(MEDIAWIKI_DATE_FORMAT)

    def format_block_reason(self):
        return self.block_data['reason']\
            .replace('[[Category:', '[[:Category:')\
            .replace('[[category:', '[[:category:')\
            .replace('{', '&#123;')\
            .replace('<', '&lt;')\
            .replace('>', '&gt;')

    def format_block(self):
        return "%s by {{no ping|%s}} on %s with expiry at %s.<br/>Block reason is %s" % (
            'Partially blocked' if self.block_data['partial'] else 'Blocked',
            self.block_data['by'], self.block_data['at'], self.block_data['expiry'], self.format_block_reason())

    def to_table_row(self):
        return TABLE_ROW_FORMAT % (
            self.name,
            self.format_date(self.last_activity_timestamp),
            self.format_date(self.last_edit_timestamp),
            self.format_date(self.last_log_timestamp),
            self.edit_count, '{:,}'.format(self.edit_count),
            ', '.join(self.groups),
            self.format_block() if self.block_data is not None else ''
        )


class BotStatusTask(Task):
    def __init__(self, number, name, site):
        super().__init__(number, name, site)

    def get_bot_data(self, username):
        data = QueryGenerator(site=self.get_mediawiki_api().get_site(),
                              list="users|usercontribs|logevents",
                              uclimit=1, ucuser=username, ucdir="older",
                              usprop="blockinfo|groups|editcount", ususers=username,
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

            return BotStatusData(
                name=data['users'][0]['name'],
                last_edit_timestamp=None if len(data['usercontribs']) == 0 else data['usercontribs'][0]['timestamp'],
                last_log_timestamp=None if len(data['logevents']) == 0 else data['logevents'][0]['timestamp'],
                edit_count=data['users'][0]['editcount'],
                groups=data['users'][0]['groups'],
                block_data=block,
            )
        # TODO: make better error handling
        raise Exception("Failed loading bot data for " + username + ": " + str(data))

    def run(self):
        api = self.get_mediawiki_api()

        table = """
{| class="wikitable sortable"
|-
! Bot account
! Last activity
! Last edit
! Last logged action
! Total edits
! Groups
! Block
        """

        for user in api.get_site().allusers(group='bot'):
            username = user['name']
            print("Loading data for bot", username)
            try:
                data = self.get_bot_data(username)
                table += data.to_table_row()
            except Exception as e:
                print(e, file=sys.stderr)

        table += "|}"

        with open('tmp.txt', 'w', encoding="utf-8", errors="ignore") as file:
            file.write(table)


task_registry.add_task(BotStatusTask(3, 'Bot status report', 'en'))
