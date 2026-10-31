import os
import sys
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.driver_base import DeviceInfo, KeyboardDriver
from core.g810_driver import G810Driver


class TestG810Driver(unittest.TestCase):
    def setUp(self):
        self.driver = G810Driver()

    def test_driver_initialization(self):
        self.assertEqual(self.driver.driver_name, "Logitech G810 Native Shared Library")
        self.assertIsNotNone(self.driver._bridge)
        self.assertIsNotNone(self.driver._handle)

    def test_list_devices(self):
        devices = self.driver.list_devices()
        self.assertIsInstance(devices, list)
        for d in devices:
            self.assertIsInstance(d, DeviceInfo)
            self.assertTrue(len(d.vendor_id) > 0)
            self.assertTrue(len(d.product_id) > 0)
            self.assertEqual(d.driver_name, "Logitech G810 Native Shared Library")

    def test_is_open(self):
        # Hardware isOpen query should return a boolean without crashing
        state = self.driver.is_open()
        self.assertIsInstance(state, bool)


if __name__ == "__main__":
    unittest.main()
