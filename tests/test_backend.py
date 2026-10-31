import os
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gui.backend import G810LedBackend, ProfileCommand, DeviceInfo


class TestG810LedBackend(unittest.TestCase):
    def setUp(self):
        self.backend = G810LedBackend()

    def test_find_binary(self):
        path = self.backend.find_binary()
        self.assertTrue(os.path.exists(path) or path == "g810-led")

    def test_list_keyboards(self):
        devices = self.backend.list_keyboards()
        # The connected keyboard should be detected or returned empty in restricted env
        self.assertIsInstance(devices, list)
        for d in devices:
            self.assertIsInstance(d, DeviceInfo)
            self.assertTrue(len(d.vendor_id) > 0)
            self.assertTrue(len(d.product_id) > 0)

    def test_parse_and_serialize_profile(self):
        sample = """
        # Test Profile
        a 00ff00 # Set all keys green
        g fkeys ff0000
        k w 0000ff
        c
        """
        cmds = self.backend.parse_profile(sample)
        self.assertEqual(len(cmds), 4)
        self.assertEqual(cmds[0].cmd_type, "a")
        self.assertEqual(cmds[0].color, "00ff00")
        self.assertEqual(cmds[1].cmd_type, "g")
        self.assertEqual(cmds[1].target, "fkeys")
        self.assertEqual(cmds[1].color, "ff0000")
        self.assertEqual(cmds[2].cmd_type, "k")
        self.assertEqual(cmds[2].target, "w")
        self.assertEqual(cmds[2].color, "0000ff")
        self.assertEqual(cmds[3].cmd_type, "c")

        serialized = self.backend.serialize_profile(cmds, "Test Header")
        self.assertIn("a 00ff00", serialized)
        self.assertIn("g fkeys ff0000", serialized)
        self.assertIn("k w 0000ff", serialized)
        self.assertIn("c", serialized)

    def test_sample_profiles_discovery(self):
        samples = self.backend.get_sample_profiles()
        self.assertIsInstance(samples, list)
        self.assertTrue(len(samples) > 0)
        names = [s[0] for s in samples]
        self.assertIn("group_keys", names)
        self.assertIn("all_blue", names)

    def test_help_text(self):
        help_general = self.backend.get_help_text("general")
        self.assertIn("Usage: g810-led", help_general)

        help_keys = self.backend.get_help_text("keys")
        self.assertIn("Group List", help_keys)

        help_effects = self.backend.get_help_text("effects")
        self.assertIn("Activate an on-board lighting effect", help_effects)


if __name__ == "__main__":
    unittest.main()

