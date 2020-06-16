from pathlib import Path
from gi.repository import Gtk
from gi.repository import GdkPixbuf


class ResourceManager:
    def __init__(self):
        self._icons_dir = Path('/usr/share/icons/news')
        self.icons = {
            'rss': self.load_icon('rss.png'),
            'folder': self.load_icon('folder.png')
        }

    def load_icon(self, icon_name):
        return GdkPixbuf.Pixbuf.new_from_file(str(self._icons_dir / icon_name))


resource = ResourceManager()
