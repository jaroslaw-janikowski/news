import requests
import feedgenerator
import bs4


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    @classmethod
    def _download(cls, url):
        resp = requests.get(url)
        return resp.text

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('zbiam.pl', 'https://zbiam/pl', 'RSS dla zbiam.pl')
        do_run = True
        i = 1
        while do_run:
            url = f'{self._start_url}page/{i}/'
            print('pobieram: ', url)
            resp = requests.get(url)

            # czy to już koniec paginacji artykułów?
            if resp.status_code == 404:
                print('Kończę: status 404')
                break

            doc = bs4.BeautifulSoup(resp.text, 'html.parser')

            # znajdź wszystkie posty i dodaj do dokumentu wynikowego
            for div in doc.select('.oxy-post'):
                title = div.select('a.oxy-post-title:nth-of-type(1)')[0].text
                print('Nowy news: ', title)
                if title == self._stop_title:
                    do_run = False
                    break
                link = div.select('a.oxy-post-title:nth-of-type(1)')[0]['href']
                description = title
                feed_gen.add_item(title, link, description)

            i += 1

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')


if __name__ == '__main__':
    urls = [
        ('https://zbiam.pl/artykuly-kategoria/marynarka-wojenna/', 'Przyszłość rosyjskich sił podwodnych'),
        ('https://zbiam.pl/artykuly-kategoria/sily-powietrzne/', 'Bayraktar TB2 jako system operacyjny'),
        ('https://zbiam.pl/artykuly-kategoria/przemysl-zbrojeniowy/', 'JFD – lider produkcji systemów'),
        ('https://zbiam.pl/artykuly-kategoria/wojska-ladowe/', 'Bułgaria modernizuje T-72')
    ]

    for url, stop_title in urls:
        s = Spider(url, stop_title)
        s.start()
