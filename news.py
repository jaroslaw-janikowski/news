#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk


class NewsList(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._treeview = ttk.Treeview(self)
        self._treeview.pack(fill=tk.BOTH, expand=True)


class NewsViewer(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._text = tk.Text(self)
        self._text.pack(fill=tk.BOTH, expand=True)


class ChannelManager(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._treeview = ttk.Treeview(self)
        self._treeview.pack(fill=tk.BOTH, expand=True)


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry('640x480+100+100')
        self.title('news')
        self.bind('<Control-q>', self._on_quit)

        self.config(menu=self._create_main_menu())

        paned_h = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned_v = ttk.PanedWindow(paned_h, orient=tk.VERTICAL)

        self._channel_manager = ChannelManager(paned_h)
        self._news_list = NewsList(paned_v)
        self._news_viewer = NewsViewer(paned_v)

        # podział pomiędzy listą newsów kanału a przeglądarką
        paned_v.add(self._news_list, weight=1)
        paned_v.add(self._news_viewer, weight=3)
        paned_v.pack(fill=tk.X, expand=True)

        # poziomy podział okna
        paned_h.add(self._channel_manager, weight=1)
        paned_h.add(paned_v, weight=3)
        paned_h.pack(fill=tk.BOTH, expand=True)

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
        self.bind('<N>', self._on_next_news)
        news_menu.add_command(label='Goto', command=self._on_goto_news, accelerator='G')
        self.bind('<G>', self._on_goto_news)
        news_menu.add_command(label='Streamlink worst', command=self._on_streamlink_worst, accelerator='1')
        self.bind('<1>', self._on_streamlink_worst)
        news_menu.add_command(label='Streamlink 360p', command=self._on_streamlink_360p, accelerator='2')
        self.bind('<2>', self._on_streamlink_360p)
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
        pass

    def _on_streamlink_worst(self, event=None):
        pass

    def _on_goto_news(self, event=None):
        pass

    def _on_next_news(self, event=None):
        pass

    def _on_add_folder(self, event=None):
        pass

    def _on_add_channel(self, event=None):
        pass

    def _on_update_all(self):
        pass

    def _on_quit(self, event=None):
        self.quit()


if __name__ == '__main__':
    app = Application()
    app.mainloop()
