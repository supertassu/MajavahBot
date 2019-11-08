import pywikibot


class MediawikiApi:
    def __init__(self):
        self.site = pywikibot.Site()

    def test(self):
        return pywikibot.User(self.site, self.site.username()).exists()

    def get_page(self, page_name) -> pywikibot.Page:
        return pywikibot.Page(self.site, page_name)


mediawiki_api = MediawikiApi()


def get_mediawiki_api():
    return mediawiki_api
