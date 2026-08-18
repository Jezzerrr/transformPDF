import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartHandler(FileSystemEventHandler):

    def __init__(self):
        self.process = self.start_app()

    def start_app(self):
        return subprocess.Popen([sys.executable, "main.py"])

    def on_modified(self, event):

        if not event.src_path.endswith(".py"):
            return

        self.process.kill()
        self.process = self.start_app()


observer = Observer()

observer.schedule(
    RestartHandler(),
    ".",
    recursive=True
)

observer.start()

observer.join()
