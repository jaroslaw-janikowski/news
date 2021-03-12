import os.path
import subprocess
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from com.bps.news.resources import resource
import com.bps.news.ui
import com.bps.news
import com.bps.news.database
import com.bps.news.updater
import com.bps.news.parentalctrl


class App(Gtk.Window):
    def __init__(self):
        super().__init__(Gtk.WindowType.TOPLEVEL, 'News')
        self.set_title('News')
        self._progress_dialog = None
        self.connect('destroy', self._on_destroy)

        # otworzenie / utworzenie pliku bazy danych
        database_file = os.path.join(
            os.path.expanduser('~'),
            '.config/news',
            'news.sqlite3'
        )
        self._db = com.bps.news.database.Database()
        if not os.path.isfile(database_file):
            self._db.create_new(database_file)
        self._db.open_file(database_file)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # menubar
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)

        # News menu
        app_menu_item = Gtk.MenuItem('News')
        app_menu = Gtk.Menu()
        app_menu_item.set_submenu(app_menu)
        menubar.append(app_menu_item)

        self._update_all_item = Gtk.MenuItem('Update all')
        key, mod = Gtk.accelerator_parse("<Control>U")
        self._update_all_item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        self._update_all_item.connect('activate', self._on_update_all_item)
        app_menu.append(self._update_all_item)

        quit_item = Gtk.MenuItem('Quit')
        quit_item.connect('activate', self._on_quit_menu_item)
        key, mod = Gtk.accelerator_parse("<Control>Q")
        quit_item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        app_menu.append(quit_item)

        # channel menu
        channel_menu_item = Gtk.MenuItem('Channel')
        channel_menu = Gtk.Menu()
        channel_menu_item.set_submenu(channel_menu)
        menubar.append(channel_menu_item)

        channel_add_item = Gtk.MenuItem('Add channel')
        channel_add_item.connect('activate', self._on_channel_add_item)
        key, mod = Gtk.accelerator_parse('<Control>N')
        channel_add_item.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        channel_menu.append(channel_add_item)

        folder_add_item = Gtk.MenuItem('Add folder')
        folder_add_item.connect('activate', self._on_folder_add_item)
        key, mod = Gtk.accelerator_parse('<Control><Shift>N')
        folder_add_item.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        channel_menu.append(folder_add_item)

        # news menu
        news_menu_item = Gtk.MenuItem('News')
        news_menu = Gtk.Menu()
        news_menu_item.set_submenu(news_menu)
        menubar.append(news_menu_item)

        news_next_item = Gtk.MenuItem('Next')
        news_next_item.connect('activate', self._on_news_next_item)
        key, mod = Gtk.accelerator_parse('N')
        news_next_item.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        news_menu.append(news_next_item)

        news_goto_item = Gtk.MenuItem('Goto')
        news_goto_item.connect('activate', self._on_news_goto_item)
        key, mod = Gtk.accelerator_parse('G')
        news_goto_item.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        news_menu.append(news_goto_item)

        news_streamlink_worst = Gtk.MenuItem('Streamlink worst')
        news_streamlink_worst.connect('activate', self._on_news_streamlink_worst)
        key, mod = Gtk.accelerator_parse('1')
        news_streamlink_worst.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        news_menu.append(news_streamlink_worst)

        news_streamlink_360p = Gtk.MenuItem('Streamlink 360p')
        news_streamlink_360p.connect('activate', self._on_news_streamlink_360p)
        key, mod = Gtk.accelerator_parse('2')
        news_streamlink_360p.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        news_menu.append(news_streamlink_360p)

        news_mark_read_all = Gtk.MenuItem('Mark all as read')
        news_mark_read_all.connect('activate', self._on_mark_all_read)
        key, mod = Gtk.accelerator_parse('<Control>M')
        news_mark_read_all.add_accelerator('activate', accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        news_menu.append(news_mark_read_all)

        # help menu
        help_menu_item = Gtk.MenuItem('Help')
        help_menu = Gtk.Menu()
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)

        about_menu_item = Gtk.MenuItem('About')
        about_menu_item.connect('activate', self._on_about_item)
        help_menu.append(about_menu_item)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(paned, True, True, 0)

        # lewy panel
        self._channel_viewer = com.bps.news.ui.ChannelViewer(
            self._on_channel_activate,
            self._on_delete_channel_item,
            self._on_dragdrop_channel,
            self._on_folder_toggle
        )
        paned.pack1(self._channel_viewer, False, False)

        # prawy panel
        l_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self._news_list_box = com.bps.news.ui.NewsListView(self._on_note_activated)
        l_paned.pack1(self._news_list_box, False, False)

        self._news_viewer = com.bps.news.ui.NewsViewer(on_click=self._on_news_view, on_like=self._on_like_click)
        l_paned.pack2(self._news_viewer, True, False)
        paned.pack2(l_paned, True, False)

        self.add(vbox)

        # załaduj dane i ustawienia
        folders = self._db.get_folders()
        for folder in folders:
            self._channel_viewer.add_folder(folder['title'])

        for id, title, url, channel_type, unread_count, folder_title in self._db.get_channels():
            # wybierz ikonę odpowiednią do źródła newsów
            icon = 'rss'
            if 'youtube' in url:
                icon = 'youtube'

            self._channel_viewer.add_channel(title, unread_count, folder_title, icon_name=icon)

        # rozwin katalogi jeśli trzeba
        for folder in folders:
            self._channel_viewer.toggle_folder(folder['title'], folder['expanded'])

        self.show_all()

    def _on_mark_all_read(self, e):
        self._db.set_all_as_read()
        self._news_list_box.clear_news()
        self._channel_viewer.clear_news_count()

    def _on_like_click(self, news_title, news_content):
        news_channel = self._channel_viewer.get_selected_channel()[0]
        text = f'{news_channel} {news_title} {news_content}'.lower()

        r = self._db.recommend_count_words(text)
        self._db.recommend_update_words(r)
        for word, count in r:
            self._db.recommend_update_quality(word)
        self._db.commit()

    def _on_news_streamlink_worst(self, e):
        url = self._news_viewer.get_url()
        if url:
            self.goto(url, 2)

    def _on_news_streamlink_360p(self, e):
        url = self._news_viewer.get_url()
        if url:
            self.goto(url, 3)

    def _on_progress_cancel(self):
        self._updater.cancel()

    def _on_about_item(self, e):
        dlg = com.bps.news.ui.AboutDialog(self)
        dlg.run()
        dlg.destroy()

    def _on_folder_toggle(self, expanding, folder_title):
        self._db.set_folder_expanded(folder_title, expanding)

    def _on_dragdrop_channel(self, channel_title, folder_title):
        self._db.move_channel(channel_title, folder_title)

    def _on_channel_activate(self, channel_title):
        # pobierz wszystkie nieprzeczytane newsy z tego kanału
        # wyświetl newsy w panelu newsów
        self._news_list_box.clear_news()
        for id, channel_id, title, url  in self._db.get_news(channel_title):
            self._news_list_box.add_news(title, id)

    def _on_news_goto_item(self, e):
        url = self._news_viewer.get_url()
        if url:
            self.goto(url)

    def _on_news_view(self, url, button):
        self.goto(url, button)

    def goto(self, url, button=1):
        if button == 1:
            webbrowser.open_new_tab(url)
        elif button == 2:
            subprocess.Popen(['streamlink', url, 'worst', '-p', 'mplayer'])
        elif button == 3:
            subprocess.Popen(['streamlink', url, '360p', '-p', 'mplayer'])

    def _on_note_activated(self, news_id):
        news = self._db.get_news_from_id(news_id)
        self._news_viewer.set_news(news['title'], news['url'], news['summary'])

    def _on_news_next_item(self, e):
        # zaznacz losowy kanał posiadający nieprzeczytane posty
        channel_name = self._channel_viewer.select_next_channel()
        if not channel_name:
            return False

        # znajdź następny news w tym kanale
        news = self._db.get_news_next(channel_name, random=True)
        if news is None:
            # nie ma następnego newsa, zaznacz inny kanał
            # który ma jeszcze nie przeczytane newsy
            # self._on_news_next_item(e)
            return False

        # ustaw newsy na liście newsów dla kanalu
        self.set_channel(channel_name)

        # przekaż focus do kontrolki z listą newsów
        # aby upewnić się że zaznaczenie będzie widoczne
        self._news_list_box.grab_focus()

        # zaznacz news na liście
        self._news_list_box.select_news(news['id'])

        # ustaw news w przeglądarce newsów
        self._news_viewer.set_news(news['title'], news['url'], news['summary'])

        # oznacz notatkę jako przeczytaną
        self._db.set_news_as_read(news['id'])
        self._news_list_box.mark_as_read(news)
        self._channel_viewer.dec_unread_count(channel_name)

    def set_channel(self, channel_title):
        self._channel_viewer.select_channel(channel_title)

        # wyświetl listę notatek na liście notatek
        self._news_list_box.clear_news()
        for news in self._db.get_news(channel_title):
            self._news_list_box.add_news(news['title'], news['id'])

    def _on_delete_channel_item(self, channel_title):
        result = False

        dlg = Gtk.MessageDialog(self, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, 'Czy usunąć kanał?')
        if dlg.run() == Gtk.ResponseType.OK:
            self._db.remove_channel(channel_title)
            result = True

        dlg.destroy()
        return result

    def _on_folder_add_item(self, e):
        dlg = com.bps.news.ui.FolderDialog(self)
        if dlg.run() == Gtk.ResponseType.OK:
            data = dlg.get_data()
            if data:
                if self._db.add_folder(data['title']):
                    self._channel_viewer.add_folder(data['title'])

        dlg.destroy()

    def _on_channel_add_item(self, e):
        dlg = com.bps.news.ui.ChannelDialog(self)
        if dlg.run() == Gtk.ResponseType.OK:
            data = dlg.get_data()
            if data:
                if self._db.add_channel(data['title'], data['url'], data['channel_type']):
                    icon = 'rss'
                    if 'youtube' in data['url']:
                        icon = 'youtube'

                    self._channel_viewer.add_channel(data['title'], 0, icon_name=icon)

        dlg.destroy()

    def _on_update_all_item(self, e):
        self._update_all_item.set_sensitive(False)
        self._progress_dialog = com.bps.news.ui.ProgressDialog(self, self._on_progress_cancel)
        self._progress_dialog.show()

        channels = self._db.get_channels()
        self._updater = com.bps.news.updater.Updater(self._db, channels, self._on_channel_end, self._on_update_end)
        self._updater.start()

    def _on_channel_end(self, channel_title, channel_index, num_channels, channel_items):
        self._progress_dialog.set_position(channel_index / num_channels, f'Pobieram wiadomości z kanału {channel_title}')

    def _on_update_end(self):
        self._update_unread_count()
        self._update_all_item.set_sensitive(True)
        self._db.recommend_update_quality_all()
        self._db.commit()

        # avoid crash
        GObject.idle_add(lambda: self._progress_dialog.destroy())

    def _update_unread_count(self):
        # uaktualnij ilość nieprzeczytanych we wszystkich kanałach
        for channel_title, unread_count in self._db.get_news_count():
            self._channel_viewer.set_channel_unread(channel_title, unread_count)

    def _on_quit_menu_item(self, e):
        self._quit()

    def _on_destroy(self, e=None):
        self._quit()

    def _quit(self):
        Gtk.main_quit()

    def run(self):
        if not com.bps.news.parentalctrl.check_parental_control():
            # inform user why program will be closed
            dlg = com.bps.news.parentalctrl.DisallowedDialog(self)
            dlg.run()
            dlg.destroy()

            return

        Gdk.threads_init()
        Gdk.threads_enter()
        Gtk.main()
        Gdk.threads_leave()
