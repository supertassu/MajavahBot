import pywikibot
from pywikibot.comms.eventstreams import EventStreams, site_rc_listener


class MediawikiApi:
    def __init__(self):
        self.site = pywikibot.Site()

    def test(self):
        return pywikibot.User(self.site, self.site.username()).exists()

    def get_page(self, page_name: str) -> pywikibot.Page:
        return pywikibot.Page(self.site, page_name)

    def get_page_change_stream(self, page_name: str, allow_bots: bool = False) -> EventStreams:
        stream = site_rc_listener(self.site)
        stream.register_filter(title=page_name)

        if not allow_bots:
            stream.register_filter(bot=False)

        return stream

    def __repr__(self):
        return "MediawikiApi{wiki=%s,user=%s}" % (self.site.hostname(), self.site.username())


mediawiki_api = MediawikiApi()


def get_mediawiki_api():
    return mediawiki_api
