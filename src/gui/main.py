#!/usr/bin/env python3
"""
Entry point for g810-led-gui.
"""

import os
import sys
from pathlib import Path

# Ensure src directory is in sys.path
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import gi

try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gtk, Gdk
except ValueError as e:
    print(f"Error: Required GTK 4 libraries not found: {e}", file=sys.stderr)
    print("Please install python3-gi and libgtk-4-1.", file=sys.stderr)
    sys.exit(1)

from gui.backend import G810LedBackend
from gui.app import G810LedApplication


def main() -> int:
    # Check for graphical display
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not has_display:
        print("Warning: No DISPLAY or WAYLAND_DISPLAY environment variable detected.", file=sys.stderr)
        print("g810-led-gui is a graphical application that must be run inside an X11 or Wayland desktop session.", file=sys.stderr)

    backend = G810LedBackend()
    app = G810LedApplication(backend)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

