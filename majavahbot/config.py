from pywikibot import config

use_tools_database = config.family != "vagrant"

# effpr_page_name = 'Wikipedia:Edit filter/False Positives/Reports'
effpr_page_name = 'Test Page'
effpr_filter_log_format = '//en.wikipedia.org/wiki/Special:AbuseLog?title=Special:AbuseLog&wpSearchTitle=%s'
effpr_section_header_regex = r"==([^=]+)==[^\n=]*\n"

effpr_page_title_regex = r";Page you were editing\n: ([^\n]*)\n" # https://regex101.com/r/7kc9xJ/1
effpr_page_title_wrong_format_regexes = \
    r'\[\[https:\/\/en.wikipedia.org\/wiki\/([^\]]+)]] \(<span class="plainlinks">[^<]+<\/span>\)'

effpr_closed_strings = (
    "{{effp|f|", "{{effp|f}}", "{{effp|fixed",
    "{{effp|d|", "{{effp|d}}", "{{effp|done",
    "{{effp|t|", "{{effp|t}}", "{{effp|talk",
    "{{effp|a|", "{{effp|a}}", "{{effp|alreadydone",
    "{{effp|nd}}", "{{effp|notdone}}",
    "{{effp|v}}", "{{effp|denied}}",
    "{{effp|b|", "{{effp|b}}", "{{effp|blocked",
)

if use_tools_database:
    own_db_hostname = "tools.db.svc.eqiad.wmflabs"
    own_db_option_file = "~/replica.my.cnf"
    own_db_database = "s54198__majavahbot"
else:
    own_db_hostname = "localhost"
    own_db_option_file = "local.my.cnf"
    own_db_database = "majavahbot"
