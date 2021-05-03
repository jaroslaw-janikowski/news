import datetime
import calendar
from gi.repository import Gtk


class DisallowedDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__()
        self.set_title('Parental control')
        self.set_modal(True)
        self.set_transient_for(parent)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_skip_taskbar_hint(True)
        self.set_destroy_with_parent(True)
        self.add_button('OK', Gtk.ResponseType.OK)

        label = Gtk.Label('Today is not sunday, exiting ;)')
        self.vbox.pack_start(label, False, False, 0)

        self.show_all()


def check_parental_control():
    # check parental control rules
    today = datetime.datetime.now()
    if calendar.weekday(today.year, today.month, today.day) == 6 or today.hour > 17:
        return True

    return False
