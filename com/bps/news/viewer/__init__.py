import subprocess
import threading


class StreamlinkViewer(threading.Thread):
    def __init__(self, url, quality='worst', **kwargs):
        super().__init__()

        # self.daemon = True  # powoduje dziwne zawieszenia po kilku odtworzeniach filmów

        self._url = url
        self._quality = quality

        self._on_start = kwargs['on_start'] if 'on_start' in kwargs else None

    def run(self):
        self._run_streamlink(self._url, self._quality)

    def _run_streamlink(self, url, quality='worst'):
        # run process in blocking mode
        with subprocess.Popen(['streamlink', url, quality, '-p', 'mpv'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as p:
            while p.stdout:
                # read lines from stdout
                l = p.stdout.readline()
                if l == b'':
                    break

                # if certain line is detected then stop blocking main window
                if b'Writing stream to output' in l:
                    if callable(self._on_start):
                        self._on_start()
