import re
import random
import html.parser
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from com.bps.news.updater import Channel
from com.bps.news.resources import resource


class NewsListView(Gtk.ScrolledWindow):
    def __init__(self, on_activate=None):
        super().__init__()
        self.set_size_request(300, 100)
        self._on_activate = on_activate

        self._list_store = Gtk.ListStore(str, int)
        self._tree_view = Gtk.TreeView(self._list_store)
        self._tree_view.set_headers_visible(False)
        self.add(self._tree_view)
        self._tree_view.connect('row_activated', self._on_row_activated)

        # title column
        title_renderer = Gtk.CellRendererText()
        title_column = Gtk.TreeViewColumn(None, title_renderer)
        title_column.add_attribute(title_renderer, 'text', 0)
        self._tree_view.append_column(title_column)

        self.show_all()

    def add_news(self, title, id):
        self._list_store.append((title, id))

    def clear_news(self):
        self._list_store.clear()

    def select_news(self, news_id):
        for news in self._list_store:
            if news[1] == news_id:
                # zaznacz element
                self._tree_view.get_selection().select_iter(news.iter)

                # przewiń widok aby pokazać zaznaczenie
                self._tree_view.scroll_to_cell(news.path, None, True, 0.5, 0.5)

                break

    def mark_as_read(self, news):
        pass

    def _on_row_activated(self, tree_view, tree_path, tree_column):
        if callable(self._on_activate):
            model, iter_ = news_id = tree_view.get_selection().get_selected()

            if iter_ is None:
                return False

            self._on_activate(model.get_value(iter_, 1))


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


class NewsViewer(Gtk.Box):
    def __init__(self, on_click=None, on_like=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._on_title_click = on_click
        self._on_like_btn_click = on_like
        self._link_cursor = Gdk.Cursor(Gdk.CursorType.HAND1)

        # pasek narzędzi
        vbox = Gtk.HBox()

        # tytuł
        self._title_label = Gtk.Label('')
        self._title_label.set_tooltip_text('1 - streamlink worst\n2 - streamlink 360p')
        self._title_label.set_line_wrap(True)
        self._title_label.set_halign(Gtk.Align.START)
        self._title_label.set_margin_start(5)
        self._title_label.set_has_window(True)
        self._title_label.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._title_label.connect('button-press-event', self._on_url_click)
        self._title_label.connect('realize', self._on_label_realize)
        vbox.pack_start(self._title_label, False, False, 0)

        # ikona "lubię to"
        self._thumbs_up_btn = Gtk.Button('like')
        self._thumbs_up_btn.connect('clicked', self._on_like_click)
        vbox.pack_end(self._thumbs_up_btn, False, False, 0)

        self.pack_start(vbox, False, False, 2)

        # url
        self._url = None

        # treść
        scrolledWindow = Gtk.ScrolledWindow()
        self._text_buffer = Gtk.TextBuffer()
        self._text_view = Gtk.TextView()
        self._text_view.set_buffer(self._text_buffer)
        self._text_view.set_editable(False)
        self._text_view.set_monospace(True)
        self._text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self._text_view.set_cursor_visible(False)
        self._text_view.set_margin_start(5)
        scrolledWindow.add(self._text_view)
        self.pack_start(scrolledWindow, True, True, 5)

    def set_news_quality(self, q):
        self._thumbs_up_btn.set_label(f'Like - {q}')

    def _on_like_click(self, e):
        if callable(self._on_like_btn_click):
            news_title = self._title_label.get_text()
            news_content = self._text_buffer.get_text(self._text_buffer.get_start_iter(), self._text_buffer.get_end_iter(), False)
            self._on_like_btn_click(news_title, news_content)

    def _on_label_realize(self, widget):
        self._title_label.get_window().set_cursor(self._link_cursor)

    def set_news(self, title, url, content, quality=0):
        self._title_label.set_text(title.strip())
        self._url = url
        self.set_news_quality(quality)

        # parsuj HTML
        parser = NewsParser()
        parser.feed(content)
        self._text_buffer.set_text(parser.get_text())

    def get_url(self):
        return self._url

    def _on_url_click(self, w, event):
        if callable(self._on_title_click):
            self._on_title_click(self._url, event.button)


class ChannelDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__()
        self.set_modal(True)
        self.set_title('Channel')
        self.set_transient_for(parent)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_skip_taskbar_hint(True)
        self.set_destroy_with_parent(True)
        self.add_button('Cancel', Gtk.ResponseType.CANCEL)
        self._ok_button = self.add_button('OK', Gtk.ResponseType.OK)
        self._ok_button.set_sensitive(False)

        # form
        title_label = Gtk.Label('Channel title')
        self._rss_title_entry = Gtk.Entry()
        self._rss_title_entry.connect('changed', self._on_validate)
        self.vbox.pack_start(title_label, False, False, 0)
        self.vbox.pack_start(self._rss_title_entry, False, False, 0)

        url_label = Gtk.Label('URL')
        self._rss_url_entry = Gtk.Entry()
        self._rss_url_entry.connect('changed', self._on_validate)
        self._rss_url_entry.connect('activate', self._on_rss_url_entry)
        self.vbox.pack_start(url_label, False, False, 0)
        self.vbox.pack_start(self._rss_url_entry, False, False, 0)

        channel_type_label = Gtk.Label('Channel type')
        self._channel_type_combo = Gtk.ComboBoxText()
        for channel_id, channel_class in Channel.Map.items():
            self._channel_type_combo.append(str(channel_id), channel_class)
        self._channel_type_combo.set_active(0)
        self.vbox.pack_start(channel_type_label, False, False, 0)
        self.vbox.pack_start(self._channel_type_combo, False, False, 0)

        self.show_all()

    def set_data(self, values):
        self._rss_title_entry.set_text(values['title'])
        self._rss_url_entry.set_text(values['url'])
        self._channel_type_combo.set_active(values['channel_type'])
        self._on_validate()

    def get_data(self):
        return {
            'title': self._rss_title_entry.get_text(),
            'url': self._rss_url_entry.get_text(),
            'channel_type': self._channel_type_combo.get_active()
        }

    def _auto_populate_form(self):
        '''Wykrywa specjalne ciągi znaków w polu tytułu i na ich podstawie automatycznie uzupełnia wszystkie pola formularza'''
        url = self._rss_title_entry.get_text()
        channel_type = self._channel_type_combo.get_active_text()

        # link do kanału youtube
        m = re.match(r'^https:\/\/www\.youtube\.com\/channel\/([a-zA-Z0-9_\-]+)$', url)
        if m is not None and channel_type == 'RssChannel':
            channel_id = m.group(1)
            self._rss_url_entry.set_text(f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}')
            self._rss_title_entry.set_text(channel_id)
            return True

        # link do usera youtube
        m = re.match(r'^https:\/\/www\.youtube\.com\/user\/([a-zA-Z0-9_\-]+)$', url)
        if m is not None and channel_type == 'RssChannel':
            user_id = m.group(1)
            self._rss_url_entry.set_text(f'https://www.youtube.com/feeds/videos.xml?user={user_id}')
            self._rss_title_entry.set_text(user_id)
            return True

    def _on_rss_url_entry(self, e):
        self.response(Gtk.ResponseType.OK)

    def _on_validate(self, event=None):
        self._auto_populate_form()
        b = all([
            self._rss_title_entry.get_text(),
            self._rss_url_entry.get_text()
        ])
        self._ok_button.set_sensitive(b)


class ChannelViewer(Gtk.ScrolledWindow):
    '''Widget with tree of channels.'''

    ITEM_TYPE_FOLDER = 0
    ITEM_TYPE_CHANNEL = 1

    def __init__(self, on_channel_activate=None, on_delete_channel=None, on_dragdrop_channel=None, on_folder_toggle=None):
        super().__init__()

        self._signal_handles = {}

        self._on_channel_activate = on_channel_activate
        self._on_delete_channel = on_delete_channel
        self._on_dragdrop_channel = on_dragdrop_channel
        self._on_folder_toggle = on_folder_toggle

        self._tree_store = Gtk.TreeStore(str, int, int, GdkPixbuf.Pixbuf)  # title, unread_count, type(0 - folder, 1 - channel)

        # icon column
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn(None, icon_renderer)
        icon_column.add_attribute(icon_renderer, 'pixbuf', 3)

        # title column
        title_renderer = Gtk.CellRendererText()
        title_column = Gtk.TreeViewColumn(None, title_renderer)
        title_column.add_attribute(title_renderer, 'text', 0)

        # news count column
        news_count_renderer = Gtk.CellRendererText()
        news_count_column = Gtk.TreeViewColumn(None, news_count_renderer)
        news_count_column.add_attribute(news_count_renderer, 'text', 1)

        self._tree_view = Gtk.TreeView(self._tree_store)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        self.set_size_request(150, 100)
        self.add(self._tree_view)
        self._tree_view.set_headers_visible(False)
        self._tree_view.append_column(icon_column)
        self._tree_view.append_column(title_column)
        self._tree_view.append_column(news_count_column)
        self._tree_view.connect('button_press_event', self._on_channel_tree_button_press)
        self._tree_view.connect('row_activated', self._on_row_activated)
        self._signal_handles['row-expanded'] = self._tree_view.connect('row-expanded', self._on_row_expanded)
        self._signal_handles['row-collapsed'] = self._tree_view.connect('row-collapsed', self._on_row_collapsed)

        self._channel_context_menu = self._create_channel_context_menu()

        # drag & drop
        self._tree_view.connect('drag-data-received', self._on_drag_data_received)
        self._tree_view.connect('drag-data-get', self._on_drag_data_get)
        target_entry = Gtk.TargetEntry.new('text/plain', 0, 0)
        self._tree_view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [target_entry],
            Gdk.DragAction.DEFAULT | Gdk.DragAction.MOVE
        )
        self._tree_view.enable_model_drag_dest(
            [target_entry],
            Gdk.DragAction.DEFAULT | Gdk.DragAction.MOVE
        )

        self._selected_channel = None

        self.show_all()

    def get_selected_channel(self):
        return self._selected_channel

    def _on_row_expanded(self, treeview, iter_, path):
        if callable(self._on_folder_toggle):
            self._on_folder_toggle(True, self._tree_store.get_value(iter_, 0))

            # przywróć zaznaczenie jeśli trzeba
            if self._selected_channel is not None:
                self._tree_view.get_selection().select_iter(self._selected_channel.iter)
                self._tree_view.scroll_to_cell(self._selected_channel.path, None, True, 0.5, 0.5)

    def _on_row_collapsed(self, treeview, iter_, path):
        if callable(self._on_folder_toggle):
            self._on_folder_toggle(False, self._tree_store.get_value(iter_, 0))

    def _on_drag_data_get(self, widget, drag_context, data, info, time):
        # ustal ciągnięty kanał
        model, path = self._tree_view.get_selection().get_selected_rows()
        data.set_text(str(path[0]), -1)

    def _on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        # ustal ścieżkę do ciągniętego kanału
        channel_path = data.get_text()

        # ustal ścieżkę do katalogu z którego zabierasz kanał
        folder_path = None
        s = channel_path.split(':')
        if len(s) > 1:
            # katalog jest obecny w ścieżce kanału, ekstraktuj go
            folder_path = s[0]

        source_iter = self._tree_store.get_iter(channel_path)
        dest_path = self._tree_view.get_dest_row_at_pos(x, y)
        dest_iter = None
        if dest_path is not None:
            dest_path, drop_pos = dest_path

            # nie pozwól na dodanie kanału do innego kanału
            if dest_path and dest_path.get_depth() > 1:
                dest_path.up()

            dest_iter = self._tree_store.get_iter(dest_path)

            # dest_path musi wskazywać na katalog
            # to usuwa możliwość doawania kanału do kanału w katalogu root
            if self._tree_store.get_value(dest_iter, 2) != 0:
                dest_path = None
                dest_iter = None

        # ustal przenoszone wartości
        channel_title = self._tree_store.get_value(source_iter, 0)
        unread_count = self._tree_store.get_value(source_iter, 1)
        icon = self._tree_store.get_value(source_iter, 3)
        folder_title = ''
        if dest_iter is not None:
            folder_title = self._tree_store.get_value(dest_iter, 0)

        # zmniejsz ilość nieprzeczytanych w folderze z którego zabrałeś kanał
        if folder_path is not None:
            # Ta metoda źle zlicza jeśli kanał jest ciągany
            # self._folder_update_unread(self._tree_store.get_iter(folder_path))
            i = self._tree_store.get_iter(folder_path)
            n = self._tree_store.get_value(i, 1)
            n -= unread_count
            self._tree_store.set_value(i, 1, n)

        # przenieś element poprzez zrobienie kopii i usunięcie starego
        self._tree_store.remove(source_iter)
        new_channel_iter = self._tree_store.append(dest_iter, (channel_title, unread_count, self.ITEM_TYPE_CHANNEL, icon))

        # odśwież ilość nieprzeczytanych w folderze do którego wrzuciłeś ciągnięty kanał
        if dest_iter is not None:
            self._folder_update_unread(dest_iter)

        # zaznacz przeniesiony kanał
        if dest_path is not None:
            self._tree_view.expand_row(dest_path, True)
        self._tree_view.get_selection().select_iter(new_channel_iter)

        # wykonaj inne, być może potrzebne, operacje
        if callable(self._on_dragdrop_channel):
            self._on_dragdrop_channel(channel_title, folder_title)

    def add_folder(self, channel_title, expanded=False):
        iter_ = self._tree_store.append(None, (channel_title, 0, self.ITEM_TYPE_FOLDER, resource.icons['folder']))

    def toggle_folder(self, folder_title, expand):
        '''Zwiń / rozwiń katalog bez emitowania zdarzeń.'''
        iter_ = self._tree_store.get_iter_first()
        iter_ = self._get_folder_iter(folder_title)
        if iter_ is not None:
            self._tree_view.disconnect(self._signal_handles['row-expanded'])
            self._tree_view.disconnect(self._signal_handles['row-collapsed'])

            # czy zwinąć / rozwinąć
            folder_path = self._tree_store.get_path(iter_)
            if expand:
                self._tree_view.expand_row(folder_path, True)
            else:
                self._tree_view.collapse_row(folder_path)

            self._signal_handles['row-expanded'] = self._tree_view.connect('row-expanded', self._on_row_expanded)
            self._signal_handles['row-collapsed'] = self._tree_view.connect('row-collapsed', self._on_row_collapsed)

    def _get_folder_iter(self, folder_title):
        for row in self._tree_store:
            if row[0] == folder_title:
                return row.iter

    def _folder_update_unread(self, folder_iter):
        news_count = 0

        # sumuj wartości wszystkich kanałów w folderze
        if self._tree_store.iter_has_child(folder_iter):
            iter_ = self._tree_store.iter_children(folder_iter)
            while True:
                news_count += self._tree_store.get_value(iter_, 1)
                iter_ = self._tree_store.iter_next(iter_)
                if iter_ is None:
                    break

        self._tree_store.set_value(folder_iter, 1, news_count)

    def add_channel(self, channel_title, unread_count, folder_title=None, icon_name='rss'):
        folder_iter = self._get_folder_iter(folder_title)
        channel_iter = self._tree_store.append(folder_iter, (channel_title, unread_count, self.ITEM_TYPE_CHANNEL, resource.icons[icon_name]))

        # jeśli kanał dodano do folderu to uaktualnij liczbę nieprzeczytanych w tym folderze
        if folder_iter is not None:
            self._folder_update_unread(folder_iter)

        return channel_iter

    def get_selected_title(self):
        model, iter_ = self._tree_view.get_selection().get_selected()
        if iter is None:
            return False

        return model.get_value(iter_, 0)

    def _find_channel(self, channel_title, iter_):
        while iter_ is not None:
            title = self._tree_store.get_value(iter_, 0)
            type_ = self._tree_store.get_value(iter_, 2)
            if type_ == self.ITEM_TYPE_CHANNEL and title == channel_title:
                return iter_
            if self._tree_store.iter_has_child(iter_):
                a = self._find_channel(channel_title, self._tree_store.iter_children(iter_))
                if a is not None:
                    return a
            iter_ = self._tree_store.iter_next(iter_)
        return None

    def clear_news_count(self):
        for row in self._tree_store:
            self._tree_store.set_value(row.iter, 1, 0)

    def dec_unread_count(self, channel_title):
        iter_ = self._tree_store.get_iter_first()
        iter_ = self._find_channel(channel_title, iter_)
        if iter_ is not None:
                news_count = self._tree_store.get_value(iter_, 1)
                if news_count <= 0:
                    news_count = 1
                self._tree_store.set_value(iter_, 1, news_count - 1)

        # jeśli kanał jest w folderze to odśwież również wartość dla folderu
        folder_iter = self._tree_store.iter_parent(iter_)
        if folder_iter is not None:
            self._folder_update_unread(folder_iter)

    def set_channel_unread(self, channel_title, unread_count):
        # znajdź element w drzewie
        iter_ = self._tree_store.get_iter_first()
        iter_ = self._find_channel(channel_title, iter_)
        if iter_ is not None:
            # uaktualnij ilość nieprzeczytanych w UI
            self._tree_store.set_value(iter_, 1, unread_count)

            # jeśli kanał jest w folderze to uaktualnij również numerek przy folderze
            folder_iter =  self._tree_store.iter_parent(iter_)
            if folder_iter is not None:
                self._folder_update_unread(folder_iter)

    def select_channel(self, channel_title):
        channel = None

        # wyszukaj wśród kanałów bez folderów
        for row in self._tree_store:
            # kanały poza folderami
            if row[2] == self.ITEM_TYPE_CHANNEL and row[0] == channel_title:
                channel = row
                break

            # wyszukaj w kanałach wewnątrz folderów
            elif row[2] == self.ITEM_TYPE_FOLDER:
                for i in row.iterchildren():
                    if i[0] == channel_title:
                        channel = i
                        break

        if channel is None:
            return False

        self._tree_view.get_selection().select_iter(channel.iter)
        self._tree_view.scroll_to_cell(channel.path, None, True, 0.5, 0.5)
        self._selected_channel = channel
        return channel[0]

    def select_next_channel(self):
        '''Zaznacza następny kanał który posiada nieprzeczytane newsy'''
        row_list = []

        # wybierz kanały z elementami nieprzeczytanymi
        for row in self._tree_store:
            # kanały poza folderami
            if row[2] == self.ITEM_TYPE_CHANNEL and row[1] > 0:
                row_list.append(row)

            # kanały wewnątrz folderów
            elif row[2] == self.ITEM_TYPE_FOLDER:
                for i in row.iterchildren():
                    if i[1] > 0:
                        row_list.append(i)

        # jeśli nie ma takich kanałów to koniec
        if len(row_list) == 0:
            return False

        row = random.choice(row_list)
        if row is None:
            return False

        channel_name = row[0]

        # usuń stare zaznaczenie przed nowym
        # zaznaczeniem tak na wszelki wypadek
        self._tree_view.get_selection().unselect_all()

        self._tree_view.get_selection().select_iter(row.iter)
        self._tree_view.scroll_to_cell(row.path, None, True, 0.5, 0.5)
        self._selected_channel = row
        return channel_name

    def _on_channel_tree_button_press(self, tree_view, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self._channel_context_menu.popup_at_pointer(event)
            return True
        return False

    def _create_channel_context_menu(self):
        menu = Gtk.Menu()
        delete_item = Gtk.MenuItem('Delete')
        delete_item.connect('activate', self._on_delete_channel_item)
        menu.append(delete_item)
        menu.show_all()
        return menu

    def _on_delete_channel_item(self, e):
        model, iter_ = self._tree_view.get_selection().get_selected()
        if iter_ is not None:
            channel_title = model.get_value(iter_, 0)
            if callable(self._on_delete_channel):
                if self._on_delete_channel(channel_title):
                    self._tree_store.remove(iter_)


    def _on_row_activated(self, tree_view, tree_path, tree_column):
        # ustal tytuł zaznaczonego kanału
        model, iter_ = tree_view.get_selection().get_selected()
        if iter_ is None:
            return False
        channel_title = self._tree_store.get_value(iter_, 0)

        if callable(self._on_channel_activate):
            self._on_channel_activate(channel_title)


class FolderDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__()
        self.set_modal(True)
        self.set_title('Folder')
        self.set_transient_for(parent)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_skip_taskbar_hint(True)
        self.set_destroy_with_parent(True)
        self.add_button('Cancel', Gtk.ResponseType.CANCEL)
        self.add_button('OK', Gtk.ResponseType.OK)

        # form
        folder_title_label = Gtk.Label('Folder title')
        self._folder_title_entry = Gtk.Entry()
        self.vbox.pack_start(folder_title_label, False, False, 0)
        self.vbox.pack_start(self._folder_title_entry, False, False, 0)

        self.show_all()

    def set_data(self, values):
        self._folder_title_entry.set_text(values['title'])

    def get_data(self):
        return {
            'title': self._folder_title_entry.get_text()
        }

    def _on_rss_url_entry(self, e):
        self.response(Gtk.ResponseType.OK)


class AboutDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__()
        self.set_size_request(320, 280)
        self.set_modal(True)
        self.set_title('About')
        self.set_transient_for(parent)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_skip_taskbar_hint(True)
        self.set_destroy_with_parent(True)
        self.add_button('OK', Gtk.ResponseType.OK)

        text_buffer = Gtk.TextBuffer()
        text_buffer.set_text('''Authors:
- jaroslaw.janikowski@gmail.com (programming)
- www.freepik.com (icons)''')
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_buffer(text_buffer)
        self.vbox.pack_start(text_view, True, True, 0)

        self.show_all()


class ProgressDialog(Gtk.Dialog):
    def __init__(self, parent, on_cancel=None):
        super().__init__()
        self.set_size_request(640, 480)
        self.set_modal(True)
        self.set_title('Operation progress...')
        self.set_transient_for(parent)
        self.set_default_response(Gtk.ResponseType.CANCEL)
        self.set_skip_taskbar_hint(True)
        self.set_destroy_with_parent(True)
        self.add_button('Cancel', Gtk.ResponseType.CANCEL)
        self._on_cancel = on_cancel
        self.connect('response', self._on_response)

        # progress bar
        progress_label = Gtk.Label('Progress')
        self.vbox.pack_start(progress_label, False, False, 0)
        self._progressbar = Gtk.ProgressBar()
        self.vbox.pack_start(self._progressbar, False, False, 0)

        # log view
        log_label = Gtk.Label('Log')
        self.vbox.pack_start(log_label, False, False, 0)
        self._log_text_buffer = Gtk.TextBuffer()
        self._log_text_view = Gtk.TextView()
        self._log_text_view.set_editable(False)
        self._log_text_view.set_cursor_visible(False)
        self._log_text_view.set_buffer(self._log_text_buffer)

        log_scrollbars = Gtk.ScrolledWindow()
        log_scrollbars.add(self._log_text_view)
        self.vbox.pack_start(log_scrollbars, True, True, 0)

    def _on_response(self, progress_dialog, response_id):
        if response_id == Gtk.ResponseType.DELETE_EVENT or response_id == Gtk.ResponseType.NONE or response_id == Gtk.ResponseType.CANCEL and callable(self._on_cancel):
            self._on_cancel()
            return True

    def set_position(self, pos, msg=None):
        self._progressbar.set_fraction(pos)

        if msg:
            end_iter = self._log_text_buffer.get_end_iter()
            if end_iter and self.is_visible():
                self._log_text_buffer.insert(end_iter, f'{msg}\n')
                self._log_text_view.scroll_to_iter(end_iter, 0.3, False, 0, 0)

    def show(self):
        # reset dialog controls
        self._log_text_buffer.set_text('')
        self.set_position(0.01)

        # show all controls
        self.show_all()
