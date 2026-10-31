"""
G810 Shared Library Driver using libg810-led.so and libg810_bridge.so via ctypes.
Enables native, in-process LED hardware control without spawning subprocesses.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path
from typing import List, Optional

from .driver_base import DeviceInfo, KeyboardDriver


class C_DeviceInfo(ctypes.Structure):
    _fields_ = [
        ("manufacturer", ctypes.c_char * 64),
        ("product", ctypes.c_char * 128),
        ("vendor_id", ctypes.c_char * 8),
        ("product_id", ctypes.c_char * 8),
        ("serial_number", ctypes.c_char * 128),
    ]


class G810Driver(KeyboardDriver):
    """
    Direct hardware driver communicating through libg810-led.so and libg810_bridge.so.
    """

    def __init__(self, lib_path: Optional[str] = None, bridge_path: Optional[str] = None):
        self._bridge_path = bridge_path or self._find_bridge_library()
        self._lib_path = lib_path or self._find_g810_library()

        self._libg810: Optional[ctypes.CDLL] = None
        self._bridge: Optional[ctypes.CDLL] = None
        self._handle: Optional[int] = None
        self._current_device: Optional[DeviceInfo] = None

        self._load_libraries()
        self._init_handle()

    @property
    def driver_name(self) -> str:
        return "Logitech G810 Native Shared Library"

    # -----------------------------------------------------------------
    # Library Discovery & Loading
    # -----------------------------------------------------------------

    @staticmethod
    def _find_g810_library() -> Optional[str]:
        """Locates libg810-led.so (bundled, system apt package, or dynamic search)."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            repo_root / "lib" / "libg810-led.so",
            repo_root / "lib" / "libg810-led.so.0",
            repo_root / "lib" / "libg810-led.so.0.4.3",
            repo_root.parent / "g810-led-gui" / "lib" / "libg810-led.so",
            "/usr/lib/libg810-led.so",
            "/usr/lib/libg810-led.so.0",
            "/usr/local/lib/libg810-led.so",
            "/usr/local/lib/libg810-led.so.0",
            "/usr/lib/x86_64-linux-gnu/libg810-led.so",
            "/usr/lib/x86_64-linux-gnu/libg810-led.so.0",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)

        sys_lib = ctypes.util.find_library("g810-led")
        if sys_lib:
            return sys_lib
        return None

    @staticmethod
    def _find_bridge_library() -> Optional[str]:
        """Locates libg810_bridge.so."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            repo_root / "lib" / "libg810_bridge.so",
            repo_root / "c_bridge" / "libg810_bridge.so",
            Path(sys.prefix) / "lib" / "libg810_bridge.so",
            "/usr/lib/libg810_bridge.so",
            "/usr/local/lib/libg810_bridge.so",
            "/usr/lib/x86_64-linux-gnu/libg810_bridge.so",
            "/usr/lib/g810-led-gui-app/libg810_bridge.so",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)

        sys_lib = ctypes.util.find_library("g810_bridge")
        if sys_lib:
            return sys_lib
        return None

    def _load_libraries(self) -> None:
        """Loads libg810-led.so and libg810_bridge.so via ctypes."""
        if self._lib_path and os.path.isfile(self._lib_path):
            try:
                self._libg810 = ctypes.CDLL(self._lib_path, mode=ctypes.RTLD_GLOBAL)
            except Exception as e:
                print(f"[G810Driver] Warning: Failed loading libg810-led.so from {self._lib_path}: {e}", file=sys.stderr)

        if not self._bridge_path or not os.path.isfile(self._bridge_path):
            raise RuntimeError(
                f"libg810_bridge.so not found. Please compile it in c_bridge/ (make)."
            )

        try:
            self._bridge = ctypes.CDLL(self._bridge_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load bridge library {self._bridge_path}: {e}")

        # Configure ctypes function signatures
        b = self._bridge

        b.kbd_create.restype = ctypes.c_void_p
        b.kbd_create.argtypes = []

        b.kbd_destroy.restype = None
        b.kbd_destroy.argtypes = [ctypes.c_void_p]

        b.kbd_is_open.restype = ctypes.c_int
        b.kbd_is_open.argtypes = [ctypes.c_void_p]

        b.kbd_open.restype = ctypes.c_int
        b.kbd_open.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_char_p]

        b.kbd_close.restype = None
        b.kbd_close.argtypes = [ctypes.c_void_p]

        b.kbd_commit.restype = ctypes.c_int
        b.kbd_commit.argtypes = [ctypes.c_void_p]

        b.kbd_set_all_keys.restype = ctypes.c_int
        b.kbd_set_all_keys.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]

        b.kbd_set_region.restype = ctypes.c_int
        b.kbd_set_region.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]

        b.kbd_set_group_keys.restype = ctypes.c_int
        b.kbd_set_group_keys.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]

        b.kbd_set_key.restype = ctypes.c_int
        b.kbd_set_key.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]

        b.kbd_set_startup_mode.restype = ctypes.c_int
        b.kbd_set_startup_mode.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

        b.kbd_set_native_effect.restype = ctypes.c_int
        b.kbd_set_native_effect.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint16,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint8,
        ]

        b.kbd_list_devices.restype = ctypes.c_int
        b.kbd_list_devices.argtypes = [ctypes.c_void_p, ctypes.POINTER(C_DeviceInfo), ctypes.c_int]

    def _init_handle(self) -> None:
        if self._bridge and not self._handle:
            self._handle = self._bridge.kbd_create()

    def __del__(self) -> None:
        self.close_device()
        if self._bridge and self._handle:
            try:
                self._bridge.kbd_destroy(self._handle)
                self._handle = None
            except Exception:
                pass

    # -----------------------------------------------------------------
    # Device State & Connection
    # -----------------------------------------------------------------

    def is_open(self) -> bool:
        if not self._bridge or not self._handle:
            return False
        return bool(self._bridge.kbd_is_open(self._handle))

    def _ensure_open(self) -> bool:
        """Ensures the keyboard hardware is opened, opening default or selected device if needed."""
        if self.is_open():
            return True

        if self._current_device:
            return self.open_device(self._current_device)

        # Open default detected keyboard
        return bool(self._bridge.kbd_open(self._handle, 0, 0, None))

    def list_devices(self) -> List[DeviceInfo]:
        """Scans and returns compatible devices."""
        self._init_handle()
        max_devs = 32
        arr = (C_DeviceInfo * max_devs)()
        cnt = self._bridge.kbd_list_devices(self._handle, arr, max_devs)

        devices: List[DeviceInfo] = []
        seen = set()

        for i in range(cnt):
            raw = arr[i]
            vid = raw.vendor_id.decode("utf-8", errors="ignore").strip()
            pid = raw.product_id.decode("utf-8", errors="ignore").strip()
            serial = raw.serial_number.decode("utf-8", errors="ignore").strip()
            mfg = raw.manufacturer.decode("utf-8", errors="ignore").strip() or "Logitech"
            prod = raw.product.decode("utf-8", errors="ignore").strip() or "Keyboard"

            key = (vid, pid, serial)
            if key not in seen:
                seen.add(key)
                devices.append(
                    DeviceInfo(
                        vendor_id=vid,
                        product_id=pid,
                        serial_number=serial,
                        manufacturer=mfg,
                        product=prod,
                        driver_name=self.driver_name,
                    )
                )

        return devices

    def open_device(self, device: DeviceInfo) -> bool:
        """Opens communication with the specified keyboard device."""
        self._init_handle()
        self.close_device()

        vid = int(device.vendor_id, 16) if device.vendor_id else 0
        pid = int(device.product_id, 16) if device.product_id else 0
        serial_bytes = device.serial_number.encode("utf-8") if device.serial_number else None

        ok = bool(self._bridge.kbd_open(self._handle, vid, pid, serial_bytes))
        if ok:
            self._current_device = device
        return ok

    def close_device(self) -> None:
        """Closes hardware communication."""
        if self._bridge and self._handle and self.is_open():
            self._bridge.kbd_close(self._handle)

    # -----------------------------------------------------------------
    # Hardware LED Actions
    # -----------------------------------------------------------------

    def commit(self) -> bool:
        """Commits pending LED updates to hardware."""
        if not self._ensure_open():
            return False
        return bool(self._bridge.kbd_commit(self._handle))

    def set_all_keys(self, r: int, g: int, b: int) -> bool:
        """Sets color for all keys."""
        if not self._ensure_open():
            return False
        return bool(self._bridge.kbd_set_all_keys(self._handle, r, g, b))

    def set_group_keys(self, group: str, r: int, g: int, b: int) -> bool:
        """Sets color for a designated group of keys."""
        if not self._ensure_open():
            return False
        return bool(
            self._bridge.kbd_set_group_keys(
                self._handle, group.encode("utf-8"), r, g, b
            )
        )

    def set_key(self, key_name: str, r: int, g: int, b: int) -> bool:
        """Sets color for an individual single key."""
        if not self._ensure_open():
            return False
        return bool(
            self._bridge.kbd_set_key(
                self._handle, key_name.encode("utf-8"), r, g, b
            )
        )

    def set_region(self, region: int, r: int, g: int, b: int) -> bool:
        """Sets color for a hardware lighting region (e.g. G213 zones)."""
        if not self._ensure_open():
            return False
        return bool(self._bridge.kbd_set_region(self._handle, region, r, g, b))

    def set_startup_mode(self, mode: str) -> bool:
        """Sets power-on startup mode (wave or color)."""
        if not self._ensure_open():
            return False
        return bool(
            self._bridge.kbd_set_startup_mode(self._handle, mode.encode("utf-8"))
        )

    def set_native_effect(
        self,
        effect_name: str,
        target_name: str,
        period_ms: int,
        r: int,
        g: int,
        b: int,
    ) -> bool:
        """Activates a native hardware effect onboard the keyboard."""
        if not self._ensure_open():
            return False
        return bool(
            self._bridge.kbd_set_native_effect(
                self._handle,
                effect_name.encode("utf-8"),
                target_name.encode("utf-8"),
                period_ms,
                r,
                g,
                b,
            )
        )
