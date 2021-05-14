#!/usr/bin/env python3

import sqlite3
import threading
import subprocess
import webbrowser
import html.parser
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk


style = {
    'news.viewer.text': {
        'bg': '#000000',
        'fg': '#2eff7b',
        'font': ('roboto', 16, 'normal')
    }
}


class StreamlinkViewer(threading.Thread):
    def __init__(self, url, quality='worst', **kwargs):
        super().__init__()

        # self.daemon = True  # powoduje dziwne zawieszenia po kilku odtworzeniach filmów

        self._url = url
        self._quality = quality

        self._on_start = kwargs['on_start'] if 'on_start' in kwargs else None

    def run(self):
        self._run_streamlink(self._url, self._quality)

    def _run_streamlink(self, url, quality='worst'):
        # run process in blocking mode
        with subprocess.Popen(['streamlink', url, quality, '-p', 'mpv'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as p:
            while p.stdout:
                # read lines from stdout
                l = p.stdout.readline()
                if l == b'':
                    break

                # if certain line is detected then stop blocking main window
                if b'Writing stream to output' in l:
                    if callable(self._on_start):
                        self._on_start()


class NewsParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = ''

        self._processed_tags = []  # debug

    def handle_endtag(self, tag):
        if tag not in self._processed_tags:
            print(f'Unprocessed tag: {tag}')

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self._text += '\n'

        self._processed_tags = ['br']  # debug

    def handle_data(self, data):
        self._text += data

    def get_text(self):
        return self._text.strip()


class WaitDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.withdraw()
        self.title('Proszę czekać...')
        self.geometry('250x120')
        self.transient(master)
        self.bind('<Escape>', self._on_escape)

        label = tk.Label(self, text='Operacja w toku, proszę czekać...')
        label.pack(side=tk.TOP, fill=tk.X, expand=True)

    def _on_escape(self, event=None):
        self.hide()

    def show(self):
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        # self.wait_window()

    def hide(self):
        self.grab_release()
        self.withdraw()


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry('640x480+100+100')
        self.title('news')
        self.bind('<Control-q>', self._on_quit)

        self.config(menu=self._create_main_menu())

        paned_h = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_h.add(self._create_channel_manager(paned_h), weight=0)
        paned_h.add(self._create_news_viewer(paned_h), weight=1)
        paned_h.pack(fill=tk.BOTH, expand=True)

        self._db_connection = sqlite3.connect(Path.home() / '.config' / 'news' / 'news.sqlite3')
        self._db_connection.row_factory = sqlite3.Row
        self._db_cursor = self._db_connection.cursor()
        # self._db_cursor.execute('pragma journal_mode=wal')

        self._wait_dlg = WaitDialog(self)
        self._current_news = None

        self._load_resources()
        self._load_data()

    def _load_resources(self):
        self._icons = {
            'folder': ImageTk.PhotoImage(Image.open('/usr/share/icons/news/folder.png')),
            'rss': ImageTk.PhotoImage(Image.open('/usr/share/icons/news/rss.png')),
            'youtube': ImageTk.PhotoImage(Image.open('/usr/share/icons/news/youtube.png')),
            'twitch': ImageTk.PhotoImage(Image.open('/usr/share/icons/news/twitch.png'))
        }

    def _load_data(self):
        # dodaj foldery
        folders = {}
        for row in self._db_cursor.execute('select * from folder').fetchall():
            i = self._channel_manager_treeview.insert('', tk.END, text=row['title'], image=self._icons['folder'])
            folders[row['id']] = i
            self._channel_manager_folders[row['title']] = i

        # dodaj kanały
        self._db_cursor.execute('select *, count(news.id) as news_count from channel join news on news.channel_id = channel.id where news.is_read = 0 group by channel.id')
        for row in self._db_cursor.fetchall():
            parent_id = ''
            if row['folder_id'] is not None:
                parent_id = folders[row['folder_id']]

            # wybór ikony ze względu na źródło danych
            icon = None
            if 'youtube' in row['url']:
                icon = self._icons['youtube']
            elif 'twitch' in row['url']:
                icon = self._icons['twitch']
            else:
                icon = self._icons['rss']

            i = self._channel_manager_treeview.insert(parent_id, tk.END, row['id'], text=row['title'], image=icon, values=(row['news_count'],))
            self._channel_manager_channels[row['title']] = i

    def _create_channel_manager(self, master):
        self._channel_manager_channels = {}
        self._channel_manager_folders = {}

        frame = tk.Frame(master, width=200)
        self._channel_manager_treeview = ttk.Treeview(frame, columns=('#news-count',))
        self._channel_manager_treeview.column('#news-count', width=40, stretch=tk.YES)
        self._channel_manager_treeview.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar_v = tk.Scrollbar(frame, orient=tk.VERTICAL)
        scrollbar_v.grid(row=0, column=1, sticky=tk.NS)
        scrollbar_h = tk.Scrollbar(frame, orient=tk.HORIZONTAL)
        scrollbar_h.grid(row=1, column=0, sticky=tk.EW)

        self._channel_manager_treeview['yscrollcommand'] = scrollbar_v.set
        self._channel_manager_treeview['xscrollcommand'] = scrollbar_h.set
        scrollbar_v['command'] = self._channel_manager_treeview.yview
        scrollbar_h['command'] = self._channel_manager_treeview.xview

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        return frame

    def _create_news_viewer(self, master):
        frame = tk.Frame(master)
        self._news_viewer_title = tk.Label(frame, **style['news.viewer.text'])
        self._news_viewer_title.pack(anchor=tk.NW, fill=tk.X, expand=False)
        self._news_viewer_text = ScrolledText(frame, wrap=tk.WORD, **style['news.viewer.text'])
        self._news_viewer_text.pack(fill=tk.BOTH, expand=True)
        return frame

    def _create_main_menu(self):
        menubar = tk.Menu(self, tearoff=False)

        app_menu = tk.Menu(self, tearoff=False)
        app_menu.add_command(label='Update all', command=self._on_update_all, accelerator='Ctrl-U')
        self.bind('<Control-u>', self._on_update_all)
        app_menu.add_separator()
        app_menu.add_command(label='Quit', command=self._on_quit, accelerator='Ctrl-Q')
        self.bind('<Control-q>', self._on_quit)
        menubar.add_cascade(label='App', menu=app_menu)

        channel_menu = tk.Menu(self, tearoff=False)
        channel_menu.add_command(label='Add channel', command=self._on_add_channel, accelerator='Ctrl-N')
        self.bind('<Control-n>', self._on_add_channel)
        channel_menu.add_command(label='Add folder', command=self._on_add_folder, accelerator='Ctrl-Shift-N')
        self.bind('<Control-Shift-n>', self._on_add_folder)
        menubar.add_cascade(label='Channel', menu=channel_menu)

        news_menu = tk.Menu(self, tearoff=False)
        news_menu.add_command(label='Next', command=self._on_next_news, accelerator='N')
        self.bind('n', self._on_next_news)
        news_menu.add_command(label='Goto', command=self._on_goto_news, accelerator='G')
        self.bind('g', self._on_goto_news)
        news_menu.add_command(label='Streamlink worst', command=self._on_streamlink_worst, accelerator='1')
        self.bind('1', self._on_streamlink_worst)
        news_menu.add_command(label='Streamlink 360p', command=self._on_streamlink_360p, accelerator='2')
        self.bind('2', self._on_streamlink_360p)
        news_menu.add_separator()
        news_menu.add_command(label='Mark all as read', command=self._on_mark_all_as_read, accelerator='Ctrl-M')
        self.bind('<Control-m>', self._on_mark_all_as_read)
        menubar.add_cascade(label='News', menu=news_menu)

        help_menu = tk.Menu(self, tearoff=False)
        help_menu.add_command(label='About', command=self._on_about)

        menubar.add_cascade(label='Help', menu=help_menu)

        return menubar

    def _on_about(self, event=None):
        pass

    def _on_mark_all_as_read(self, event=None):
        pass

    def _on_streamlink_360p(self, event=None):
        if self._current_news:
            self._wait_dlg.show()
            v = StreamlinkViewer(self._current_news['url'], '360p', on_start=self._wait_dlg.hide)
            v.start()

    def _on_streamlink_worst(self, event=None):
        if self._current_news:
            self._wait_dlg.show()
            v = StreamlinkViewer(self._current_news['url'], 'worst', on_start=self._wait_dlg.hide)
            v.start()

    def _on_goto_news(self, event=None):
        if self._current_news:
            webbrowser.open_new_tab(self._current_news['url'])

    def _on_next_news(self, event=None):
        # oznacz poprzedni aktywny news jako przeczytany
        if self._current_news:
            self._db_cursor.execute('update news set is_read = 1 where id = ?', (self._current_news['id'],))

            # zmniejsz o 1 ilość nieprzeczytanych newsów w tym kanale
            tree_item = self._channel_manager_treeview.selection()[0]
            news_count = int(self._channel_manager_treeview.set(tree_item, '#news-count')) - 1
            if news_count >= 0:
                self._channel_manager_treeview.set(tree_item, '#news-count', news_count)

        # znajdź kolejny news
        news = self._db_cursor.execute('select news.*, channel.title as channel_title from news join channel on channel.id = news.channel_id where is_read = 0 order by quality desc limit 1').fetchone()

        self._current_news = news

        if news is None:
            return 'break'

        self._set_news(news)

    def _set_news(self, news):
        '''Wybiera news jako aktywny w programie. Parametr to słownik z bazy z tabeli news.'''
        # zaznacz i pokaż kanał w drzewie kanałów
        sel_item = self._channel_manager_channels[news['channel_title']]
        self._channel_manager_treeview.selection_set(sel_item)
        self._channel_manager_treeview.see(sel_item)

        # parsuj HTML
        parser = NewsParser()
        parser.feed(news['summary'])

        # załaduj treść do przeglądarki
        self._news_viewer_text.delete('1.0', tk.END)
        self._news_viewer_text.insert(tk.END, parser.get_text())
        self._news_viewer_title['text'] = news['title']

    def _on_add_folder(self, event=None):
        pass

    def _on_add_channel(self, event=None):
        pass

    def _on_update_all(self):
        pass

    def _on_quit(self, event=None):
        self._db_connection.commit()
        self._db_connection.close()
        self.quit()


if __name__ == '__main__':
    app = Application()
    app.mainloop()
