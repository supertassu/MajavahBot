from pywikibot import config
from os import path

effpr_config_page = 'User:MajavahBot/EFFP Helper Configuration'
requested_articles_config_page = 'Käyttäjä:MajavahBot/Asetukset/Artikkelitoiveiden siivoaja'

own_db_hostname = "tools.db.svc.eqiad.wmflabs"
own_db_port = 3306
own_db_option_file = path.expanduser("~/replica.my.cnf")
own_db_database = "s54198__majavahbot"

analytics_db_hostname = "{DB}.analytics.db.svc.eqiad.wmflabs"
analytics_db_port = 3306
analytics_db_option_file = path.expanduser("~/replica.my.cnf")
