import json
import requests
import feedgenerator
import bs4


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('ohmydev.pl', 'https://ohmydev.pl', 'RSS dla ohmydev.pl')
        do_run = True
        i = 1
        while do_run:
            url = f'https://ohmydev.pl/omd/api/feed?page={i}&perPage=15&sortBy=recent'
            print('pobieram porcję: ', i)
            resp = requests.get(url)
            data = resp.json()['data']

            # czy to już koniec paginacji artykułów?
            if len(data) == 0:
                print('Nie ma więcej artykułów.')
                break

            # znajdź wszystkie posty i dodaj do dokumentu wynikowego
            for article in data:
                title = article['title']
                print('Nowy news: ', title)
                if title == self._stop_title:
                    do_run = False
                    break
                link = article['linkUrl'] if 'linkUrl' in article else None
                description = article['shortBody'] if 'shortBody' in article else 'Brak opisu.'
                feed_gen.add_item(title, link, description)

            i += 1

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')


if __name__ == '__main__':
    s = Spider('https://ohmydev.pl/omd/api/feed?page=1&perPage=15&sortBy=recent')
    s.start()
