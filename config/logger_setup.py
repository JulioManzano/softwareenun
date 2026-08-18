import sys
import platform


if platform.system() == "Linux":

    class LoggerWriter:
        def __init__(self, file_path):
            self.file = open(file_path, "a", encoding="utf-8")

        def write(self, message):
            if message.strip():
                self.file.write(message)
                self.file.flush()

        def flush(self):
            self.file.flush()

    # Redirigir prints a /opt/softwareenun/logs/print.log
    log_file = "/opt/softwareenun/logs/print.log"

    sys.stdout = LoggerWriter(log_file)
    sys.stderr = LoggerWriter(log_file)