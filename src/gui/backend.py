"""
Backend communication layer and data abstractions for g810-led.
Interacts with the native shared library driver (libg810-led.so) and manages keyboard states and profiles.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from core.driver_base import DeviceInfo

try:
    from core.g810_driver import G810Driver
except ImportError:
    try:
        from ..core.g810_driver import G810Driver
    except ImportError:
        G810Driver = None


@dataclass
class ProfileCommand:
    cmd_type: str  # 'a', 'an', 'g', 'gn', 'k', 'kn', 'r', 'fx', 'c', 'var'
    target: str = ""
    color: str = ""
    speed: str = ""
    extra: str = ""
    comment: str = ""

    def to_line(self) -> str:
        parts = [self.cmd_type]
        if self.cmd_type in ("a", "an"):
            if self.color:
                parts.append(self.color)
        elif self.cmd_type in ("g", "gn", "k", "kn", "r"):
            if self.target:
                parts.append(self.target)
            if self.color:
                parts.append(self.color)
        elif self.cmd_type == "fx":
            if self.target:
                parts.append(self.target)
            if self.extra:
                parts.append(self.extra)
            if self.color:
                parts.append(self.color)
            if self.speed:
                parts.append(self.speed)
        elif self.cmd_type == "var":
            if self.target:
                parts.append(self.target)
            if self.color:
                parts.append(self.color)
        elif self.cmd_type == "c":
            pass
        else:
            if self.target:
                parts.append(self.target)
            if self.color:
                parts.append(self.color)
            if self.speed:
                parts.append(self.speed)

        line = " ".join(parts)
        if self.comment:
            line += f" # {self.comment}"
        return line


class G810LedBackend:
    """Core controller communicating with g810-led shared library / binary."""

    KEY_GROUPS = [
        "logo",
        "indicators",
        "fkeys",
        "modifiers",
        "multimedia",
        "arrows",
        "numeric",
        "functions",
        "keys",
        "gkeys",
    ]

    EFFECTS = [
        "color",
        "breathing",
        "cycle",
        "waves",
        "hwave",
        "vwave",
        "cwave",
    ]

    STARTUP_MODES = ["wave", "color"]

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or self.find_binary()
        self.selected_device: Optional[DeviceInfo] = None
        self.use_pkexec: bool = False
        self._trial_snapshot: Optional[List[str]] = None
        self._is_in_trial: bool = False

        self.driver: Optional[G810Driver] = None
        if G810Driver is not None:
            try:
                self.driver = G810Driver()
            except Exception as e:
                print(f"[Backend] Note: Native driver init deferred or unavailable: {e}")
                self.driver = None

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        clean = hex_str.lstrip("#").strip()
        if len(clean) == 6:
            try:
                return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)
            except ValueError:
                pass
        return 0, 0, 0

    @staticmethod
    def find_binary() -> str:
        """Locates the g810-led executable."""
        repo_bin = Path(__file__).resolve().parent.parent.parent / "bin" / "g810-led"
        if repo_bin.is_file() and os.access(repo_bin, os.X_OK):
            return str(repo_bin)

        cwd_bin = Path("bin/g810-led")
        if cwd_bin.is_file() and os.access(cwd_bin, os.X_OK):
            return str(cwd_bin.resolve())

        system_bin = shutil.which("g810-led")
        if system_bin:
            return system_bin

        for candidate in ["/usr/bin/g810-led", "/usr/local/bin/g810-led"]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        return "g810-led"

    def select_device(self, device: DeviceInfo) -> bool:
        """Selects and opens communication with the specified keyboard."""
        self.selected_device = device
        if self.driver:
            return self.driver.open_device(device)
        return True

    def run_raw(
        self,
        args: List[str],
        stdin_data: Optional[str] = None,
        use_pkexec: Optional[bool] = None,
    ) -> Tuple[bool, str, str]:
        """Runs the g810-led binary with specified arguments (fallback path)."""
        pk = self.use_pkexec if use_pkexec is None else use_pkexec

        cmd: List[str] = []
        if pk:
            cmd.extend(["pkexec"])

        cmd.append(self.binary_path)

        if self.selected_device:
            if self.selected_device.vendor_id:
                cmd.extend(["-dv", self.selected_device.vendor_id])
            if self.selected_device.product_id:
                cmd.extend(["-dp", self.selected_device.product_id])
            if self.selected_device.serial_number:
                cmd.extend(["-ds", self.selected_device.serial_number])

        cmd.extend(args)

        try:
            res = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=10,
            )
            success = res.returncode == 0
            return success, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out."
        except FileNotFoundError:
            return False, "", f"Binary not found: {self.binary_path}"
        except Exception as ex:
            return False, "", str(ex)

    def list_keyboards(self) -> List[DeviceInfo]:
        """Scans and returns compatible keyboards via native shared library (or fallback)."""
        if self.driver:
            try:
                devs = self.driver.list_devices()
                if devs:
                    return devs
            except Exception:
                pass

        success, out, err = self.run_raw(["--list-keyboards"])
        devices: List[DeviceInfo] = []
        if not success and not out:
            return devices

        current: Dict[str, str] = {}
        for line in out.splitlines():
            line_str = line.strip()
            if line.startswith("Device:"):
                if current:
                    devices.append(self._create_device_info(current))
                    current = {}
                parts = line.split("Device:", 1)[1].strip()
                if " - " in parts:
                    mfg, prod = parts.split(" - ", 1)
                    current["mfg"] = mfg.strip()
                    current["prod"] = prod.strip()
                else:
                    current["mfg"] = "Logitech"
                    current["prod"] = parts.strip()
            elif "Vendor ID:" in line_str:
                current["vendor"] = line_str.split("Vendor ID:", 1)[1].strip()
            elif "Product ID:" in line_str:
                current["product"] = line_str.split("Product ID:", 1)[1].strip()
            elif "Serial Number:" in line_str:
                current["serial"] = line_str.split("Serial Number:", 1)[1].strip()

        if current:
            devices.append(self._create_device_info(current))

        deduped: List[DeviceInfo] = []
        seen = set()
        for d in devices:
            key = (d.vendor_id, d.product_id, d.serial_number)
            if key not in seen:
                seen.add(key)
                deduped.append(d)

        return deduped

    @staticmethod
    def _create_device_info(d: Dict[str, str]) -> DeviceInfo:
        return DeviceInfo(
            vendor_id=d.get("vendor", ""),
            product_id=d.get("product", ""),
            serial_number=d.get("serial", ""),
            manufacturer=d.get("mfg", "Logitech"),
            product=d.get("prod", "Keyboard"),
            driver_name="G810 CLI",
        )

    # -------------------------------------------------------------
    # AC 1a: Lighting control methods
    # -------------------------------------------------------------

    def set_all_keys(self, color_hex: str, commit: bool = True) -> Tuple[bool, str]:
        """Sets the color for all keys (-a or -an)."""
        color_hex = color_hex.lstrip("#").lower()
        if self.driver and not self.use_pkexec:
            r, g, b = self._hex_to_rgb(color_hex)
            ok = self.driver.set_all_keys(r, g, b)
            if commit and ok:
                self.driver.commit()
            return ok, "" if ok else "Failed to set all keys"

        cmd = ["-a" if commit else "-an", color_hex]
        success, out, err = self.run_raw(cmd)
        return success, err or out

    def set_group_color(
        self, group: str, color_hex: str, commit: bool = True
    ) -> Tuple[bool, str]:
        """Sets color for a specific key group (-g or -gn)."""
        color_hex = color_hex.lstrip("#").lower()
        if self.driver and not self.use_pkexec:
            r, g, b = self._hex_to_rgb(color_hex)
            ok = self.driver.set_group_keys(group, r, g, b)
            if commit and ok:
                self.driver.commit()
            return ok, "" if ok else f"Failed to set group {group}"

        cmd = ["-g" if commit else "-gn", group, color_hex]
        success, out, err = self.run_raw(cmd)
        return success, err or out

    def set_key_color(
        self, key: str, color_hex: str, commit: bool = True
    ) -> Tuple[bool, str]:
        """Sets color for a specific single key (-k or -kn)."""
        color_hex = color_hex.lstrip("#").lower()
        if self.driver and not self.use_pkexec:
            r, g, b = self._hex_to_rgb(color_hex)
            ok = self.driver.set_key(key, r, g, b)
            if commit and ok:
                self.driver.commit()
            return ok, "" if ok else f"Failed to set key {key}"

        cmd = ["-k" if commit else "-kn", key, color_hex]
        success, out, err = self.run_raw(cmd)
        return success, err or out

    def set_region_color(self, region: int, color_hex: str) -> Tuple[bool, str]:
        """Sets color for a region (-r, e.g. for G213 keyboards)."""
        color_hex = color_hex.lstrip("#").lower()
        if self.driver and not self.use_pkexec:
            r, g, b = self._hex_to_rgb(color_hex)
            ok = self.driver.set_region(region, r, g, b)
            if ok:
                self.driver.commit()
            return ok, "" if ok else f"Failed to set region {region}"

        cmd = ["-r", str(region), color_hex]
        success, out, err = self.run_raw(cmd)
        return success, err or out

    def set_effect(
        self,
        effect_name: str,
        target: str = "all",
        color_hex: Optional[str] = None,
        speed: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Activates native on-board lighting effect (-fx)."""
        if self.driver and not self.use_pkexec:
            r, g, b = self._hex_to_rgb(color_hex) if color_hex else (0, 0, 0)
            period_ms = int(speed) if speed and speed.isdigit() else 1000
            ok = self.driver.set_native_effect(effect_name, target, period_ms, r, g, b)
            return ok, "" if ok else f"Failed to activate effect {effect_name}"

        cmd = ["-fx", effect_name, target]
        if color_hex:
            cmd.append(color_hex.lstrip("#").lower())
        if speed:
            cmd.append(speed)
        success, out, err = self.run_raw(cmd)
        return success, err or out

    def commit(self) -> Tuple[bool, str]:
        """Commits changes (-c)."""
        if self.driver and not self.use_pkexec:
            ok = self.driver.commit()
            return ok, "" if ok else "Failed to commit"

        success, out, err = self.run_raw(["-c"])
        return success, err or out

    # -------------------------------------------------------------
    # AC 3: Startup Mode
    # -------------------------------------------------------------

    def set_startup_mode(self, mode: str) -> Tuple[bool, str]:
        """Sets keyboard power-on startup mode (--startup-mode wave|color)."""
        if mode not in self.STARTUP_MODES:
            return False, f"Invalid startup mode: {mode}"

        if self.driver and not self.use_pkexec:
            ok = self.driver.set_startup_mode(mode)
            return ok, "" if ok else f"Failed to set startup mode {mode}"

        cmd = ["--startup-mode", mode]
        success, out, err = self.run_raw(cmd)
        return success, err or out

    # -------------------------------------------------------------
    # AC 1b: Trial and Error option (Live preview & revert)
    # -------------------------------------------------------------

    def start_trial(self, initial_snapshot_commands: Optional[List[str]] = None) -> None:
        """Starts trial mode, storing a snapshot to revert to if needed."""
        self._trial_snapshot = initial_snapshot_commands or []
        self._is_in_trial = True

    def is_trial_active(self) -> bool:
        return self._is_in_trial

    def revert_trial(self) -> Tuple[bool, str]:
        """Reverts the keyboard to the snapshot state captured before trial."""
        if not self._is_in_trial or self._trial_snapshot is None:
            return True, "No active trial snapshot to revert."

        snapshot_content = "\n".join(self._trial_snapshot)
        if snapshot_content.strip():
            success, err = self.apply_profile_text(snapshot_content)
        else:
            success, err = True, ""

        self._is_in_trial = False
        self._trial_snapshot = None
        return success, err

    def apply_trial(self) -> Tuple[bool, str]:
        """Confirms the trial changes and commits them permanently."""
        success, err = self.commit()
        self._is_in_trial = False
        self._trial_snapshot = None
        return success, err

    # -------------------------------------------------------------
    # AC 2: Profiles (Create, Load, Save, Apply)
    # -------------------------------------------------------------

    def apply_profile_file(self, filepath: str) -> Tuple[bool, str]:
        """Loads and applies a profile from file (-p <filepath>)."""
        if not os.path.isfile(filepath):
            return False, f"File not found: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return self.apply_profile_text(content)
        except Exception as e:
            return False, str(e)

    def apply_profile_text(self, profile_text: str) -> Tuple[bool, str]:
        """Applies profile text commands, using direct in-process driver or CLI pipe."""
        if self.driver and not self.use_pkexec:
            cmds = self.parse_profile(profile_text)
            has_explicit_commit = False
            for c in cmds:
                if c.cmd_type in ("a", "an"):
                    r, g, b = self._hex_to_rgb(c.color)
                    self.driver.set_all_keys(r, g, b)
                elif c.cmd_type in ("g", "gn"):
                    r, g, b = self._hex_to_rgb(c.color)
                    self.driver.set_group_keys(c.target, r, g, b)
                elif c.cmd_type in ("k", "kn"):
                    r, g, b = self._hex_to_rgb(c.color)
                    self.driver.set_key(c.target, r, g, b)
                elif c.cmd_type == "r":
                    r, g, b = self._hex_to_rgb(c.color)
                    reg_num = int(c.target) if c.target.isdigit() else 1
                    self.driver.set_region(reg_num, r, g, b)
                elif c.cmd_type == "fx":
                    r, g, b = self._hex_to_rgb(c.color) if c.color else (0, 0, 0)
                    spd = int(c.speed) if c.speed and c.speed.isdigit() else 1000
                    tgt = c.extra or "all"
                    self.driver.set_native_effect(c.target, tgt, spd, r, g, b)
                elif c.cmd_type == "c":
                    has_explicit_commit = True
                    self.driver.commit()

            if not has_explicit_commit and any(c.cmd_type in ("a", "g", "k", "r") for c in cmds):
                self.driver.commit()
            return True, ""

        success, out, err = self.run_raw(["-pp"], stdin_data=profile_text)
        return success, err or out

    @staticmethod
    def parse_profile(content: str) -> List[ProfileCommand]:
        """Parses profile file contents into structured ProfileCommands."""
        commands: List[ProfileCommand] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            comment = ""
            if "#" in line:
                line, comment = line.split("#", 1)
                line = line.strip()
                comment = comment.strip()

            tokens = line.split()
            if not tokens:
                continue

            cmd_type = tokens[0]
            target = ""
            color = ""
            speed = ""
            extra = ""

            if cmd_type in ("a", "an"):
                color = tokens[1] if len(tokens) > 1 else ""
            elif cmd_type in ("g", "gn", "k", "kn", "r", "var"):
                target = tokens[1] if len(tokens) > 1 else ""
                color = tokens[2] if len(tokens) > 2 else ""
            elif cmd_type == "fx":
                target = tokens[1] if len(tokens) > 1 else ""
                extra = tokens[2] if len(tokens) > 2 else ""
                if len(tokens) == 4:
                    val = tokens[3]
                    if len(val) == 6 and all(c in "0123456789abcdefABCDEF" for c in val):
                        color = val
                    else:
                        speed = val
                elif len(tokens) > 4:
                    color = tokens[3]
                    speed = tokens[4]
            elif cmd_type == "c":
                pass
            else:
                target = tokens[1] if len(tokens) > 1 else ""
                color = tokens[2] if len(tokens) > 2 else ""

            commands.append(
                ProfileCommand(
                    cmd_type=cmd_type,
                    target=target,
                    color=color,
                    speed=speed,
                    extra=extra,
                    comment=comment,
                )
            )
        return commands

    @staticmethod
    def serialize_profile(commands: List[ProfileCommand], header: str = "") -> str:
        """Serializes a list of ProfileCommands into profile file text format."""
        lines = []
        if header:
            lines.append(f"# {header}")
        lines.append("# Generated by g810-led-gui\n")

        for cmd in commands:
            lines.append(cmd.to_line())

        if not any(c.cmd_type == "c" for c in commands):
            lines.append("c # Commit changes")

        return "\n".join(lines) + "\n"

    def get_sample_profiles(self) -> List[Tuple[str, str]]:
        """Returns list of (profile_name, absolute_filepath) for bundled sample profiles."""
        results: List[Tuple[str, str]] = []

        repo_samples = (
            Path(__file__).resolve().parent.parent.parent / "sample_profiles"
        )
        dirs_to_check = [repo_samples, Path("/etc/g810-led/samples")]

        for directory in dirs_to_check:
            if directory.is_dir():
                for item in sorted(directory.iterdir()):
                    if item.is_file() and not item.name.startswith("."):
                        results.append((item.name, str(item)))
                if results:
                    break

        return results

    # -------------------------------------------------------------
    # AC 5: Help Information
    # -------------------------------------------------------------

    def get_help_text(self, topic: str = "general") -> str:
        """Retrieves help text, using built-in reference documentation or CLI."""
        builtins = {
            "general": """Usage: g810-led [OPTIONS...]
Control Logitech RGB mechanical and membrane keyboards.

OPTIONS:
  -a, -an <color>         Set all keys color (commit / no-commit)
  -g, -gn <group> <color> Set group keys color
  -k, -kn <key> <color>   Set single key color
  -r <region> <color>     Set region color (for zone keyboards like G213)
  -fx <effect> <target>   Activate native hardware lighting effect
  --startup-mode <mode>   Set power-on mode (wave or color)
  -p <profile>            Load and apply profile file
  -c                      Commit pending changes
  --list-keyboards        List connected Logitech keyboards
""",
            "keys": """Group List:
  logo        Logitech G Logo
  indicators  Caps, Num, Scroll lock, Game, Backlight LEDs
  fkeys       F1 to F12 keys
  modifiers   Ctrl, Shift, Alt, Win, Menu keys
  multimedia  Next, Prev, Stop, Play/Pause, Mute keys
  arrows      Arrow navigation keys (up, down, left, right)
  numeric     Numpad keys
  functions   Esc, Print, Scroll, Pause, Insert, Del, Home, End, PgUp, PgDn
  keys        Standard alphanumeric QWERTY/AZERTY keys
  gkeys       G1 to G9 dedicated macro keys

Keys List:
  a-z, 0-9, f1-f12, space, enter, esc, tab, backspace, caps_lock,
  shift_left, shift_right, ctrl_left, ctrl_right, alt_left, alt_right,
  win_left, win_right, arrow_top, arrow_bottom, arrow_left, arrow_right,
  insert, delete, home, end, page_up, page_down, num_lock, numenter, ...
""",
            "effects": """Native On-Board Lighting Effects:
  color     Fixed color (target: all, keys, logo)
  breathing Pulsing color animation (target: all, keys, logo)
  cycle     Color spectrum cycling through RGB hues
  waves     Rainbow wave across keys
  hwave     Horizontal rainbow wave
  vwave     Vertical rainbow wave
  cwave     Center outward circular wave
""",
            "samples": """Sample Profile Scripts:
  a 00ff00               # Set all keys to green
  g fkeys ff0000         # Set F-keys to red
  k space 0000ff         # Set Spacebar to blue
  c                      # Commit changes to hardware

Profiles can be saved and loaded directly from the Profile Editor tab.
""",
        }

        if shutil.which(self.binary_path) or (
            os.path.isfile(self.binary_path) and os.access(self.binary_path, os.X_OK)
        ):
            flag_map = {
                "general": "--help",
                "keys": "--help-keys",
                "effects": "--help-effects",
                "samples": "--help-samples",
            }
            flag = flag_map.get(topic, "--help")
            success, out, err = self.run_raw([flag])
            if success and out.strip():
                return out

        return builtins.get(topic, builtins["general"])
