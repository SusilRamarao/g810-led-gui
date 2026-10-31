# g810-led-gui-app

A standalone, modern **GTK 4** graphical controller for Logitech mechanical and membrane keyboards (G213, G410, G413, G512, G513, G610, G810, G815, G910, G Pro).

Communicates directly in-process with `libg810-led.so` through an `extern "C"` bridge via Python `ctypes` for real-time, low-latency LED and profile control without subprocess overhead.

---

## Features

- **Colors & Key Groups**: Configure full keyboard illumination, single keys, or key groups (F-keys, modifiers, multimedia, logo, arrows, numpad).
- **Native Hardware Effects**: Activate on-board breathing, color cycle, waves (horizontal, vertical, circular), and fixed colors.
- **Trial & Error Live Preview**: Test LED adjustments live on the keyboard with an instant "Keep & Commit" or "Revert" transaction buffer.
- **Profile Manager**: Create, load, edit, and save `.profile` files, with bundled sample profiles and syntax help.
- **Hardware Startup & Boot Modes**: Configure hardware power-on default modes (`wave` or `color`) and system boot profile persistence.
- **Multi-Device Support**: Scan and select connected Logitech RGB keyboards dynamically.
- **Zero-Process Direct Binding**: Links directly to `libg810-led.so` and `hidapi-hidraw` for instant 60 FPS hardware updates.

---

## Architecture

Detailed architecture specifications, layers, and operational flowcharts are documented in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

```text
+-------------------------------------------------------------+
| Presentation Layer (GTK 4 / Python)                        |
|   src/gui/app.py | src/gui/dialogs.py | src/gui/main.py     |
+------------------------------|------------------------------+
                               v
+-------------------------------------------------------------+
| State & Controller Layer (Python)                           |
|   src/gui/backend.py (Trial buffer & Profile engine)        |
+------------------------------|------------------------------+
                               v
+-------------------------------------------------------------+
| Hardware Abstraction Layer - HAL (Python)                   |
|   src/core/driver_base.py & src/core/g810_driver.py         |
+------------------------------|------------------------------+
                               v (ctypes C ABI)
+-------------------------------------------------------------+
| Native C Bridge & Shared Objects (C / C++)                  |
|   lib/libg810_bridge.so -> lib/libg810-led.so -> hidapi     |
+------------------------------|------------------------------+
                               v
+-------------------------------------------------------------+
| Physical Hardware (Logitech Keyboards via USB HID)          |
+-------------------------------------------------------------+
```

---

## Prerequisites

On Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3-gi libgtk-4-1 libhidapi-hidraw0 g++ make
```

---

## Building and Running

### 1. Build the Native Bridge
To compile the C bridge (`libg810_bridge.so`) and link with `libg810-led.so`:
```bash
make
```
*(Or `make bridge`)*

### 2. Launch the Application
```bash
make gui
```
Or directly execute the launcher:
```bash
./bin/g810-led-gui
```

### 3. Run the Test Suite
```bash
make test
```

### 4. Verify System Dependencies
```bash
make check-deps
```

### 5. Clean Build Artifacts
```bash
make clean
```

---

## USB Device Permissions (udev)

To access USB HID devices without requiring `root` or `pkexec`, install the udev rule:
```bash
sudo cp /home/susil-ramarao/Desktop/projects/open_source/g810-led-gui/udev/g810-led.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Alternatively, you can toggle the **"Root (pkexec)"** switch inside the application header bar.

---

## License

GPL-3.0 License.
