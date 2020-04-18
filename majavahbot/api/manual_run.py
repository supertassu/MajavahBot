def confirm_with_enter() -> bool:
    return input('> Press ENTER to confirm, type anything and press ENTER to abort: ') == ''


def confirm_edit() -> bool:
    return input('> Type yes to confirm edit, anything else to abort: ').lower() == 'yes'
