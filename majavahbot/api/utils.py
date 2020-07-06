import time
import re
import subprocess

multiline_reply_regex = re.compile("\n+([^\n]+~~~~)")


def remove_empty_lines_before_replies(text: str) -> str:
    return multiline_reply_regex.sub(text, "\n\\1")


def get_revision():
    try:
        output = subprocess.check_output(["git", "describe", "--always"], stderr=subprocess.STDOUT).strip().decode()
        assert 'fatal' not in output
        return output
    except Exception:
        # if somehow git version retrieving command failed, just return
        return ''


class Delay:
    def __init__(self, seconds):
        self.seconds = seconds
        self.started = time.time()

    def get_remaining(self):
        return self.seconds - (time.time() - self.started)

    def wait(self):
        delay = self.get_remaining()
        if delay > 0:
            time.sleep(delay)


def create_delay(seconds):
    return Delay(seconds)
