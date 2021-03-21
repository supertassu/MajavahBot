import re
import pywikibot
import dateparser
from pywikibot.data import api
from pywikibot.comms.eventstreams import EventStreams, site_rc_listener

SIGNATURE_TIME_REGEX = re.compile(r'\d\d:\d\d, \d{1,2} \w*? \d\d\d\d \(UTC\)')


class MediawikiApi:
    def __init__(self, site, family):
        self.site = pywikibot.Site(site, family)

    def __repr__(self):
        self.site.login()
        return 'MediawikiApi{wiki=%s,user=%s,has_bot_flag=%s}' % (
            self.site.hostname(),
            self.site.username(),
            'bot' in self.site.userinfo['rights'],
        )

    def test(self):
        return pywikibot.User(self.site, self.site.username()).exists()

    def get_site(self) -> pywikibot.Site:
        return self.site

    def get_page(self, page_name: str) -> pywikibot.Page:
        return pywikibot.Page(self.site, page_name)

    def get_user(self, user_name) -> pywikibot.User:
        return pywikibot.User(self.site, user_name)

    def get_page_change_stream(self, page_name: str, allow_bots: bool = False) -> EventStreams:
        stream = site_rc_listener(self.site)
        stream.register_filter(title=page_name)

        if not allow_bots:
            stream.register_filter(bot=False)

        return stream

    def get_last_abuse_filter_trigger(self, user: str):
        '''Retrieves latest Special:AbuseLog entry for specified user.'''
        self.site.login()
        request = api.Request(
            self.site,
            action='query',
            list='abuselog',
            afluser=user,
            afldir='older',
            afllimit='1',
            aflprop='ids|user|title|action|result|timestamp|filter|details',
        )
        response = request.submit()['query']['abuselog']
        if len(response) > 0:
            return response[0]
        return None

    def is_filter_private(self, filter_id: str) -> bool:
        self.site.login()
        request = api.Request(
            self.site,
            action='query',
            list='abusefilters',
            abfstartid=filter_id,
            abfendid=filter_id,
            abflimit=1,
            abfshow='private',
        )
        response = request.submit()['query']['abusefilters']
        return len(response) > 0

    def get_last_reply(self, section: str):
        # example: 22:25, 11 September 2019 (UTC)
        date_strings = SIGNATURE_TIME_REGEX.findall(section)
        dates = list(map(dateparser.parse, date_strings))
        dates = sorted(dates)
        return dates[-1] if len(dates) > 0 else None

    def get_wikidata_id(self, page: pywikibot.Page):
        if not page.exists():
            return None

        # T256583, T87345
        page.get(get_redirect=True)
        if page.isRedirectPage():
            page = page.getRedirectTarget()
            page.get()

        item = pywikibot.ItemPage.fromPage(page)
        if not item or not item.exists():
            return None
        return item.title()

    def compare_page_titles(self, first: str, second: str) -> bool:
        return first.lower().replace('_', ' ') == second.lower().replace('_', ' ')


mediawiki_apis = {}


def get_mediawiki_api(site='en', family='wikipedia') -> MediawikiApi:
    if family not in mediawiki_apis:
        mediawiki_apis[family] = {}
    if site not in mediawiki_apis[family]:
        mediawiki_apis[family][site] = MediawikiApi(site, family)
    return mediawiki_apis[family][site]
