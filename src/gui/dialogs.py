"""
Dialogs and helper windows for g810-led GUI.
Includes Help Submenu window, Permission Guide, and Profile Rule editor.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango
from typing import Optional


class HelpDialog(Gtk.Window):
    """Help & Reference Window corresponding to AC 5."""

    def __init__(self, parent_window: Optional[Gtk.Window], backend):
        super().__init__()
        self.set_title("g810-led Help & Reference")
        self.set_default_size(720, 520)
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.backend = backend

        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)
        self.set_child(vbox)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_lbl = Gtk.Label(label="<b>g810-led Documentation &amp; Reference</b>")
        title_lbl.set_use_markup(True)
        title_lbl.set_xalign(0)
        title_box.append(title_lbl)
        vbox.append(title_box)

        # Notebook tabs
        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        vbox.append(notebook)

        # Tabs content
        notebook.append_page(
            self._create_text_page(self.backend.get_help_text("general")),
            Gtk.Label(label="General Usage"),
        )
        notebook.append_page(
            self._create_text_page(self.backend.get_help_text("keys")),
            Gtk.Label(label="Keys & Groups"),
        )
        notebook.append_page(
            self._create_text_page(self.backend.get_help_text("effects")),
            Gtk.Label(label="Lighting Effects"),
        )
        notebook.append_page(
            self._create_text_page(self.backend.get_help_text("samples")),
            Gtk.Label(label="Usage Samples"),
        )
        notebook.append_page(
            self._create_about_page(),
            Gtk.Label(label="About"),
        )

        # Close button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.END)
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda b: self.destroy())
        btn_box.append(close_btn)
        vbox.append(btn_box)

    def _create_text_page(self, text_content: str) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_left_margin(12)
        text_view.set_right_margin(12)
        text_view.set_top_margin(12)
        text_view.set_bottom_margin(12)

        buffer = text_view.get_buffer()
        buffer.set_text(text_content)

        scrolled.set_child(text_view)
        return scrolled

    def _create_about_page(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_margin_top(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)

        title = Gtk.Label(label="<big><b>g810-led GUI</b></big>")
        title.set_use_markup(True)
        title.set_xalign(0)
        vbox.append(title)

        desc = Gtk.Label(
            label="Linux LED controller GUI for Logitech Keyboards:\n"
            "G213, G410, G413, G512, G513, G610, G810, G815, G910 and GPRO.\n\n"
            "Features:\n"
            "• Color, group, and region configuration\n"
            "• Native hardware lighting effects\n"
            "• Live trial and error preview with revert\n"
            "• Profile creation, loading, and saving\n"
            "• Power-on startup mode configuration\n"
            "• Multiple keyboard selection\n\n"
            "License: GNU General Public License v3.0\n"
            "Original CLI Author: MatMoul & Contributors"
        )
        desc.set_xalign(0)
        desc.set_wrap(True)
        vbox.append(desc)

        return vbox


class PermissionDialog(Gtk.Window):
    """Helper dialog displaying udev setup instructions if permission is denied."""

    def __init__(self, parent_window: Optional[Gtk.Window]):
        super().__init__()
        self.set_title("USB Permissions Configuration")
        self.set_default_size(580, 360)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        self.set_child(vbox)

        lbl_head = Gtk.Label(label="<b>Direct USB Access Setup</b>")
        lbl_head.set_use_markup(True)
        lbl_head.set_xalign(0)
        vbox.append(lbl_head)

        lbl_info = Gtk.Label(
            label="Logitech keyboards require udev rules so non-root users can write "
            "lighting configurations directly via USB without typing sudo.\n\n"
            "To grant standard user permissions, run the following commands in terminal:"
        )
        lbl_info.set_wrap(True)
        lbl_info.set_xalign(0)
        vbox.append(lbl_info)

        # Code block
        cmd_text = (
            "sudo cp udev/g810-led.rules /etc/udev/rules.d/\n"
            "sudo udevadm control --reload-rules\n"
            "sudo udevadm trigger"
        )
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_monospace(True)
        tv.set_left_margin(10)
        tv.set_right_margin(10)
        tv.set_top_margin(10)
        tv.set_bottom_margin(10)
        tv.get_buffer().set_text(cmd_text)
        scrolled.set_child(tv)
        vbox.append(scrolled)

        lbl_alt = Gtk.Label(
            label="Alternatively, enable <i>Run as Root (pkexec)</i> in the top bar."
        )
        lbl_alt.set_use_markup(True)
        lbl_alt.set_xalign(0)
        vbox.append(lbl_alt)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.END)
        close_btn = Gtk.Button(label="Got It")
        close_btn.connect("clicked", lambda b: self.destroy())
        btn_box.append(close_btn)
        vbox.append(btn_box)

