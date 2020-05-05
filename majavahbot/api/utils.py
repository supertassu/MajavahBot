import time


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
