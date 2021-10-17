import requests
import feedgenerator
import bs4


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('strefa44.pl', 'https://strefa44.pl', 'RSS dla strefa.pl')
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
            for div in doc.select('.post'):
                title = div.select('div.title > h2 > a')[0].text
                print('Nowy news: ', title)
                if title == self._stop_title:
                    do_run = False
                    break
                link = div.select('div.title > h2 > a')[0]['href']
                description = div.select('div.cover > div.entry > p')[0].text
                feed_gen.add_item(title, link, description)

            i += 1

            if i > 10:
                break

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')

if __name__ == '__main__':
    s = Spider('https://strefa44.pl/', 'Mapa ciemnej materii ujawnia ukryte mosty między galaktykami')
    s.start()
