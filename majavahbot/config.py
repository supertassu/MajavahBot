from pywikibot import config

use_tools_database = config.family != "vagrant"

effpr_config_page = 'User:MajavahBot/EFFP Helper Configuration'

if use_tools_database:
    own_db_hostname = "tools.db.svc.eqiad.wmflabs"
    own_db_option_file = "~/replica.my.cnf"
    own_db_database = "s54198__majavahbot"
else:
    own_db_hostname = "localhost"
    own_db_option_file = "local.my.cnf"
    own_db_database = "majavahbot"
