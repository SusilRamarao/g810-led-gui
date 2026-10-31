"""
Abstract Base Class for Keyboard LED Hardware Drivers.
Enables pluggable multi-vendor keyboard support (Logitech, Corsair, OpenRGB, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class DeviceInfo:
    vendor_id: str
    product_id: str
    serial_number: str
    manufacturer: str
    product: str
    driver_name: str = "Generic"

    @property
    def display_name(self) -> str:
        prod = self.product.strip() or "RGB Keyboard"
        return f"{prod} [{self.vendor_id}:{self.product_id}] ({self.serial_number or 'No S/N'})"


class KeyboardDriver(ABC):
    """Abstract interface that every keyboard vendor backend must implement."""

    @property
    @abstractmethod
    def driver_name(self) -> str:
        """Name of the driver/vendor (e.g. 'Logitech G810-LED')."""
        pass

    @abstractmethod
    def list_devices(self) -> List[DeviceInfo]:
        """Scans and returns compatible devices for this driver."""
        pass

    @abstractmethod
    def open_device(self, device: DeviceInfo) -> bool:
        """Opens communication with the specified keyboard."""
        pass

    @abstractmethod
    def close_device(self) -> None:
        """Closes hardware communication."""
        pass

    @abstractmethod
    def commit(self) -> bool:
        """Commits pending LED state changes to the hardware."""
        pass

    @abstractmethod
    def set_all_keys(self, r: int, g: int, b: int) -> bool:
        """Sets color for all keys."""
        pass

    @abstractmethod
    def set_group_keys(self, group: str, r: int, g: int, b: int) -> bool:
        """Sets color for a designated group of keys."""
        pass

    @abstractmethod
    def set_key(self, key_name: str, r: int, g: int, b: int) -> bool:
        """Sets color for an individual single key."""
        pass

    @abstractmethod
    def set_region(self, region: int, r: int, g: int, b: int) -> bool:
        """Sets color for a hardware lighting region (e.g. G213 zones)."""
        pass

    @abstractmethod
    def set_startup_mode(self, mode: str) -> bool:
        """Sets power-on startup mode (e.g. 'wave', 'color')."""
        pass

    @abstractmethod
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
        pass
