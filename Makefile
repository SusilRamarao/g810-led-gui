# Top-level Makefile for g810-led-gui-app

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
APPDIR ?= $(PREFIX)/share/applications
PYTHON ?= python3

.PHONY: all bridge gui run test clean check-deps install

all: bridge
	@chmod +x bin/g810-led-gui
	@echo "=========================================================="
	@echo "Build complete!"
	@echo "Run 'make gui' or './bin/g810-led-gui' to launch the app."
	@echo "=========================================================="

bridge:
	@echo "Building C bridge (libg810_bridge.so)..."
	$(MAKE) -C c_bridge

gui: bridge
	@./bin/g810-led-gui

run: gui

bin: bridge
	@chmod +x bin/g810-led-gui
	@echo "Binaries and launcher ready."

test: bridge
	@echo "Running test suite..."
	$(PYTHON) -m unittest discover tests

clean:
	$(MAKE) -C c_bridge clean
	rm -rf __pycache__ src/*/__pycache__ tests/__pycache__

check-deps:
	@echo "Checking system dependencies..."
	@$(PYTHON) -c "import gi; gi.require_version('Gtk', '4.0'); print('  [OK] Python GObject & GTK 4')" 2>/dev/null || echo "  [MISSING] GTK 4 (run: sudo apt install python3-gi libgtk-4-1)"
	@test -f lib/libg810-led.so && echo "  [OK] libg810-led.so" || echo "  [MISSING] lib/libg810-led.so"
	@echo "Dependency check finished."
