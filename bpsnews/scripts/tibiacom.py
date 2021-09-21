import requests
import feedgenerator
import json


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    @classmethod
    def _download(cls, url):
        resp = requests.get(url)
        return resp.text

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('tibia.com', 'https://tibia.com', 'RSS dla tibia.com')

        print('pobieram: ', self._start_url)
        try:
            jsn = self._download(self._start_url)
            doc = json.loads(jsn)

            # znajdź wszystkie posty i dodaj do dokumentu wynikowego
            for news in doc['newslist']['data']:
                title = news['news']
                print('Nowy news: ', title)
                link = news['tibiaurl']
                description = title
                feed_gen.add_item(title, link, description)

            return feed_gen.writeString('utf-8')
        except json.JSONDecodeError:
            print('Error: Tibia: brak zawartości JSON.')
        except requests.exceptions.ConnectionError:
            print('Error: Brak połączenia.')
