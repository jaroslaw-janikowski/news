import threading
import feedparser


class Updater(threading.Thread):
    def __init__(self, database, channels, on_update_end=None):
        super().__init__()
        self._db = database
        self._channels = channels
        self._on_update_end = on_update_end

    def run(self):
        # dla każdego kanału w bazie
        for id, title, url, unread_count, folder_title in self._channels:
            # pobierz plik xml
            items = feedparser.parse(url)['items']

            # dodaj nowe wpisy do bazy danych,
            # powtarajace się zostaną zignorowane
            self._db.add_news(title, items)

        if callable(self._on_update_end):
            self._on_update_end()
