#!/usr/bin/env python3

import io
import re
import sqlite3
import requests
import threading
import importlib
import subprocess
import feedparser
import webbrowser
import html.parser
import dotenv
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesno, showerror, showinfo
from pathlib import Path
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from parentalctl import QUALITY_TRESHOLD


style = {
    'news.viewer.text': {
        'bg': '#000000',
        'fg': '#2eff7b',
        'font': ('roboto', 16, 'normal')
    }
}
dotenv.load_dotenv(dotenv_path=Path.home() / '.config/news/.env')


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
        fallback_to_youtube_dl = False

        # run process in blocking mode
        with subprocess.Popen(['streamlink', url, quality, '-p', 'mpv'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as p:
            while p.stdout:
                # read lines from stdout
                l = p.stdout.readline()
                if l == b'':
                    break

                # if certain line is detected then stop blocking main window
                elif b'Writing stream to output' in l:
                    if callable(self._on_start):
                        self._on_start()

                # youtube premiere
                elif l.startswith(b'[plugins.youtube][error] Could not get video info: Premiera za'):
                    showinfo('Brak materiału wideo', 'Premiera jeszcze nie nastąpiła.')
                    p.terminate()
                    self._on_start()
                    return

                # protected youtube video shoul be downloaded by youtube-dl
                elif url.startswith('https://www.youtube.com/watch') and b'[cli][error] This plugin does not support protected videos, try youtube-dl instead' in l:
                    fallback_to_youtube_dl = True
                    p.terminate()
                    break

        # youtube-dl fallback mode for "protected videos"
        if fallback_to_youtube_dl:
            quality = 'worst' if quality == 'worst' else '18'
            subprocess.Popen([f'mpv `youtube-dl -g -f {quality} {url}`'], shell=True)
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


class AboutDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        self.title('About')
        self.bind('<Escape>', self._on_ok_button)

        label = tk.Label(self, text='Authors:')
        label.pack(fill=tk.X)

        text = tk.Text(self)
        text.insert(tk.END, '''Authors:
- jaroslaw.janikowski@gmail.com (programming)
- www.freepik.com(icons) ''')
        text['state'] = tk.DISABLED
        text.pack(fill=tk.BOTH, expand=True)

        self._ok_button = tk.Button(self, text='OK', command=self._on_ok_button)
        self._ok_button.pack(anchor=tk.E)

        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    def _on_ok_button(self, event=None):
        self.grab_release()
        self.destroy()


class FolderDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('Add / edit folder')
        self.transient(master)
        self.bind('<Escape>', self._on_cancel)
        self._result = None

        tk.Label(self, text='Folder title').pack(fill=tk.X, padx=2)
        self._folder_title_entry = tk.Entry(self)
        self._folder_title_entry.bind('<FocusOut>', self._validate)
        self._folder_title_entry.pack(fill=tk.X, padx=2)
        self._folder_title_entry.focus()

        button_cancel = tk.Button(self, text='Cancel', command=self._on_cancel)
        button_cancel.pack(fill=tk.X, padx=2)

        self._button_ok = tk.Button(self, text='Ok', state=tk.DISABLED, command=self._on_apply)
        self._button_ok.pack(fill=tk.X, padx=2)

    def _on_apply(self, event=None):
        self._result = {
            'title': self._folder_title_entry.get()
        }
        self.destroy()

    def _validate(self, *args):
        b = bool(self._folder_title_entry.get())
        self._button_ok['state'] = (tk.NORMAL if b else tk.DISABLED)

    def _on_cancel(self, event=None):
        self._result = None
        self.destroy()

    def run(self):
        self.grab_set()
        self.wait_window()
        self.grab_release()
        return self._result


class ChannelDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title('Add / edit channel info')
        self.transient(master)
        self.bind('<Escape>', self._on_cancel)

        self._result = False  # naciśnięto escape lub cancel

        tk.Label(self, text='Channel title').pack(fill=tk.X, padx=2)
        self._channel_title_entry = tk.Entry(self)
        self._channel_title_entry.bind('<FocusOut>', self._validate)
        self._channel_title_entry.pack(fill=tk.X, padx=2)
        self._channel_title_entry.focus()

        tk.Label(self, text='URL').pack(fill=tk.X, padx=2)
        self._channel_url_entry = tk.Entry(self)
        self._channel_url_entry.bind('<FocusOut>', self._validate)
        self._channel_url_entry.pack(fill=tk.X, padx=2)

        button_cancel = tk.Button(self, text='Cancel', command=self._on_cancel)
        button_cancel.pack(fill=tk.X, padx=2)

        self._button_ok = tk.Button(self, text='Ok', state=tk.DISABLED, command=self._on_apply)
        self._button_ok.pack(fill=tk.X, padx=2)

    def _validate(self, *args):
        self._autopopulate_form()

        b = all([
            self._channel_title_entry.get(),
            self._channel_url_entry.get()
        ])

        self._button_ok['state'] = (tk.NORMAL if b else tk.DISABLED)

    def _autopopulate_form(self):
        url = self._channel_title_entry.get()

        # link do kanału youtube
        m = re.match(r'^https:\/\/www\.youtube\.com\/channel\/([a-zA-Z0-9_\-]+)$', url)
        if m is not None:
            channel_id = m.group(1)
            self._channel_url_entry.delete(1, tk.END)
            self._channel_url_entry.insert(tk.END, f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}')
            self._channel_title_entry.delete(1, tk.END)
            self._channel_title_entry.insert(tk.END, channel_id)
            return True

        # link do usera youtube
        m = re.match(r'^https:\/\/www\.youtube\.com\/user\/([a-zA-Z0-9_\-]+)$', url)
        if m is not None:
            user_id = m.group(1)
            self._channel_url_entry.delete(1, tk.END)
            self._channel_url_entry.insert(tk.END, f'https://www.youtube.com/feeds/videos.xml?user={user_id}')
            self._channel_title_entry.delete(1, tk.END)
            self._channel_title_entry.insert(tk.END, user_id)
            return True

    def _on_cancel(self, event=None):
        self._result = None
        self.destroy()

    def _on_apply(self, event=None):
        self._result = {
            'title': self._channel_title_entry.get(),
            'url': self._channel_url_entry.get()
        }
        self.destroy()

    def set_data(self, channel):
        self._channel_title_entry.set(channel['title'])
        self._channel_url_entry.set(channel['url'])

    def run(self):
        self.grab_set()
        self.wait_window()
        self.grab_release()
        return self._result


class ProgressDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        # self.geometry('640x480')
        self.title('Operation progress...')
        self.transient(master)
        self.bind('<Configure>', self._on_resize)
        self.bind('<Escape>', self._on_escape)

        progress_label = tk.Label(self, text='Progress')
        progress_label.grid(row=0, column=0, sticky=tk.EW, padx=2, pady=2)
        self._progressbar = ttk.Progressbar(self, value=0)
        self._progressbar.grid(row=1, column=0, sticky=tk.EW, padx=2, pady=2)
        self._text = tk.Text(self)
        self._text.grid(row=2, column=0, sticky=tk.NSEW, padx=2, pady=2)
        cancel_btn = tk.Button(self, text='Cancel', command=self._on_escape)
        cancel_btn.grid(row=3, column=0, sticky=tk.E, padx=2, pady=2)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def _on_resize(self, event):
        self.update_idletasks()

    def _on_escape(self, event=None):
        self.destroy()

    def set_position(self, pos, msg=None):
        self._progressbar['value'] = pos
        if msg:
            self._text.insert(tk.END, msg+'\n')
            self._text.see(tk.END)
        self.update_idletasks()

    def show(self):
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        # self.wait_window()

    def destroy(self):
        self.withdraw()
        self.grab_release()
        super().destroy()


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

        self._load_resources()

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

        self._load_data()

    def _load_resources(self):
        RES_DIR = Path('/', 'usr', 'local', 'lib', 'news', 'res', 'icons')
        self._icons = {
            'folder': ImageTk.PhotoImage(Image.open(RES_DIR / 'folder.png')),
            'rss': ImageTk.PhotoImage(Image.open(RES_DIR / 'rss.png')),
            'youtube': ImageTk.PhotoImage(Image.open(RES_DIR / 'youtube.png')),
            'twitch': ImageTk.PhotoImage(Image.open(RES_DIR / 'twitch.png')),
            'like': ImageTk.PhotoImage(Image.open(RES_DIR / 'like.png'))
        }

    def _load_data(self):
        # dodaj foldery
        folders = {}
        for row in self._db_cursor.execute('select * from folder').fetchall():
            i = self._channel_manager_treeview.insert('', tk.END, text=row['title'], image=self._icons['folder'])
            folders[row['id']] = i
            self._channel_manager_folders[row['title']] = i
            self._channel_manager_title_type[row['title']] = 'folder'

        # dodaj kanały
        self._db_cursor.execute('select channel.*, coalesce(a.news_count1, 0) news_count from channel left join (select channel_id, count(id) news_count1 from news where news.is_read = 0 group by channel_id) a on channel.id = a.channel_id')
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
            self._channel_manager_title_type[row['title']] = 'channel'

    def _create_channel_manager(self, master):
        self._channel_manager_channels = {}
        self._channel_manager_folders = {}
        self._channel_manager_title_type = {}

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

        # drag and drop
        self._dragged_item = None
        self._channel_manager_treeview.bind('<ButtonPress-1>', self._on_channel_manager_button_press)
        self._channel_manager_treeview.bind('<ButtonRelease-1>', self._on_channel_manager_button_release)
        self._channel_manager_treeview.bind('<B1-Motion>', self._on_channel_manager_motion)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        return frame

    def _on_channel_manager_button_press(self, event):
        self._dragged_item = self._channel_manager_treeview.identify_row(event.y)

    def _on_channel_manager_button_release(self, event):
        target = self._channel_manager_treeview.identify_row(event.y)

        # target nie może trafić do samego siebie
        if target == self._dragged_item:
            return 'break'

        # target musi być folderem
        if target not in self._channel_manager_folders.values():
            return 'break'

        self._channel_manager_treeview.move(self._dragged_item, target, tk.END)

        # zmiana folderu w bazie
        folder_title = tuple(k for k, v in self._channel_manager_folders.items() if v == target)[0]
        channel_title = tuple(k for k, v in self._channel_manager_channels.items() if v == self._dragged_item)[0]
        self._db_cursor.execute('update channel set folder_id = (select id from folder where title = ? limit 1) where title = ?', (folder_title, channel_title))

    def _on_channel_manager_motion(self, event):
        self._channel_manager_treeview['cursor'] = 'plus'

    def _create_news_viewer(self, master):
        frame = tk.Frame(master)
        self._news_viewer_title = tk.Text(frame, wrap=tk.WORD, height=3, state=tk.DISABLED, cursor='hand1', **style['news.viewer.text'])
        self._news_viewer_title.bind('<Button-1>', self._on_goto_news)
        self._news_viewer_title.grid(row=0, column=0, sticky=tk.NSEW)

        self._vote_up_btn = tk.Button(frame, text='0', command=self._on_vote_up, image=self._icons['like'], compound=tk.LEFT)
        self.bind('=', self._on_vote_up)
        self._vote_up_btn.grid(row=0, column=1, sticky=tk.NSEW)

        self._news_viewer_text = ScrolledText(frame, wrap=tk.WORD, state=tk.DISABLED, **style['news.viewer.text'])
        self._news_viewer_text.bind('<Up>', self._on_up_key)
        self._news_viewer_text.bind('<Down>', self._on_down_key)
        self._news_viewer_text.bind('<Home>', self._on_home_key)
        self._news_viewer_text.bind('<End>', self._on_end_key)
        self._news_viewer_text.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)

        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)

        return frame

    def _on_end_key(self, event=None):
        # self._news_viewer_text.yview_moveto(1.0)
        self._news_viewer_text.see(tk.END)

    def _on_home_key(self, event=None):
        self._news_viewer_text.yview_moveto(0)

    def _on_vote_up(self, event=None):
        channel_title = self._current_news['channel_title']
        text = f'{channel_title} {self._current_news["title"]} {self._current_news["summary"]}'.lower()

        r = self._recommend_count_words(text)
        self._recommend_update_words(r)
        for word in r:
            self._recommend_update_quality(word)

        # uaktualnij wartość na przycisku
        self._current_news = self._db_cursor.execute('select news.*, channel.title as channel_title from news join channel on news.channel_id = channel.id where news.id = ? limit 1', (self._current_news['id'],)).fetchone()
        self._vote_up_btn['text'] = f"{self._current_news['quality']:.2f}"

    def _on_down_key(self, event=None):
        self._news_viewer_text.yview_scroll(1, 'units')

    def _on_up_key(self, event=None):
        self._news_viewer_text.yview_scroll(-1, 'units')

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
        channel_menu.add_command(label='Remove', command=self._on_remove_channel_or_folder, accelerator='Del')
        self.bind('<Delete>', self._on_remove_channel_or_folder)
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
        news_menu.add_command(label='Streamlink 480p', command=self._on_streamlink_480p, accelerator='3')
        self.bind('3', self._on_streamlink_480p)
        news_menu.add_separator()
        news_menu.add_command(label='Mark all as read', command=self._on_mark_all_as_read, accelerator='Ctrl-M')
        self.bind('<Control-m>', self._on_mark_all_as_read)
        menubar.add_cascade(label='News', menu=news_menu)

        help_menu = tk.Menu(self, tearoff=False)
        help_menu.add_command(label='About', command=self._on_about)

        menubar.add_cascade(label='Help', menu=help_menu)

        return menubar

    def _on_about(self, event=None):
        dlg = AboutDialog(self)

    def _on_mark_all_as_read(self, event=None):
        self._db_cursor.execute('update news set is_read = 1')
        for channel_title, channel_iid in self._channel_manager_channels.items():
            self._channel_manager_treeview.set(channel_iid, '#news-count', 0)

    def _on_streamlink_360p(self, event=None):
        if self._current_news:
            self._wait_dlg.show()
            v = StreamlinkViewer(self._current_news['url'], '360p', on_start=self._wait_dlg.hide)
            v.start()

    def _on_streamlink_480p(self, event=None):
        if self._current_news:
            self._wait_dlg.show()
            v = StreamlinkViewer(self._current_news['url'], '480p', on_start=self._wait_dlg.hide)
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
            # przywróć zaznaczenie na element z którego pochodzi bieżący news (ktoś mógł zmienić pomiędzy notatkami)
            self._select_channel_news(self._current_news)

            # oznacz jako przeczytany w bazie
            self._db_cursor.execute('update news set is_read = 1 where id = ?', (self._current_news['id'],))

            # zmniejsz o 1 ilość nieprzeczytanych newsów w tym kanale
            sel = self._channel_manager_treeview.selection()
            if sel:
                tree_item = sel[0]
                news_count = int(self._channel_manager_treeview.set(tree_item, '#news-count')) - 1
                if news_count >= 0:
                    self._channel_manager_treeview.set(tree_item, '#news-count', news_count)

        # znajdź kolejny news
        news = self._db_cursor.execute('select news.*, channel.title as channel_title from news join channel on channel.id = news.channel_id where is_read = 0 and quality < ? order by quality asc limit 1', (QUALITY_TRESHOLD,)).fetchone()

        self._current_news = news

        if news is None:
            return 'break'

        self._set_news(news)

    def _select_channel_news(self, news):
        # zaznacz i pokaż kanał w drzewie kanałów
        sel_item = self._channel_manager_channels[news['channel_title']]
        try:
            self._channel_manager_treeview.selection_set(sel_item)
            self._channel_manager_treeview.see(sel_item)
        except tk.TclError as e:
            print(e)

    def _set_news(self, news):
        '''Wybiera news jako aktywny w programie. Parametr to słownik z bazy z tabeli news.'''
        self._select_channel_news(news)

        # parsuj HTML
        parser = NewsParser()
        parser.feed(news['summary'])

        # załaduj treść do przeglądarki
        self._news_viewer_text['state'] = tk.NORMAL
        self._news_viewer_text.delete('1.0', tk.END)
        self._news_viewer_text.insert(tk.END, parser.get_text())
        self._news_viewer_text.mark_set(tk.INSERT, '1.0')
        self._news_viewer_text['state'] = tk.DISABLED
        self._news_viewer_title['state'] =  tk.NORMAL
        self._news_viewer_title.delete('1.0', tk.END)
        self._news_viewer_title.insert(tk.END, news['title'])
        self._news_viewer_title['state'] = tk.DISABLED
        self._vote_up_btn['text'] = f"{news['quality']:.2f}"

        # zaznacz kontrolkę z treścią aby łatwo przewijać za pomocą strzałek
        self._news_viewer_text.focus()

    def _on_remove_channel_or_folder(self, event=None):
        selection = self._channel_manager_treeview.selection()
        if selection is None:
            return

        selected_id = selection[0]
        title = self._channel_manager_treeview.item(selected_id, option='text')
        type_ = self._channel_manager_title_type[title]

        if not askyesno('Question', f'Do you really want to remove {title}?'):
            return

        # usuń z bazy
        if type_ == 'folder':
            # nie można usuwać nie pustych folderów
            if self._channel_manager_treeview.get_children(selected_id):
                showerror('Error', 'Could not remove non empty folder.')
                return

            self._db_cursor.execute('delete from folder where title = ?', (title,))
        elif type_ == 'channel':
            self._db_cursor.execute('delete from channel where title = ?', (title,))
            self._db_cursor.execute('delete from news where channel_id = (select channel.id from channel where channel.title = ?)', (title,))

        # usuń z listy
        self._channel_manager_treeview.delete(selected_id)
        del self._channel_manager_title_type[title]

    def _on_add_folder(self, event=None):
        dlg = FolderDialog(self)
        data = dlg.run()
        if data:
            try:
                self._db_cursor.execute('insert into folder(title) values (?)', (data['title'],))
                item_id = self._channel_manager_treeview.insert('', tk.END, text=data['title'], image=self._icons['folder'])
                self._channel_manager_folders[data['title']] = item_id
                self._channel_manager_treeview.selection_set(item_id)
                self._channel_manager_title_type[data['title']] = 'folder'
            except:
                showerror('Error', 'Error while adding new folder.')

    def _on_add_channel(self, event=None):
        dlg = ChannelDialog(self)
        data = dlg.run()
        if data:
            self._db_cursor.execute('insert into channel(title, url) values (?, ?)', (data['title'], data['url']))

            icon = 'rss'
            if 'youtube' in data['url']:
                icon = 'youtube'
            elif 'twitch' in data['url']:
                icon = 'twitch'

            self._channel_manager_channels[data['title']] = self._channel_manager_treeview.insert('', tk.END, text=data['title'], image=self._icons[icon])
            self._channel_manager_title_type[data['title']] = 'channel'

        dlg.destroy()

    def _on_update_all(self, event=None):
        channels = self._db_cursor.execute('select * from channel').fetchall()
        channel_count = len(channels)

        dlg = ProgressDialog(self)
        dlg.show()

        for index, channel in enumerate(channels):
            status = ((index + 1) * 1 / channel_count) * 100

            dlg.set_position(status, msg=f"Pobieram wiadomości z kanału {channel['title']}...")
            self.update_idletasks()

            try:
                feed = None
                if channel['url'].startswith('http'):
                    resp = requests.get(channel['url'], timeout=10.0)
                    feed = io.BytesIO(resp.content)
                elif channel['url'].startswith('script'):
                    script_name, url = channel['url'].split(':', maxsplit=2)[1:]
                    print(script_name, url)
                    pkg = f'bpsnews.scripts.{script_name}'
                    m = importlib.import_module(pkg)
                    klass = getattr(m, 'Spider')

                    # ustal tytuł ostatniego newsa pobranego z tego źródła
                    last_news_title = self._db_cursor.execute('select * from news where channel_id = (select id from channel where title = ?) order by id desc limit 1', (channel['title'],)).fetchone()
                    if last_news_title:
                        last_news_title = last_news_title['title']

                    # pobierz newsy
                    spider = klass(url, stop_title=last_news_title)
                    feed = spider.start()
            except:
                dlg.set_position(status, msg=f"Nie można pobrać wiadomości dla kanału {channel['title']}.")
                continue

            data = feedparser.parse(feed)
            news = data['items']

            # create list of values
            insert_values = []
            for d in news:
                # sanityzuj tytuł
                title = d['title'].replace('\n', '')

                # summary musi być zawsze
                if 'summary' not in d:
                    d['summary'] = 'Brak.'

                insert_values.append((channel['id'], d['title'], d['link'], d['summary']))

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
                self._db_cursor.execute(insert_sql, [d for sublist in insert_values for d in sublist])
            except sqlite3.OperationalError as e:
                pass
            finally:
                # ustal ilość nieprzeczytanych dla tego kanału (returning nie działa dla tej wersji sqlite3)
                inserted_count = self._db_cursor.execute('select count(id) from news where channel_id = ? and is_read = 0', (channel['id'],)).fetchone()[0]

                # uaktualnij liczbę nieprzeczytanych w kanale
                channel_item = self._channel_manager_channels[channel['title']]
                self._channel_manager_treeview.set(channel_item, '#news-count', inserted_count)

        # uaktualnij wagi newsów
        dlg.set_position(100, msg='Uaktualniam rekomendacje...')
        self._recommend_update_quality_all()

        dlg.destroy()

    def _recommend_count_words(self, text):
        # usuń znaki specjalne
        spec = '~!@#$%^&*()_+{}:"|<>?`-=[];\'\\,./'
        for spec_char in spec:
            text = text.replace(spec_char, ' ')

        # usuń słowa 3 znakowe lub krótsze
        text = text.split()
        text = list(set([word.lower() for word in text if len(word) > 3]))
        return text

    def _recommend_update_words(self, words_count):
        # aktualizuj tabelę words
        for word in words_count:
            sql = 'insert into words(word, weight) values(?, 1) on conflict(word) do update set weight = weight + 1 where word = ?'
            self._db_cursor.execute(sql, (word, word))

    def _recommend_update_quality_all(self):
        '''Aktualizuje pole quality dla wszystkich nie przeczytanych newsów'''
        sql = "select news.id, (channel.title || ' ' || news.title || ' ' || summary) as text from news join channel on channel.id = news.channel_id where is_read = 0"
        q = self._db_cursor.execute(sql)
        for row in q.fetchall():
            words = list(set([f'"{i}"' for i in self._recommend_count_words(row['text'])]))
            words_list = f'({",".join(words)})'
            new_quality = self._db_cursor.execute(f'select {float(len(words_list))} / sum(weight) from words where use = 1 and word in {words_list}').fetchone()[0]
            if new_quality is not None:
                self._db_cursor.execute('update news set quality = ? where id = ?', (new_quality, row['id']))

    def _recommend_update_quality(self, word):
        # znajdź wszystkie nie przejrzane zawierajace słowo
        sql = "select news.id, (channel.title || ' ' || news.title || ' ' || summary) as text from news join channel on channel.id = news.channel_id where is_read = 0 and (channel.title || ' ' || news.title || ' ' || summary) like ? collate nocase"
        q = self._db_cursor.execute(sql, (f'%{word}%',))
        for row in q:
            words = list(set([f'"{i}"' for i in self._recommend_count_words(row['text'])]))
            words_list = f'({",".join(words)})'
            new_quality = self._db_cursor.execute(f'select {float(len(words_list))} / sum(weight) from words where use = 1 and word in {words_list}').fetchone()[0]
            if new_quality is not None:
                self._db_cursor.execute('update news set quality = ? where id = ?', (new_quality, row['id']))

    def _on_quit(self, event=None):
        if self._db_connection:
            self._db_connection.commit()
            self._db_connection.close()
        self.quit()


if __name__ == '__main__':
    app = Application()
    app.mainloop()