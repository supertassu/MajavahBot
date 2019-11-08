import pywikibot
from pywikibot.data import api
from pywikibot.comms.eventstreams import EventStreams, site_rc_listener


class MediawikiApi:
    def __init__(self):
        self.site = pywikibot.Site()

    def __repr__(self):
        return "MediawikiApi{wiki=%s,user=%s}" % (self.site.hostname(), self.site.username())

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

    """Retrieves latest Special:AbuseLog entry for specified user."""
    def get_last_abuse_filter_trigger(self, user: str):
        self.site.login()
        request = api.Request(self.site, action="query", list="abuselog", afluser=user, afldir="older", afllimit="1",
                              aflprop="ids|user|title|action|result|timestamp|filter|details")
        response = request.submit()['query']['abuselog']
        if len(response) > 0:
            return response[0]
        return None

    def is_filter_private(self, filter_id: str) -> bool:
        self.site.login()
        request = api.Request(self.site, action="query", list="abusefilters", abfstartid=filter_id, abfendid=filter_id,
                              abflimit=1, abfshow="private")
        response = request.submit()['query']['abusefilters']
        return len(response) > 0


mediawiki_api = MediawikiApi()


def get_mediawiki_api():
    return mediawiki_api
