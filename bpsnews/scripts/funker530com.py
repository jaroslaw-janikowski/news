import json
import requests
import feedgenerator


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('funker530.com', 'https://funker530.com', 'RSS dla funker530.com')
        do_run = True
        i = 1
        while do_run:
            url = f'https://www.funker530.com/api/latest/?category_name=all&page={i}'
            print('pobieram porcję: ', i)
            resp = requests.get(url)

            # czy to już koniec paginacji artykułów?
            # podanie nieistniejącej strony
            # powoduje crash aplikacji
            if resp.status_code == 503:
                print('Nie ma więcej artykułów.')
                break

            data = resp.json()['videos']

            # znajdź wszystkie posty i dodaj do dokumentu wynikowego
            for key_, article in data.items():
                title = article['title']
                print('Nowy news: ', title)
                if title == self._stop_title:
                    do_run = False
                    break
                link = f"https://www.funker530.com/video/{article['slug'] if 'slug' in article else None}/"
                description = article['description'] if 'description' in article else 'Brak opisu.'
                feed_gen.add_item(title, link, description)

            i += 1

            # pobieraj tylko 2 najnowsze strony,
            # stosowanie semafora nie ma sensu bo sortowanie po stronie serwera jest zjebane
            if i > 5:
                break

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')


if __name__ == '__main__':
    s = Spider('https://www.funker530.com/')
    s.start()
