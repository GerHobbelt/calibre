#!/usr/bin/env python


__license__   = 'GPL v3'
__copyright__ = '2010, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'


from qt.core import QAction, QTimer

from calibre.gui2.actions import InterfaceAction
from calibre.gui2.dialogs.quickview import Quickview
from calibre.gui2 import error_dialog


current_qv_action_pi = None


def set_quickview_action_plugin(pi):
    global current_qv_action_pi
    current_qv_action_pi = pi


def get_quickview_action_plugin():
    return current_qv_action_pi


class ShowQuickviewAction(InterfaceAction):

    name = 'Quickview'
    action_spec = (_('Quickview'), 'quickview.png', _('Toggle Quickview'), 'Q')
    dont_add_to = frozenset(('context-menu-device',))
    action_type = 'current'

    current_instance = None

    def genesis(self):
        self.menuless_qaction.changed.connect(self.update_layout_button)
        self.qaction.triggered.connect(self.toggle_quick_view)
        self.focus_action = QAction(self.gui)
        self.gui.addAction(self.focus_action)
        self.gui.keyboard.register_shortcut('Focus To Quickview', _('Focus to Quickview'),
                     description=_('Move the focus to the Quickview panel/window'),
                     default_keys=('Shift+Q',), action=self.focus_action,
                     group=self.action_spec[0])
        self.focus_action.triggered.connect(self.focus_quickview)

        self.focus_bl_action = QAction(self.gui)
        self.gui.addAction(self.focus_bl_action)
        self.gui.keyboard.register_shortcut('Focus from Quickview',
                     _('Focus from Quickview to the book list'),
                     description=_('Move the focus from Quickview to the book list'),
                     default_keys=('Shift+Alt+Q',), action=self.focus_bl_action,
                     group=self.action_spec[0])
        self.focus_bl_action.triggered.connect(self.focus_booklist)

        self.focus_refresh_action = QAction(self.gui)
        self.gui.addAction(self.focus_refresh_action)
        self.gui.keyboard.register_shortcut('Refresh from Quickview',
                     _('Refresh Quickview'),
                     description=_('Refresh the information shown in the Quickview panel'),
                     action=self.focus_refresh_action,
                     group=self.action_spec[0])
        self.focus_refresh_action.triggered.connect(self.refill_quickview)

        self.search_action = QAction(self.gui)
        self.gui.addAction(self.search_action)
        self.gui.keyboard.register_shortcut('Search from Quickview', _('Search from Quickview'),
                     description=_('Search for the currently selected Quickview item'),
                     default_keys=('Shift+S',), action=self.search_action,
                     group=self.action_spec[0])
        self.search_action.triggered.connect(self.search_quickview)

    def update_layout_button(self):
        self.qv_button.update_shortcut(self.menuless_qaction)

    def toggle_quick_view(self):
        if self.current_instance and not self.current_instance.is_closed:
            self._hide_quickview()
        else:
            self._show_quickview()

    @property
    def qv_button(self):
        return self.gui.layout_container.quick_view_button

    def initialization_complete(self):
        set_quickview_action_plugin(self)
        self.qv_button.toggled.connect(self.toggle_quick_view)

    def show_on_startup(self):
        self.gui.hide_panel('quick_view')
        self._show_quickview()

    def _hide_quickview(self):
        '''
        This is called only from the QV button toggle
        '''
        if self.current_instance:
            if not self.current_instance.is_closed:
                self.current_instance._reject()
            self.current_instance = None

    def _show_quickview(self, *args):
        '''
        This is called only from the QV button toggle
        '''
        if self.current_instance:
            if not self.current_instance.is_closed:
                self.current_instance._reject()
            self.current_instance = None
        if self.gui.current_view() is not self.gui.library_view:
            error_dialog(self.gui, _('No quickview available'),
                _('Quickview is not available for books '
                  'on the device.')).exec()
            return
        self.qv_button.blockSignals(True)
        self.qv_button.set_state_to_hide()
        self.qv_button.blockSignals(False)
        index = self.gui.library_view.currentIndex()
        self.current_instance = Quickview(self.gui, index, self.qaction.shortcut(),
                                          focus_booklist_shortcut=self.focus_bl_action.shortcut())

        self.current_instance.reopen_after_dock_change.connect(self.open_quickview)
        self.current_instance.show()
        self.current_instance.quickview_closed.connect(self.qv_button.set_state_to_show)

    def open_quickview(self):
        '''
        QV moved from/to dock. Close and reopen the pane/window.
        Also called when QV is closed and the user asks to move the focus
        '''
        if self.current_instance and not self.current_instance.is_closed:
            self.current_instance.reject()
        self.current_instance = None
        self.qaction.triggered.emit()

    def refill_quickview(self):
        '''
        Called when the columns shown in the QV pane might have changed.
        '''
        if self.current_instance and not self.current_instance.is_closed:
            self.current_instance.refill()

    def refresh_quickview(self, idx):
        '''
        Called when the data shown in the QV pane might have changed.
        '''
        if self.current_instance and not self.current_instance.is_closed:
            self.current_instance.refresh(idx)

    def change_quickview_column(self, idx, show=True):
        '''
        Called from the column header context menu to change the QV query column
        '''
        if show or (self.current_instance and not self.current_instance.is_closed):
            self.focus_quickview()
            self.current_instance.slave(idx)
            # This is needed because if this method is invoked from the library
            # view header context menu, the library view takes back the focus. I
            # don't know if this happens for any context menu.
            QTimer.singleShot(0, self.current_instance.set_focus)

    def library_changed(self, db):
        '''
        If QV is open, close it then reopen it so the columns are correct
        '''
        if self.current_instance and not self.current_instance.is_closed:
            self.current_instance.reject()
            self.qaction.triggered.emit()

    def focus_quickview(self):
        '''
        Used to move the focus to the QV books table. Open QV if needed
        '''
        if not self.current_instance or self.current_instance.is_closed:
            self.open_quickview()
        else:
            self.current_instance.set_focus()

    def focus_booklist(self):
        self.gui.activateWindow()
        self.gui.library_view.setFocus()

    def search_quickview(self):
        if not self.current_instance or self.current_instance.is_closed:
            return
        self.current_instance.do_search()
