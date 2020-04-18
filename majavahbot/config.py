from pywikibot import config
from os import path

use_tools_database = config.family == "vagrant"

effpr_config_page = 'User:MajavahBot/EFFP Helper Configuration'
requested_articles_config_page = 'Käyttäjä:MajavahBot/Asetukset/Artikkelitoiveiden siivoaja'

if use_tools_database:
    own_db_hostname = "tools.db.svc.eqiad.wmflabs"
    own_db_option_file = path.expanduser("~/replica.my.cnf")
    own_db_database = "s54198__majavahbot"
else:
    own_db_hostname = "localhost"
    own_db_option_file = "local.my.cnf"
    own_db_database = "majavahbot"
