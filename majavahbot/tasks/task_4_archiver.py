from majavahbot.api import ReplicaDatabase
from majavahbot.api.manual_run import confirm_edit
from majavahbot.tasks import Task, task_registry


QUERY = """
select
    page_id,
    concat("Talk:", page_title) as page_full_title,
    page_len
from page
where
    page_namespace = 1
    and page_title not like '%/%'
    and page_len > 5000
    and not exists (
        select 1
        from templatelinks
        where tl_from = page_id
        and (tl_title = "MajavahBot/config" or tl_title = "MajavahBot/no-autotag")
        and tl_namespace = 2
    )
order by page_len desc
limit 20;
"""


class AchieverBot(Task):
    def __init__(self, number, name, site, family):
        super().__init__(number, name, site, family)
        self.supports_manual_run = True
        self.register_task_configuration("User:MajavahBot/Options")

    def run(self):
        if self.param != "autosetup":
            print("Unknown mode")
            return

        self.merge_task_configuration(
            autosetup_run=False,
            autosetup_tag="{{subst:Përdoruesi:MajavahBot/arkivimi automatik}}",
            autosetup_summary="MajavahBot: Vendosja e faqes së diskutimit për arkivim automatik",
        )

        if self.get_task_configuration("autosetup_run") is not True:
            print("Disabled in configuration")
            return

        api = self.get_mediawiki_api()
        replicadb = ReplicaDatabase(api.get_site().dbName())

        replag = replicadb.get_replag()
        if replag > 10:
            print("Replag is over 10 seconds, not processing! (" + str(replag) + ")")
            return

        results = replicadb.get_all(QUERY)
        print("-- Got %s pages" % (str(len(results))))
        for page_from_db in results:
            page_id = page_from_db[0]
            page_name = page_from_db[1].decode('utf-8')

            page = api.get_page(page_name)
            page_text = page.get()
            assert page.pageid == page_id

            print("Tagging page ", page.title())
            new_text = self.get_task_configuration("autosetup_tag") + "\n\n" + page_text
            if new_text != page_text and self.should_edit() and (not self.is_manual_run or confirm_edit()):
                api.site.login()
                page.text = new_text
                page.save(self.get_task_configuration("autosetup_summary"),
                          watch=False, minor=False, botflag=self.should_use_bot_flag())
                self.record_trial_edit()


task_registry.add_task(AchieverBot(4, 'Archive utility', 'sq', 'wikipedia'))
