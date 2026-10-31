# Architecture Document: g810-led-gui-app

## 1. Executive Summary

`g810-led-gui-app` is a modern, standalone graphical interface designed to control RGB lighting, animations, startup modes, and key profiles for Logitech mechanical and membrane keyboards (G213, G410, G413, G512, G513, G610, G810, G815, G910, G Pro).

Originally conceived inside the upstream C++ driver repository, this project decouples the user experience from the CLI binary and transitions the application into a clean multi-tiered architecture:
1. **GTK 4 Modern Presentation Layer**: Responsive graphical interface featuring live previews, color swatches, and profile authoring.
2. **Backend & Controller Layer**: Coordinates state transitions, transactional trial-and-error operations, and profile parsing.
3. **Hardware Driver Abstraction Layer (HAL)**: An abstract driver interface (`KeyboardDriver`) allowing multi-vendor expansion.
4. **C ABI Native Bridge Layer**: A shared library bridge (`libg810_bridge.so`) exposing a clean `extern "C"` ABI to Python `ctypes`.
5. **Hardware Protocol Engine**: Links directly against `libg810-led.so` and `hidapi-hidraw` for zero-overhead in-process USB HID control.

---

## 2. High-Level Architecture Diagram

```text
+===================================================================================+
|                        1. PRESENTATION LAYER (GTK 4 / Python)                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                       MainWindow (src/gui/app.py)                           |  |
|  |                                                                             |  |
|  |  [ Colors & Groups ]    [ Native Effects ]    [ Profile Editor & Manager ]  |  |
|  |  - ColorSwatchBox       - Breathing, Cycle    - Rule syntax editor          |  |
|  |  - Key / Group Picker   - Waves, Fx Color     - Load / Save / Samples       |  |
|  |                                                                             |  |
|  |  [ Trial & Error Mode Bar ]              [ Help & Permission Dialogs ]      |  |
|  |  - Live Staging Switch / Commit / Revert - src/gui/dialogs.py               |  |
|  +-----------------------------------------------------------------------------+  |
+=========================================|=========================================+
                                          |
                                          v (Method Calls)
+===================================================================================+
|                      2. STATE & CONTROLLER LAYER (Python)                         |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                     G810LedBackend (src/gui/backend.py)                     |  |
|  |                                                                             |  |
|  |  * Device Selection State      * Profile Parser (parse_profile)             |  |
|  |  * Trial & Error Buffer        * Profile Serializer (serialize_profile)     |  |
|  +-----------------------------------------------------------------------------+  |
+=========================================|=========================================+
                                          |
                                          v (HAL Primitives)
+===================================================================================+
|                   3. HARDWARE ABSTRACTION LAYER - HAL (Python)                    |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 KeyboardDriver Interface (src/core/driver_base.py)          |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |
|                                         v (Implements interface)
|  +-----------------------------------------------------------------------------+  |
|  |                   G810Driver (src/core/g810_driver.py)                      |  |
|  |  - Loads shared libraries via ctypes                                        |  |
|  |  - Converts Hex / Names -> RGB ints & C struct types                        |  |
|  +-----------------------------------------------------------------------------+  |
+=========================================|=========================================+
                                          |
                                          v (ctypes C ABI Callouts)
+===================================================================================+
|               4. NATIVE C ABI BRIDGE & SHARED LIBRARIES (C / C++)                 |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |       libg810_bridge.so (c_bridge/g810_bridge.cpp - extern "C" ABI)         |  |
|  |  kbd_create | kbd_open | kbd_set_all_keys | kbd_set_key | kbd_list_devices  |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |
|                                         v (Direct C++ Method Invocations)
|  +-----------------------------------------------------------------------------+  |
|  |                  libg810-led.so (Upstream C++ Driver Engine)                |  |
|  |  LedKeyboard::open() | LedKeyboard::setKey() | LedKeyboard::commit()        |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |
|                                         v
|  +-----------------------------------------------------------------------------+  |
|  |                      libhidapi-hidraw.so (Kernel USB HID)                   |  |
|  +-----------------------------------------------------------------------------+  |
+=========================================|=========================================+
                                          |
                                          v (USB HID Raw Reports)
+===================================================================================+
|                               5. PHYSICAL HARDWARE                                |
|                                                                                   |
|       [ Logitech RGB Keyboard (G213, G410, G512, G610, G810, G910, etc.) ]        |
+===================================================================================+
```

---

## 3. Layer Breakdown & Responsibilities

### 3.1 Presentation Layer (`src/gui/`)
- **`app.py`**:
  - `G810LedApplication`: Application lifecycle management (`Gtk.Application`).
  - `MainWindow`: Multi-tab interface organizing:
    - **Colors & Groups**: Full keyboard color, individual key selection, and key groups (logo, multimedia, fkeys, modifiers, arrows, etc.).
    - **Native Effects**: Hardware-calculated animations (breathing, color cycle, waves, horizontal/vertical waves).
    - **Profile Editor**: Rule-based profile authoring, syntax highlighting, load/save, and sample profile browser.
    - **Startup & Boot Hardware**: Configures power-on modes (`wave`, `color`) and systemd/udev boot profile persistence.
  - `ColorSwatchBox`: Hex input, visual RGB chip swatch, system color picker dialog, and quick presets palette.
  - **Trial & Error Live Bar**: Staged trial mode allowing real-time keyboard evaluation before permanent commit.
- **`dialogs.py`**:
  - `HelpDialog`: Integrated offline documentation covering general usage, key identifiers, lighting effects, and sample scripts.
  - `PermissionDialog`: Explains udev rule setup and privilege delegation for USB HID device access without root.
- **`main.py`**:
  - Detects graphical session (X11 / Wayland), initialises GTK 4, instantiates the backend, and starts the event loop.

### 3.2 State & Controller Layer (`src/gui/backend.py`)
- Provides unified operations to the UI layer, abstracting hardware commands into clean Python methods.
- **Trial & Error State Engine**:
  - `start_trial(snapshot)`: Captures the active keyboard lighting state.
  - `revert_trial()`: Re-applies the snapshot if the user cancels.
  - `apply_trial()`: Issues hardware commit (`-c`) once approved.
- **Profile Parser & Serializer**:
  - Parses `.profile` scripts (`a`, `g`, `k`, `r`, `fx`, `c` directives) into typed `ProfileCommand` objects.
  - Formats edited commands back into standardized profile file format.

### 3.3 Hardware Abstraction Layer (`src/core/`)
- **`driver_base.py` (`KeyboardDriver`)**:
  - Defines an abstract base class with common RGB keyboard primitives:
    - `list_devices() -> List[DeviceInfo]`
    - `open_device(device: DeviceInfo) -> bool`
    - `close_device() -> None`
    - `commit() -> bool`
    - `set_all_keys(r, g, b) -> bool`
    - `set_group_keys(group, r, g, b) -> bool`
    - `set_key(key_name, r, g, b) -> bool`
    - `set_region(region, r, g, b) -> bool`
    - `set_startup_mode(mode) -> bool`
    - `set_native_effect(effect, target, period_ms, r, g, b) -> bool`
  - Decouples UI and business logic from any specific keyboard vendor or library.
- **`g810_driver.py` (`G810Driver`)**:
  - Concrete implementation for Logitech keyboards.
  - Loads native shared libraries (`libg810-led.so` and `libg810_bridge.so`) via Python's `ctypes`.
  - Converts high-level arguments (color hex codes, group strings, key names) into binary primitives passed over the C ABI.

### 3.4 Native C ABI Bridge Layer (`c_bridge/`)
- **Why a C Bridge is necessary**:
  - `libg810-led.so` is built in C++ and exposes mangled symbols using C++ STL types (`std::string`, `std::vector`, `std::chrono::duration`).
  - Directly calling C++ mangled member functions from Python `ctypes` is fragile and non-portable across compiler versions.
  - `g810_bridge.cpp` provides an `extern "C"` ABI with flat C functions (`kbd_create`, `kbd_open`, `kbd_set_all_keys`, `kbd_list_devices`, etc.).
  - Built with dynamic runtime path (`-Wl,-rpath,'$ORIGIN/../lib':'$ORIGIN'`) to automatically bind with `libg810-led.so`.

---

## 4. Operational Workflows

### 4.1 Device Discovery & Initialization Flow

```text
  MainWindow               G810LedBackend              G810Driver              libg810_bridge.so           libhidapi
      |                          |                         |                           |                       |
      |-- _refresh_keyboards() ->|                         |                           |                       |
      |                          |-- list_keyboards() ---->|                           |                       |
      |                          |                         |-- list_devices() -------->|                       |
      |                          |                         |                           |-- kbd_list_devices ->|
      |                          |                         |                           |   hid_enumerate() --->|
      |                          |                         |                           |<-- USB device list ---|
      |                          |                         |<-- C_DeviceInfo structs --|                       |
      |                          |<-- List[DeviceInfo] ----| (deduplicated)            |                       |
      |<-- Device list options --|                         |                           |                       |
      | (Populates dropdown)     |                         |                           |                       |
```

### 4.2 In-Process LED Modification Flow

```text
  User              MainWindow             G810LedBackend           G810Driver         libg810_bridge.so      Logitech Keyboard
   |                     |                       |                      |                      |                      |
   |-- Selects 'W' key ->|                       |                      |                      |                      |
   |   and color #00FF00 |                       |                      |                      |                      |
   |                     |-- set_key_color() --->|                      |                      |                      |
   |                     |   ("w", "00ff00")     |-- set_key() -------->|                      |                      |
   |                     |                       |   ("w", 0, 255, 0)   |-- kbd_set_key() ---->|                      |
   |                     |                       |                      |   ("w", 0, 255, 0)   |-- USB HID Report --->|
   |                     |                       |-- commit() --------->|                      |                      |
   |                     |                       |                      |-- kbd_commit() ----->|                      |
   |                     |                       |                      |                      |-- USB Commit ------->|
   |                     |<-- (Success status) --|<-- (Success) --------|<-- (Success) --------|                      |
   |<-- UI status OK ----|                       |                      |                      |<-- LED changes green |
```

### 4.3 Trial & Error (Live Preview) Flow

```text
  User               MainWindow               G810LedBackend            G810Driver             Logitech Keyboard
   |                      |                          |                       |                         |
   |-- Turn ON Trial ---->|                          |                       |                         |
   |                      |-- start_trial() -------->|                       |                         |
   |                      |                          | [Snapshot current]    |                         |
   |                      |                          |                       |                         |
   |-- Tweak colors ----->|                          |                       |                         |
   |                      |-- stage changes -------->|-- update LEDs live -->|-- USB HID Reports ----->|
   |                      |   (no permanent commit)  |                       |   (Hardware responds)   |
   |                      |                          |                       |                         |
   |== CASE A: User clicks "Keep & Commit" ============================================================|
   |-- Click Keep ------->|                          |                       |                         |
   |                      |-- apply_trial() -------->|-- commit() ---------->|-- Commit to device ---->|
   |                      |                          | [Clear snapshot]      |                         |
   |                                                                                                   |
   |== CASE B: User clicks "Revert" ===================================================================|
   |-- Click Revert ----->|                          |                       |                         |
   |                      |-- revert_trial() ------->|-- replay snapshot --->|-- Restore original ---->|
   |                      |                          |-- commit() ---------->|-- Commit restored ----->|
   |                      |                          | [Clear snapshot]      |                         |
```

---

## 5. Repository File Structure

```text
g810-led-gui-app/
├── bin/
│   ├── g810-led-gui             # Shell launcher script
│   └── g810-led                 # Optional fallback driver executable
├── c_bridge/
│   ├── g810_bridge.cpp          # extern "C" ABI bridge
│   ├── Keyboard.h               # C++ LedKeyboard interface definitions
│   ├── Makefile                 # Compiles libg810_bridge.so with RPATH
│   └── libg810_bridge.so        # Compiled local shared bridge
├── lib/
│   ├── libg810-led.so           # Upstream core C++ shared library
│   ├── libg810-led.so.0.4.3     # Versioned library binary
│   └── libg810_bridge.so        # Installed bridge shared object
├── sample_profiles/             # Preset keyboard lighting profiles
│   ├── all_blue
│   ├── all_green
│   ├── all_red
│   ├── fx_breathing_red
│   ├── fx_cycle
│   └── group_keys
├── src/
│   ├── core/
│   │   ├── __init__.py          # Driver exports
│   │   ├── driver_base.py       # Abstract KeyboardDriver & DeviceInfo
│   │   └── g810_driver.py       # ctypes driver communicating with .so
│   └── gui/
│       ├── __init__.py
│       ├── app.py               # Main GTK 4 UI windows and controls
│       ├── backend.py           # Backend state controller & profile parser
│       ├── dialogs.py           # Help, reference, and permission dialogs
│       └── main.py              # Application entry point
├── tests/
│   ├── test_backend.py          # Unit tests for backend & profiles
│   └── test_driver.py           # Unit tests for native driver & bridge
├── AC.md                        # Acceptance Criteria specification
├── ARCHITECTURE.md              # In-repository architecture guide
├── g810-led-gui.desktop         # Linux XDG desktop entry
└── README.md                    # Project readme
```

---

## 6. Key Advantages of the Decoupled Shared Library Architecture

| Metric | Subprocess / Binary Invocation (`g810-led`) | Native Shared Library Bridge (`.so`) |
| :--- | :--- | :--- |
| **Execution Overhead** | High (`fork()`, `execve()`, process startup on every change) | **Zero** (Direct in-process function invocation via C ABI) |
| **Real-time Responsiveness** | Noticeable latency when dragging color sliders | **Instantaneous** (60 FPS fluid hardware updates) |
| **Device State Persistence** | USB device opened and closed on every single command | **Continuous Connection** (Device handle maintained across edits) |
| **External Dependencies** | Requires CLI binary installed in PATH | **Self-Contained** (Uses bundled or system `.so` libraries) |
| **Error Handling** | Parsing unstructured CLI stderr strings | **Direct Status Codes** & typed return values |
| **Extensibility** | Hardcoded to CLI flags of one vendor | **Pluggable Multi-Vendor HAL** via `KeyboardDriver` |
