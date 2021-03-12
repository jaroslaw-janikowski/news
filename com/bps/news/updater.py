import threading
import feedparser
from gi.repository import GObject


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
        data = feedparser.parse(self._url)

        # do not hide exceptions from getting data
        # raising exception ignores invalid rss channels from beeing viewed by user
        # even if this XML is only partially invalid.
        # if 'bozo_exception' in data:
        #     raise data['bozo_exception']

        return data['items']


class RestApiChannel(Channel):
    def __init__(self, url):
        super().__init__(url)
        self._channel_type = ChannelType.REST


class Updater(threading.Thread):
    def __init__(self, database, channels, on_channel_end=None, on_update_end=None):
        super().__init__()
        self._db = database
        self._channels = channels
        self._on_channel_end = on_channel_end
        self._on_update_end = on_update_end
        self._do_stop = False

    def run(self):
        num_channels = len(self._channels)
        channel_index = 0.001

        # dla każdego kanału w bazie
        for id, title, url, channel_type, unread_count, folder_title in self._channels:
            # user requested end of update?
            if self._do_stop:
                break

            # get items from next channel
            channel = Channel.create_channel(url, channel_type)
            try:
                items = channel.get_news()

                # dodaj nowe wpisy do bazy danych,
                # powtarajace się zostaną zignorowane
                self._db.add_news(title, items)

                if callable(self._on_channel_end):
                    GObject.idle_add(self._on_channel_end, title, channel_index, num_channels, items)

            except Exception as e:
                print(f'Error: Channel name: {title}; exception: {e}')

            finally:
                channel_index += 1
                self._db.recommend_update_quality_all()
                self._db.commit()
        if callable(self._on_update_end):
            GObject.idle_add(self._on_update_end)

    def cancel(self):
        self._db.recommend_update_quality_all()
        self._db.commit()
        self._do_stop = True
