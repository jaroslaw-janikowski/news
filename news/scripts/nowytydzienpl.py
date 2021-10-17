import json
import requests
import feedgenerator
import bs4


class Spider:
    def __init__(self, start_url, stop_title=''):
        self._start_url = start_url
        self._stop_title = stop_title

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('nowytydzien.pl', 'https://nowytydzien.pl', 'RSS dla nowytydzien.pl')
        do_run = True
        i = 1
        while do_run:
            url = 'https://www.nowytydzien.pl/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=8.8'
            data = {
                'action': 'td_ajax_loop',
                'loopState[sidebarPosition]': '',
                'loopState[moduleId]': 10,
                'loopState[currentPage]': i,
                'loopState[max_num_pages]': 1437,
                'loopState[atts][category_id]': 6,
                'loopState[atts][offset]': 3,
                'loopState[ajax_pagination_infinite_stop]': 3,
                'loopState[server_reply_html_data]': ''
            }
            print('pobieram porcję: ', i)
            resp = requests.post(url, data=data)
            html = resp.json()['server_reply_html_data']

            # czy to już koniec paginacji artykułów?
            if html == '':
                print('Kończę: status 404')
                break

            doc = bs4.BeautifulSoup(html, 'html.parser')

            # znajdź wszystkie posty i dodaj do dokumentu wynikowego
            for div in doc.select('div.item-details'):
                title = div.select('h3 > a')[0]['title']
                print('Nowy news: ', title)
                if title == self._stop_title:
                    do_run = False
                    break
                link = div.select('h3 > a')[0]['href']
                description = div.select('div.td-excerpt')[0].text
                feed_gen.add_item(title, link, description)

            i += 1

            # limit dokumnetów do pobrania
            if i > 10:
                break

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')


if __name__ == '__main__':
    s = Spider('https://www.nowytydzien.pl/kategoria/chelm/', 'Medale za służbę')
    s.start()
