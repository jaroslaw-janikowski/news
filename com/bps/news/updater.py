import threading
import feedparser


class ChannelType:
    RSS, REST = range(2)


class Channel:
    Map = {
        ChannelType.RSS: 'RssChannel',
        ChannelType.REST: 'RestApiChannel'
    }

    def __init__(self, url):
        self._url = url
        self._channel_type = ChannelType.RSS

    def get_news(self):
        raise NotImplementedError()

    @classmethod
    def create_channel(cls, url, channel_type):
        return globals()[cls.Map[channel_type]](url)


class RssChannel(Channel):
    def __init__(self, url):
        super().__init__(url)
        self._channel_type = ChannelType.RSS

    def get_news(self):
        return feedparser.parse(self._url)['items']


class RestApiChannel(Channel):
    def __init__(self, url):
        super().__init__(url)
        self._channel_type = ChannelType.REST


class Updater(threading.Thread):
    def __init__(self, database, channels, on_update_end=None):
        super().__init__()
        self._db = database
        self._channels = channels
        self._on_update_end = on_update_end

    def run(self):
        # dla każdego kanału w bazie
        for id, title, url, channel_type, unread_count, folder_title in self._channels:
            channel = Channel.create_channel(url, channel_type)
            items = channel.get_news()

            # dodaj nowe wpisy do bazy danych,
            # powtarajace się zostaną zignorowane
            self._db.add_news(title, items)

        if callable(self._on_update_end):
            self._on_update_end()
