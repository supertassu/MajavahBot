import time
import dateparser
import re
import subprocess
import datetime

multiline_reply_regex = re.compile("\n+([^\n]+~~~~)")


def remove_empty_lines_before_replies(text: str) -> str:
    return multiline_reply_regex.sub("\n\\1", text)


def get_revision() -> str:
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


def create_delay(seconds) -> Delay:
    return Delay(seconds)


def was_enough_time_ago(time_text: str, seconds: int) -> bool:
    parsed_time = dateparser.parse(time_text)
    diff = datetime.datetime.now(tz=datetime.timezone.utc) - parsed_time
    return diff.total_seconds() > seconds
