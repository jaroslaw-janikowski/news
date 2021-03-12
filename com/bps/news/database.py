import os
import os.path
import sqlite3
import collections


class Database:
    def __init__(self, filename=None):
        self._connection = None

        if isinstance(filename, str):
            self.open_file(filename)

    def open_file(self, filename):
        # zamknij plik jeśli bł otwarty
        if self._connection:
            self.close()

        self._connection = sqlite3.connect(filename, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._cursor = self._connection.cursor()

        # sanitizers

    def _sanitize_title(self, title):
        return title.replace('\n', ' ')

    def get_channels(self):
        return self._cursor.execute('select channel.id, channel.title, channel.url, channel.channel_type, (select count(id) from news where channel_id = channel.id and is_read = 0) as unread_count, folder.title as folder_title from channel left join folder on folder.id = channel.folder_id order by channel.title').fetchall()

    def add_channel(self, title, url, channel_type):
        self._cursor.execute('insert into channel(title, url, channel_type) values (?, ?, ?)', (title, url, channel_type))
        self._connection.commit()
        return True

    def remove_channel(self, channel_title):
        self._cursor.execute('delete from channel where title = ?', (channel_title,))
        self._connection.commit()
        return True

    def move_channel(self, channel_title, folder_title):
        self._cursor.execute('update channel set folder_id = (select id from folder where title = ?) where title = ?', (folder_title, channel_title))
        self._connection.commit()
        return True

    def add_news(self, channel_title, news):
        # get channel id
        channel_id = self._cursor.execute('select id from channel where title = ?', (channel_title,)).fetchone()[0]

        # create list of values
        insert_values = []
        for d in news:
            # sanityzuj tytuł
            title = self._sanitize_title(d['title'])
            insert_values.append((channel_id, title, d['link'], d['summary']))

        # build query with placeholders
        placeholders = ["(?, ?, ?, ?)" for t in insert_values]
        insert_sql = f"""
            insert or ignore into news(
                channel_id,
                title,
                url,
                summary
            )
            values {','.join(placeholders)}
        """

        # insert
        try:
            self._cursor.execute(insert_sql, [d for sublist in insert_values for d in sublist])
            # self._connection.commit()
        except sqlite3.OperationalError:
            pass

    def get_news(self, channel_title):
        return self._cursor.execute('''
            select news.id, news.channel_id, news.title, news.url
            from news
            left join channel on channel.id = news.channel_id
            where
                channel.title = ?
                and is_read = 0 limit 100
        ''', (channel_title,)).fetchall()

    def get_news_from_id(self, news_id):
        return self._cursor.execute('select * from news where id = ?', (news_id,)).fetchone()

    def get_news_next(self, channel_name=None, random=False):
        params = []

        sql = '''
            select news.*, channel.title as channel_title
            from news
            inner join channel on channel.id = news.channel_id
            where is_read  = 0'''

        # czy brać pod uwagę wszystkie kanały czy jeden wybrany
        if channel_name:
            sql += ' and channel.title = ?'
            params.append(channel_name)

        sql += ' order by quality desc'

        # czy ma być losowy?
        if random:
            sql += ', random() '

        # powinien być tylko jeden
        sql += ' limit 1'

        return self._cursor.execute(sql, params).fetchone()

    def recommend_count_words(self, text):
        # usuń znaki specjalne
        spec = '~!@#$%^&*()_+{}:"|<>?`-=[];\'\\,./'
        for spec_char in spec:
            text = text.replace(spec_char, '')

        # usuń słowa 3 znakowe lub krótsze
        text = text.split()
        text = [word for word in text if len(word) > 3]

        # policz słowa
        c = collections.Counter(text)
        return c.most_common()

    def recommend_update_words(self, words_count):
        # aktualizuj tabelę words
        for word, count in words_count:
            sql = 'insert into words(word, weight) values(?, ?) on conflict(word) do update set weight = weight + ? where word = ?'
            self._cursor.execute(sql, (word, count, count, word))

    def recommend_update_quality_all(self):
        '''Aktualizuje pole quality dla wszystkich nie przeczytanych newsów'''
        sql = "select news.id, (channel.title || ' ' || news.title || ' ' || summary) as text from news join channel on channel.id = news.channel_id where is_read = 0"
        q = self._cursor.execute(sql)
        for row in q.fetchall():
            words = [f'"{i}"' for i, c in self.recommend_count_words(row['text'])]
            words_list = f'({",".join(words)})'
            new_quality = self._cursor.execute(f'select sum(weight) from words where word in {words_list}').fetchone()[0]
            if new_quality is not None:
                self._cursor.execute('update news set quality = ? where id = ?', (new_quality, row['id']))

    def recommend_update_quality(self, word):
        # znajdź wszystkie nie przejrzane zawierajace słowo
        sql = "select news.id, (channel.title || ' ' || news.title || ' ' || summary) as text from news join channel on channel.id = news.channel_id where is_read = 0 and (channel.title || ' ' || news.title || ' ' || summary) like ? collate nocase"
        q = self._cursor.execute(sql, (f'%{word}%',))
        for row in q:
            words = [f'"{i}"' for i, c in self.recommend_count_words(row['text'])]
            words_list = f'({",".join(words)})'
            new_quality = self._cursor.execute(f'select sum(weight) from words where word in {words_list}').fetchone()[0]
            if new_quality is not None:
                self._cursor.execute('update news set quality = ? where id = ?', (new_quality, row['id']))

    def commit(self):
        self._connection.commit()

    def get_news_count(self):
        return self._cursor.execute('''
            SELECT channel.title, count(news.id)
            from news
            left join channel on channel.id = news.channel_id
            where
                is_read = 0
            group by channel.title
        ''').fetchall()

    def set_all_as_read(self):
        self._cursor.execute('update news set is_read = 1 where is_read = 0')
        self._connection.commit()

    def set_news_as_read(self, note_id):
        self._cursor.execute('update news set is_read = 1 where id = ?', (note_id,))
        self._connection.commit()

    def close(self):
        self._connection.commit()
        self._connection.close()

    @classmethod
    def create_new(cls, filename):
        '''Tworzy nową bazę danych pod wskazaną ścieżką i nazwą pliku.'''
        sql = [
            '''
            create table folder(
                id integer primary key autoincrement,
                title varchar(100) not null unique,
                expanded boolean not null default 0
            );
            ''',
            '''
            create table channel(
                id integer primary key autoincrement,
                title varchar(100) not null,
                url varchar(512) not null,
                folder_id integer,
                foreign key (folder_id) references folder(id)
            );
            ''',
            '''
            create table news(
                id integer primary key autoincrement,
                channel_id int not null,
                title varchar(256) not null,
                url varchar(512) not null unique,
                summary text not null,
                is_read boolean default 0,
                foreign key (channel_id) references channel(id)
            );
            '''
        ]

        # utwórz ścieżkę katalogów do pliku jeśli nie istnieją
        dir_ = os.path.split(filename)[0]
        if dir_ is not None:
            os.makedirs(dir_, 0o775, True)

        # utwórz plik bazy
        try:
            with sqlite3.connect(filename) as c:
                c = c.cursor()
                for s in sql:
                    c.execute(s)
        except:
            os.remove(filename)

    def get_folders(self):
        return self._cursor.execute('select title, expanded from folder order by title').fetchall()

    def add_folder(self, title):
        self._cursor.execute('insert into folder(title) values(?)', (title,))
        self._connection.commit()
        return True

    def set_folder_expanded(self, folder_title, is_expanded):
        self._cursor.execute('update folder set expanded = ? where title = ?', (is_expanded, folder_title))
        self._connection.commit()
