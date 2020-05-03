import time


class Delay:
    def __init__(self, seconds):
        self.seconds = seconds
        self.started = time.time()

    def get_remaining(self):
        return self.seconds - (time.time() - self.started)

    def wait(self):
        time.sleep(self.get_remaining())


def create_delay(seconds):
    return Delay(seconds)
