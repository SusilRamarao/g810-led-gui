"""
Main GTK 4 Application and UI Window for g810-led-gui.
Implements Acceptance Criteria 1a, 1b, 2, 3, 4, and 5.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from .backend import G810LedBackend, DeviceInfo, ProfileCommand
from .dialogs import HelpDialog, PermissionDialog


class ColorSwatchBox(Gtk.Box):
    """Convenient color picker widget with Hex entry, visual swatch, and quick palette."""

    PRESETS = [
        ("Red", "ff0000"),
        ("Green", "00ff00"),
        ("Blue", "0000ff"),
        ("Yellow", "ffff00"),
        ("Cyan", "00ffff"),
        ("Magenta", "ff00ff"),
        ("Orange", "ff7700"),
        ("Purple", "800080"),
        ("White", "ffffff"),
        ("Off (Black)", "000000"),
    ]

    def __init__(self, initial_hex: str = "00ff00", on_color_changed=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_color_changed = on_color_changed
        self._current_hex = initial_hex.lstrip("#").lower()

        # Input and Swatch row
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.append(row)

        lbl = Gtk.Label(label="Color (Hex):")
        row.append(lbl)

        self.entry = Gtk.Entry()
        self.entry.set_text(self._current_hex)
        self.entry.set_max_length(6)
        self.entry.set_width_chars(8)
        self.entry.connect("changed", self._on_entry_changed)
        row.append(self.entry)

        # Color preview button
        self.swatch_btn = Gtk.Button(label="  ")
        self._update_swatch_css()
        self.swatch_btn.connect("clicked", self._open_color_dialog)
        row.append(self.swatch_btn)

        # Quick palette chips
        palette_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for name, hex_val in self.PRESETS:
            chip = Gtk.Button(label=name)
            chip.connect("clicked", lambda b, h=hex_val: self.set_color(h))
            palette_box.append(chip)

        palette_scroll = Gtk.ScrolledWindow()
        palette_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        palette_scroll.set_child(palette_box)
        self.append(palette_scroll)

    def get_color(self) -> str:
        return self._current_hex

    def set_color(self, hex_val: str) -> None:
        self._current_hex = hex_val.lstrip("#").lower()
        self.entry.set_text(self._current_hex)
        self._update_swatch_css()
        if self.on_color_changed:
            self.on_color_changed(self._current_hex)

    def _on_entry_changed(self, entry: Gtk.Entry) -> None:
        val = entry.get_text().strip().lstrip("#")
        if len(val) == 6 and all(c in "0123456789abcdefABCDEF" for c in val):
            self._current_hex = val.lower()
            self._update_swatch_css()
            if self.on_color_changed:
                self.on_color_changed(self._current_hex)

    def _update_swatch_css(self) -> None:
        css = f"""
        button {{
            background: #{self._current_hex};
            border: 1px solid #555;
            min-width: 32px;
            min-height: 24px;
            border-radius: 4px;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        self.swatch_btn.get_style_context().add_provider(
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _open_color_dialog(self, btn) -> None:
        try:
            # GTK 4.10+ ColorDialog
            if hasattr(Gtk, "ColorDialog"):
                dialog = Gtk.ColorDialog()
                rgba = Gdk.RGBA()
                rgba.parse(f"#{self._current_hex}")

                def on_finish(dialog, result):
                    try:
                        chosen = dialog.choose_rgba_finish(result)
                        if chosen:
                            r = int(chosen.red * 255)
                            g = int(chosen.green * 255)
                            b = int(chosen.blue * 255)
                            self.set_color(f"{r:02x}{g:02x}{b:02x}")
                    except Exception:
                        pass

                root = self.get_root()
                dialog.choose_rgba(root if isinstance(root, Gtk.Window) else None, rgba, None, on_finish)
        except Exception:
            pass


class MainWindow(Gtk.ApplicationWindow):
    """Main Application Window."""

    ALL_KEYS_LIST = [
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        "escape", "space", "enter", "tab", "backspace", "caps_lock",
        "shift_left", "shift_right", "ctrl_left", "ctrl_right",
        "alt_left", "alt_right", "win_left", "win_right", "menu",
        "arrow_top", "arrow_bottom", "arrow_left", "arrow_right",
        "insert", "delete", "home", "end", "page_up", "page_down",
        "print_screen", "scroll_lock", "pause_break",
        "num_lock", "numenter", "logo", "mute", "play_pause"
    ]

    def __init__(self, app: Gtk.Application, backend: G810LedBackend):
        super().__init__(application=app)
        self.backend = backend
        self.set_title("g810-led Keyboard Controller")
        self.set_default_size(860, 640)

        self.current_profile_commands: List[ProfileCommand] = []

        self._build_header_bar()
        self._build_main_layout()

        self._refresh_keyboards()

    # -------------------------------------------------------------
    # UI Layout Builders
    # -------------------------------------------------------------

    def _build_header_bar(self) -> None:
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Keyboard selector dropdown (AC 4)
        kb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        kb_lbl = Gtk.Label(label="Keyboard:")
        kb_box.append(kb_lbl)

        self.device_combo = Gtk.DropDown()
        self.device_combo.connect("notify::selected", self._on_device_selected)
        kb_box.append(self.device_combo)

        # Refresh button
        refresh_btn = Gtk.Button(label="🔄 Refresh")
        refresh_btn.set_tooltip_text("Scan for connected Logitech keyboards")
        refresh_btn.connect("clicked", lambda b: self._refresh_keyboards())
        kb_box.append(refresh_btn)
        header.pack_start(kb_box)

        # Right side: pkexec toggle & Help button (AC 5)
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Run as root toggle
        pk_lbl = Gtk.Label(label="Root (pkexec):")
        right_box.append(pk_lbl)
        self.pk_switch = Gtk.Switch()
        self.pk_switch.set_active(False)
        self.pk_switch.connect("state-set", self._on_pkexec_toggled)
        self.pk_switch.set_tooltip_text("Run commands using pkexec if USB access is denied")
        right_box.append(self.pk_switch)

        # Help button
        help_btn = Gtk.Button(label="❓ Help")
        help_btn.set_tooltip_text("Open Help, Keys, Effects and Samples guide")
        help_btn.connect("clicked", self._open_help_dialog)
        right_box.append(help_btn)

        header.pack_end(right_box)

    def _build_main_layout(self) -> None:
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_vbox.set_margin_top(8)
        main_vbox.set_margin_bottom(8)
        main_vbox.set_margin_start(12)
        main_vbox.set_margin_end(12)
        self.set_child(main_vbox)

        # AC 1b: Trial & Error Mode Control Bar
        trial_frame = Gtk.Frame()
        trial_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        trial_box.set_margin_top(6)
        trial_box.set_margin_bottom(6)
        trial_box.set_margin_start(10)
        trial_box.set_margin_end(10)
        trial_frame.set_child(trial_box)

        trial_title = Gtk.Label(label="<b>Trial &amp; Error (Live Preview)</b>")
        trial_title.set_use_markup(True)
        trial_box.append(trial_title)

        self.trial_switch = Gtk.Switch()
        self.trial_switch.connect("state-set", self._on_trial_switch_toggled)
        self.trial_switch.set_tooltip_text(
            "When ON, changes are immediately sent to the keyboard for visual trial"
        )
        trial_box.append(self.trial_switch)

        self.trial_apply_btn = Gtk.Button(label="✔ Keep & Commit")
        self.trial_apply_btn.set_sensitive(False)
        self.trial_apply_btn.connect("clicked", self._on_trial_commit_clicked)
        trial_box.append(self.trial_apply_btn)

        self.trial_revert_btn = Gtk.Button(label="↺ Revert")
        self.trial_revert_btn.set_sensitive(False)
        self.trial_revert_btn.connect("clicked", self._on_trial_revert_clicked)
        trial_box.append(self.trial_revert_btn)

        self.trial_status_lbl = Gtk.Label(
            label="<i>Live test disabled. Changes will commit normally.</i>"
        )
        self.trial_status_lbl.set_use_markup(True)
        self.trial_status_lbl.set_hexpand(True)
        self.trial_status_lbl.set_xalign(0)
        trial_box.append(self.trial_status_lbl)

        main_vbox.append(trial_frame)

        # Notebook for main sections
        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        main_vbox.append(notebook)

        # Tab 1: Colors & Groups (AC 1a)
        notebook.append_page(self._build_colors_tab(), Gtk.Label(label="🎨 Colors & Groups"))

        # Tab 2: Lighting Effects (AC 1a)
        notebook.append_page(self._build_effects_tab(), Gtk.Label(label="✨ Lighting Effects"))

        # Tab 3: Profiles (AC 2)
        notebook.append_page(self._build_profiles_tab(), Gtk.Label(label="📁 Profiles"))

        # Tab 4: Startup & Hardware (AC 3 & AC 4)
        notebook.append_page(self._build_startup_tab(), Gtk.Label(label="⚙ Startup & Hardware"))

        # Status Bar at bottom
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.status_lbl = Gtk.Label(label="Ready")
        self.status_lbl.set_xalign(0)
        self.status_lbl.set_hexpand(True)
        status_box.append(self.status_lbl)

        self.perm_helper_btn = Gtk.Button(label="USB Permission Help")
        self.perm_helper_btn.set_visible(False)
        self.perm_helper_btn.connect("clicked", lambda b: PermissionDialog(self).present())
        status_box.append(self.perm_helper_btn)

        main_vbox.append(status_box)

    # -------------------------------------------------------------
    # Tab 1: Colors & Groups (AC 1a)
    # -------------------------------------------------------------

    def _build_colors_tab(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        scrolled.set_child(vbox)

        # Section A: All Keys Color
        all_frame = Gtk.Frame(label="All Keys (-a)")
        all_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        all_box.set_margin_top(8)
        all_box.set_margin_bottom(8)
        all_box.set_margin_start(10)
        all_box.set_margin_end(10)
        all_frame.set_child(all_box)

        self.all_swatch = ColorSwatchBox(
            initial_hex="00ff00",
            on_color_changed=lambda col: self._on_live_trial_color("all", col),
        )
        all_box.append(self.all_swatch)

        apply_all_btn = Gtk.Button(label="Apply to All Keys")
        apply_all_btn.connect("clicked", self._on_apply_all_keys)
        all_box.append(apply_all_btn)
        vbox.append(all_frame)

        # Section B: Key Groups
        group_frame = Gtk.Frame(label="Key Groups (-g)")
        group_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        group_box.set_margin_top(8)
        group_box.set_margin_bottom(8)
        group_box.set_margin_start(10)
        group_box.set_margin_end(10)
        group_frame.set_child(group_box)

        grp_sel_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        grp_lbl = Gtk.Label(label="Select Group:")
        grp_sel_box.append(grp_lbl)

        group_names = G810LedBackend.KEY_GROUPS
        model = Gtk.StringList.new(group_names)
        self.group_combo = Gtk.DropDown.new(model=model)
        grp_sel_box.append(self.group_combo)
        group_box.append(grp_sel_box)

        self.group_swatch = ColorSwatchBox(
            initial_hex="ff0000",
            on_color_changed=lambda col: self._on_live_trial_color("group", col),
        )
        group_box.append(self.group_swatch)

        apply_group_btn = Gtk.Button(label="Apply to Group")
        apply_group_btn.connect("clicked", self._on_apply_group)
        group_box.append(apply_group_btn)
        vbox.append(group_frame)

        # Section C: G213 Regions (-r)
        region_frame = Gtk.Frame(label="G213 Regions (-r)")
        region_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        region_box.set_margin_top(8)
        region_box.set_margin_bottom(8)
        region_box.set_margin_start(10)
        region_box.set_margin_end(10)
        region_frame.set_child(region_box)

        r_sel_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        r_lbl = Gtk.Label(label="Select Region (1-5):")
        r_sel_box.append(r_lbl)

        r_model = Gtk.StringList.new(["Region 1", "Region 2", "Region 3", "Region 4", "Region 5"])
        self.region_combo = Gtk.DropDown.new(model=r_model)
        r_sel_box.append(self.region_combo)
        region_box.append(r_sel_box)

        self.region_swatch = ColorSwatchBox(initial_hex="00ffff")
        region_box.append(self.region_swatch)

        apply_region_btn = Gtk.Button(label="Apply to Region")
        apply_region_btn.connect("clicked", self._on_apply_region)
        region_box.append(apply_region_btn)
        vbox.append(region_frame)

        # Section D: Individual Key (-k)
        key_frame = Gtk.Frame(label="Individual Key (-k)")
        key_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        key_box.set_margin_top(8)
        key_box.set_margin_bottom(8)
        key_box.set_margin_start(10)
        key_box.set_margin_end(10)
        key_frame.set_child(key_box)

        key_sel_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        k_lbl = Gtk.Label(label="Select Key:")
        key_sel_box.append(k_lbl)

        k_model = Gtk.StringList.new(self.ALL_KEYS_LIST)
        self.key_combo = Gtk.DropDown.new(model=k_model)
        key_sel_box.append(self.key_combo)
        key_box.append(key_sel_box)

        self.key_swatch = ColorSwatchBox(
            initial_hex="ffffff",
            on_color_changed=lambda col: self._on_live_trial_color("key", col),
        )
        key_box.append(self.key_swatch)

        apply_key_btn = Gtk.Button(label="Apply to Single Key")
        apply_key_btn.connect("clicked", self._on_apply_single_key)
        key_box.append(apply_key_btn)
        vbox.append(key_frame)

        return scrolled

    # -------------------------------------------------------------
    # Tab 2: Lighting Effects (AC 1a)
    # -------------------------------------------------------------

    def _build_effects_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)

        info_lbl = Gtk.Label(
            label="<i>Native hardware effects execute onboard without CPU load. "
            "Supported effects: breathing, cycle, waves, hwave, vwave, cwave, color.</i>"
        )
        info_lbl.set_use_markup(True)
        info_lbl.set_xalign(0)
        vbox.append(info_lbl)

        # Effect Type
        row_fx = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_fx.append(Gtk.Label(label="Effect Type:"))
        fx_model = Gtk.StringList.new(G810LedBackend.EFFECTS)
        self.fx_combo = Gtk.DropDown.new(model=fx_model)
        row_fx.append(self.fx_combo)
        vbox.append(row_fx)

        # Target (all, keys, logo)
        row_target = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_target.append(Gtk.Label(label="Target:"))
        target_model = Gtk.StringList.new(["all", "keys", "logo"])
        self.fx_target_combo = Gtk.DropDown.new(model=target_model)
        row_target.append(self.fx_target_combo)
        vbox.append(row_target)

        # Effect Color (for breathing and fixed color)
        color_frame = Gtk.Frame(label="Effect Color (for breathing & fixed color)")
        color_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        color_box.set_margin_top(6)
        color_box.set_margin_bottom(6)
        color_box.set_margin_start(8)
        color_box.set_margin_end(8)
        self.fx_swatch = ColorSwatchBox(initial_hex="00ff00")
        color_box.append(self.fx_swatch)
        color_frame.set_child(color_box)
        vbox.append(color_frame)

        # Speed / Period
        row_speed = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_speed.append(Gtk.Label(label="Speed / Period (Hex or ms):"))
        self.fx_speed_entry = Gtk.Entry()
        self.fx_speed_entry.set_text("10")
        self.fx_speed_entry.set_tooltip_text(
            "Examples: 10 (hex value for 256ms multiples), 500ms, or 2s"
        )
        row_speed.append(self.fx_speed_entry)
        vbox.append(row_speed)

        # Activate Button
        btn_apply_fx = Gtk.Button(label="✨ Activate Lighting Effect (-fx)")
        btn_apply_fx.connect("clicked", self._on_apply_effect)
        vbox.append(btn_apply_fx)

        return vbox

    # -------------------------------------------------------------
    # Tab 3: Profiles (AC 2)
    # -------------------------------------------------------------

    def _build_profiles_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)

        # Sample Profiles Quick Load
        sample_frame = Gtk.Frame(label="Bundled Sample Profiles")
        sample_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sample_box.set_margin_top(8)
        sample_box.set_margin_bottom(8)
        sample_box.set_margin_start(10)
        sample_box.set_margin_end(10)
        sample_frame.set_child(sample_box)

        self.sample_profiles = self.backend.get_sample_profiles()
        sample_names = [s[0] for s in self.sample_profiles] or ["(None found)"]
        sample_model = Gtk.StringList.new(sample_names)
        self.sample_combo = Gtk.DropDown.new(model=sample_model)
        sample_box.append(self.sample_combo)

        load_sample_btn = Gtk.Button(label="Load Sample")
        load_sample_btn.connect("clicked", self._on_load_sample_clicked)
        sample_box.append(load_sample_btn)

        apply_sample_btn = Gtk.Button(label="Apply Sample Directly")
        apply_sample_btn.connect("clicked", self._on_apply_sample_clicked)
        sample_box.append(apply_sample_btn)

        vbox.append(sample_frame)

        # File actions: Open, Save, Apply
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        open_btn = Gtk.Button(label="📂 Load Profile File...")
        open_btn.connect("clicked", self._on_open_profile_dialog)
        action_bar.append(open_btn)

        save_btn = Gtk.Button(label="💾 Save Profile...")
        save_btn.connect("clicked", self._on_save_profile_dialog)
        action_bar.append(save_btn)

        apply_profile_btn = Gtk.Button(label="▶ Apply Current Profile to Keyboard")
        apply_profile_btn.connect("clicked", self._on_apply_current_profile)
        action_bar.append(apply_profile_btn)

        vbox.append(action_bar)

        # Profile commands editor
        editor_frame = Gtk.Frame(label="Profile Content & Commands")
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        editor_frame.set_child(editor_box)
        vbox.append(editor_frame)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.profile_text_view = Gtk.TextView()
        self.profile_text_view.set_monospace(True)
        self.profile_text_view.set_left_margin(10)
        self.profile_text_view.set_right_margin(10)
        self.profile_text_view.set_top_margin(10)
        self.profile_text_view.set_bottom_margin(10)
        self.profile_text_view.get_buffer().set_text(
            "# Custom Profile\na 00ff00 # Set all green\nc # Commit\n"
        )
        scrolled.set_child(self.profile_text_view)
        editor_box.append(scrolled)

        return vbox

    # -------------------------------------------------------------
    # Tab 4: Startup & Hardware (AC 3 & AC 4)
    # -------------------------------------------------------------

    def _build_startup_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)

        # Device Info panel (AC 4)
        info_frame = Gtk.Frame(label="Current Keyboard Hardware Info")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_margin_top(10)
        info_box.set_margin_bottom(10)
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)
        info_frame.set_child(info_box)

        self.device_detail_lbl = Gtk.Label(
            label="Manufacturer: Logitech\nVendor ID: --\nProduct ID: --\nSerial Number: --"
        )
        self.device_detail_lbl.set_xalign(0)
        info_box.append(self.device_detail_lbl)
        vbox.append(info_frame)

        # AC 3: Set Startup Mode Button
        startup_frame = Gtk.Frame(label="Startup Power-on Mode (AC 3)")
        startup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        startup_box.set_margin_top(10)
        startup_box.set_margin_bottom(10)
        startup_box.set_margin_start(12)
        startup_box.set_margin_end(12)
        startup_frame.set_child(startup_box)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mode_row.append(Gtk.Label(label="Startup Mode:"))

        mode_model = Gtk.StringList.new(["wave", "color"])
        self.startup_combo = Gtk.DropDown.new(model=mode_model)
        mode_row.append(self.startup_combo)

        startup_btn = Gtk.Button(label="⚡ Set Startup Mode")
        startup_btn.connect("clicked", self._on_set_startup_mode_clicked)
        mode_row.append(startup_btn)
        startup_box.append(mode_row)

        desc = Gtk.Label(
            label="• <b>wave</b>: Shows the default Logitech RGB wave animation on power-up.\n"
            "• <b>color</b>: Restores the user-stored color/profile on power-up."
        )
        desc.set_use_markup(True)
        desc.set_xalign(0)
        startup_box.append(desc)

        vbox.append(startup_frame)

        # System Boot Profile helper
        boot_frame = Gtk.Frame(label="System Boot Profile (/etc/g810-led/profile)")
        boot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        boot_box.set_margin_top(10)
        boot_box.set_margin_bottom(10)
        boot_box.set_margin_start(12)
        boot_box.set_margin_end(12)
        boot_frame.set_child(boot_box)

        boot_desc = Gtk.Label(
            label="When the system boots or wakes from sleep, udev launches "
            "<tt>/etc/g810-led/profile</tt>. You can write your current profile "
            "to make it the permanent boot profile."
        )
        boot_desc.set_use_markup(True)
        boot_desc.set_xalign(0)
        boot_desc.set_wrap(True)
        boot_box.append(boot_desc)

        set_boot_btn = Gtk.Button(label="Save Current Profile as System Boot Profile")
        set_boot_btn.connect("clicked", self._on_save_boot_profile_clicked)
        boot_box.append(set_boot_btn)
        vbox.append(boot_frame)

        return vbox

    # -------------------------------------------------------------
    # Controller Actions & Handlers
    # -------------------------------------------------------------

    def _refresh_keyboards(self) -> None:
        """AC 4: Scans for connected keyboards."""
        devices = self.backend.list_keyboards()
        self.devices = devices

        names = [d.display_name for d in devices]
        if not names:
            names = ["No keyboards detected (or permission required)"]

        model = Gtk.StringList.new(names)
        self.device_combo.set_model(model)
        self.device_combo.set_selected(0)

        if devices:
            self.backend.select_device(devices[0])
            self._update_device_info_display(devices[0])
            self.set_status(f"Connected: {devices[0].product}", success=True)
        else:
            self.backend.selected_device = None
            self.set_status(
                "No Logitech keyboards detected. Check USB connection or permissions.",
                success=False,
            )

    def _on_device_selected(self, drop_down, param) -> None:
        idx = drop_down.get_selected()
        if hasattr(self, "devices") and 0 <= idx < len(self.devices):
            dev = self.devices[idx]
            self.backend.select_device(dev)
            self._update_device_info_display(dev)
            self.set_status(f"Selected device: {dev.display_name}", success=True)

    def _update_device_info_display(self, dev: DeviceInfo) -> None:
        prod = GLib.markup_escape_text(dev.product)
        mfg = GLib.markup_escape_text(dev.manufacturer)
        vid = GLib.markup_escape_text(dev.vendor_id)
        pid = GLib.markup_escape_text(dev.product_id)
        sn = GLib.markup_escape_text(dev.serial_number or 'N/A')
        text = (
            f"<b>Device:</b> {prod}\n"
            f"<b>Manufacturer:</b> {mfg}\n"
            f"<b>Vendor ID:</b> {vid}\n"
            f"<b>Product ID:</b> {pid}\n"
            f"<b>Serial Number:</b> {sn}"
        )
        self.device_detail_lbl.set_markup(text)

    def _on_pkexec_toggled(self, switch, state) -> bool:
        self.backend.use_pkexec = state
        self.set_status(f"Root privilege elevation (pkexec): {'ON' if state else 'OFF'}")
        return False

    def _open_help_dialog(self, btn) -> None:
        """AC 5: Opens the Help reference modal."""
        dialog = HelpDialog(self, self.backend)
        dialog.present()

    # -------------------------------------------------------------
    # AC 1b: Trial & Error Mode Handlers
    # -------------------------------------------------------------

    def _on_trial_switch_toggled(self, switch, state) -> bool:
        if state:
            # Entering trial mode: snapshot current text commands from editor
            buf = self.profile_text_view.get_buffer()
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            self.backend.start_trial([text])
            self.trial_apply_btn.set_sensitive(True)
            self.trial_revert_btn.set_sensitive(True)
            self.trial_status_lbl.set_markup(
                "<span foreground='#e5a50a'><b>Trial Mode Active:</b> Adjust colors to see them live on your keyboard!</span>"
            )
            self.set_status("Trial & Error Mode enabled. Changes are staged live.", success=True)
        else:
            if self.backend.is_trial_active():
                self._on_trial_commit_clicked(None)
            self.trial_apply_btn.set_sensitive(False)
            self.trial_revert_btn.set_sensitive(False)
            self.trial_status_lbl.set_markup(
                "<i>Live test disabled. Changes will commit normally.</i>"
            )

        return False

    def _on_live_trial_color(self, target_type: str, color_hex: str) -> None:
        """Sends uncommitted color command if trial mode is active."""
        if not self.backend.is_trial_active():
            return

        if target_type == "all":
            self.backend.set_all_keys(color_hex, commit=False)
        elif target_type == "group":
            idx = self.group_combo.get_selected()
            group_name = G810LedBackend.KEY_GROUPS[idx]
            self.backend.set_group_color(group_name, color_hex, commit=False)
        elif target_type == "key":
            idx = self.key_combo.get_selected()
            key_name = self.ALL_KEYS_LIST[idx]
            self.backend.set_key_color(key_name, color_hex, commit=False)

    def _on_trial_commit_clicked(self, btn) -> None:
        success, msg = self.backend.apply_trial()
        self.trial_switch.set_active(False)
        self.set_status("Trial changes committed permanently.", success=success)

    def _on_trial_revert_clicked(self, btn) -> None:
        success, msg = self.backend.revert_trial()
        self.trial_switch.set_active(False)
        self.set_status("Reverted to pre-trial state.", success=success)

    # -------------------------------------------------------------
    # AC 1a: Colors, Groups & Effects Handlers
    # -------------------------------------------------------------

    def _on_apply_all_keys(self, btn) -> None:
        color = self.all_swatch.get_color()
        commit = not self.backend.is_trial_active()
        success, msg = self.backend.set_all_keys(color, commit=commit)
        action_desc = "previewed" if not commit else "applied"
        self._handle_result(success, f"All keys {action_desc} with color #{color}", msg)

    def _on_apply_group(self, btn) -> None:
        idx = self.group_combo.get_selected()
        group_name = G810LedBackend.KEY_GROUPS[idx]
        color = self.group_swatch.get_color()
        commit = not self.backend.is_trial_active()
        success, msg = self.backend.set_group_color(group_name, color, commit=commit)
        action_desc = "previewed" if not commit else "applied"
        self._handle_result(success, f"Group '{group_name}' {action_desc} with #{color}", msg)

    def _on_apply_region(self, btn) -> None:
        idx = self.region_combo.get_selected() + 1
        color = self.region_swatch.get_color()
        success, msg = self.backend.set_region_color(idx, color)
        self._handle_result(success, f"Region {idx} set to #{color}", msg)

    def _on_apply_single_key(self, btn) -> None:
        idx = self.key_combo.get_selected()
        key_name = self.ALL_KEYS_LIST[idx]
        color = self.key_swatch.get_color()
        commit = not self.backend.is_trial_active()
        success, msg = self.backend.set_key_color(key_name, color, commit=commit)
        action_desc = "previewed" if not commit else "applied"
        self._handle_result(success, f"Key '{key_name}' {action_desc} with #{color}", msg)

    def _on_apply_effect(self, btn) -> None:
        fx_idx = self.fx_combo.get_selected()
        effect_name = G810LedBackend.EFFECTS[fx_idx]

        target_idx = self.fx_target_combo.get_selected()
        target = ["all", "keys", "logo"][target_idx]

        color = self.fx_swatch.get_color()
        speed = self.fx_speed_entry.get_text().strip() or "10"

        success, msg = self.backend.set_effect(
            effect_name=effect_name,
            target=target,
            color_hex=color if effect_name in ("color", "breathing") else None,
            speed=speed,
        )
        self._handle_result(success, f"Activated effect: {effect_name} on {target}", msg)

    # -------------------------------------------------------------
    # AC 2: Profiles Handlers
    # -------------------------------------------------------------

    def _on_load_sample_clicked(self, btn) -> None:
        idx = self.sample_combo.get_selected()
        if 0 <= idx < len(self.sample_profiles):
            name, path = self.sample_profiles[idx]
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.profile_text_view.get_buffer().set_text(content)
                self.set_status(f"Loaded sample profile: {name}", success=True)
            except Exception as ex:
                self.set_status(f"Failed to load sample: {ex}", success=False)

    def _on_apply_sample_clicked(self, btn) -> None:
        idx = self.sample_combo.get_selected()
        if 0 <= idx < len(self.sample_profiles):
            name, path = self.sample_profiles[idx]
            success, msg = self.backend.apply_profile_file(path)
            self._handle_result(success, f"Applied sample profile: {name}", msg)

    def _on_apply_current_profile(self, btn) -> None:
        buf = self.profile_text_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        success, msg = self.backend.apply_profile_text(text)
        self._handle_result(success, "Applied profile commands to keyboard", msg)

    def _on_open_profile_dialog(self, btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Profile File")

        def on_open_finish(dialog, res):
            try:
                gfile = dialog.open_finish(res)
                if gfile:
                    path = gfile.get_path()
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.profile_text_view.get_buffer().set_text(content)
                    self.set_status(f"Loaded profile: {path}", success=True)
            except Exception as ex:
                self.set_status(f"Error opening file: {ex}", success=False)

        dialog.open(self, None, on_open_finish)

    def _on_save_profile_dialog(self, btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Profile As")
        dialog.set_initial_name("custom.profile")

        def on_save_finish(dialog, res):
            try:
                gfile = dialog.save_finish(res)
                if gfile:
                    path = gfile.get_path()
                    buf = self.profile_text_view.get_buffer()
                    text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.set_status(f"Saved profile to {path}", success=True)
            except Exception as ex:
                self.set_status(f"Error saving profile: {ex}", success=False)

        dialog.save(self, None, on_save_finish)

    # -------------------------------------------------------------
    # AC 3: Startup Mode & Boot Profile Handlers
    # -------------------------------------------------------------

    def _on_set_startup_mode_clicked(self, btn) -> None:
        idx = self.startup_combo.get_selected()
        mode = G810LedBackend.STARTUP_MODES[idx]
        success, msg = self.backend.set_startup_mode(mode)
        self._handle_result(success, f"Startup mode set to: {mode}", msg)

    def _on_save_boot_profile_clicked(self, btn) -> None:
        buf = self.profile_text_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

        target_file = "/etc/g810-led/profile"
        try:
            # Write to a temp file and copy via pkexec if needed
            tmp_path = "/tmp/g810_boot_profile.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)

            cmd = ["pkexec", "cp", tmp_path, target_file]
            res = os.system(" ".join(cmd))
            if res == 0:
                self.set_status(f"Successfully saved to {target_file}", success=True)
            else:
                self.set_status("Failed to write /etc/g810-led/profile (needs root)", success=False)
        except Exception as ex:
            self.set_status(f"Failed to save boot profile: {ex}", success=False)

    # -------------------------------------------------------------
    # Status and Notification Helpers
    # -------------------------------------------------------------

    def _handle_result(self, success: bool, success_msg: str, err_msg: str) -> None:
        if success:
            self.set_status(success_msg, success=True)
            self.perm_helper_btn.set_visible(False)
        else:
            is_perm_issue = "Access denied" in err_msg or "privilege" in err_msg.lower()
            if is_perm_issue:
                self.set_status(
                    "Access denied: Run as root (pkexec) or configure udev rules.",
                    success=False,
                )
                self.perm_helper_btn.set_visible(True)
            else:
                self.set_status(f"Error: {err_msg.strip() or 'Command failed'}", success=False)

    def set_status(self, message: str, success: bool = True) -> None:
        color = "#2ec27e" if success else "#e01b24"
        escaped_msg = GLib.markup_escape_text(message)
        self.status_lbl.set_markup(f"<span foreground='{color}'>{escaped_msg}</span>")


class G810LedApplication(Gtk.Application):
    def __init__(self, backend: G810LedBackend):
        super().__init__(
            application_id="org.g810led.gui",
            flags=0,
        )
        self.backend = backend
        self.window: Optional[MainWindow] = None

    def do_activate(self) -> None:
        if not self.window:
            self.window = MainWindow(self, self.backend)
        self.window.present()

