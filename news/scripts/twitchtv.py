from os import getenv
import requests
import feedgenerator


class Spider:
    def __init__(self, start_url, stop_title=''):
        # wyodrębnij username z url do kanału na twitch.tv
        username = start_url.split('/')[-1]

        self._stop_title = stop_title
        self._client_id = getenv('TWITCH_CLIENT_ID')
        self._client_secret = getenv('TWITCH_CLIENT_SECRET')
        self._access_token = self._get_oauth_token()
        self._user_id = self._get_user_id(username)

    def _get_oauth_token(self):
        response = requests.post(f'https://id.twitch.tv/oauth2/token?client_id={self._client_id}&client_secret={self._client_secret}&grant_type=client_credentials')
        return response.json()['access_token']

    def _get_user_id(self, username):
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Client-Id': self._client_id
        }
        response = requests.get(f'https://api.twitch.tv/helix/users?login={username}', headers=headers)
        return response.json()['data'][0]['id']

    def _get_videos(self, stop_title=''):
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Client-Id': self._client_id
        }
        pagination_cursor = None

        while True:
            # tworzenie adresu
            url = f'https://api.twitch.tv/helix/videos?user_id={self._user_id}'
            if pagination_cursor is not None:
                url += f'&after={pagination_cursor}'

            response = requests.get(url, headers=headers)
            json = response.json()
            pagination_cursor = json['pagination']['cursor'] if 'cursor' in json['pagination'] else None

            for vid in json['data']:
                if self._stop_title == vid['title']:
                    return

                print('Nowy news: ', vid['title'])
                yield vid

            # jeśli nie ma kolejnej strony paginacji to już koniec
            if pagination_cursor is None:
                break

    def start(self):
        feed_gen = feedgenerator.Rss201rev2Feed('twitch.tv', 'https://twitch.tv', 'RSS dla twitch.tv')

        for vod in self._get_videos():
            print('Nowy news: ', vod['title'])
            feed_gen.add_item(vod['title'], vod['url'], vod['description'])

        # uczyń ostatni dodany pierwszym aby roadblock móg działać
        feed_gen.items.reverse()

        return feed_gen.writeString('utf-8')


if __name__ == '__main__':
    from pathlib import Path
    import dotenv
    from os import getenv

    dotenv.load_dotenv(dotenv_path=Path.home() / '.config/news/.env')
    print(getenv('TWITCH_CLIENT_ID'))

    app = Spider('https://twitch.tv/aikoiemil', 'Emil Jedi monkaS')
    app.start()
