/*
  g810-led C Bridge
  Provides an extern "C" ABI to libg810-led for Python / ctypes bindings.
*/

#include <iostream>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>
#include <chrono>

#if __has_include(<g810-led/Keyboard.h>)
    #include <g810-led/Keyboard.h>
#else
    #include "Keyboard.h"
#endif

extern "C" {

typedef struct {
    char manufacturer[64];
    char product[128];
    char vendor_id[8];
    char product_id[8];
    char serial_number[128];
} C_DeviceInfo;

void* kbd_create() {
    return new (std::nothrow) LedKeyboard();
}

void kbd_destroy(void* handle) {
    if (handle) {
        delete static_cast<LedKeyboard*>(handle);
    }
}

int kbd_is_open(void* handle) {
    if (!handle) return 0;
    return static_cast<LedKeyboard*>(handle)->isOpen() ? 1 : 0;
}

int kbd_open(void* handle, uint16_t vid, uint16_t pid, const char* serial) {
    if (!handle) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    if (vid == 0 && pid == 0) {
        return kbd->open() ? 1 : 0;
    }
    return kbd->open(vid, pid, serial ? std::string(serial) : "") ? 1 : 0;
}

void kbd_close(void* handle) {
    if (!handle) return;
    static_cast<LedKeyboard*>(handle)->close();
}

int kbd_commit(void* handle) {
    if (!handle) return 0;
    return static_cast<LedKeyboard*>(handle)->commit() ? 1 : 0;
}

int kbd_set_all_keys(void* handle, uint8_t r, uint8_t g, uint8_t b) {
    if (!handle) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    return kbd->setAllKeys(LedKeyboard::Color{r, g, b}) ? 1 : 0;
}

int kbd_set_region(void* handle, uint8_t region, uint8_t r, uint8_t g, uint8_t b) {
    if (!handle) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    return kbd->setRegion(region, LedKeyboard::Color{r, g, b}) ? 1 : 0;
}

static bool map_group_name(const std::string& name, LedKeyboard::KeyGroup& out_group) {
    std::string s = name;
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    if (s == "logo") out_group = LedKeyboard::KeyGroup::logo;
    else if (s == "indicators") out_group = LedKeyboard::KeyGroup::indicators;
    else if (s == "multimedia") out_group = LedKeyboard::KeyGroup::multimedia;
    else if (s == "gkeys") out_group = LedKeyboard::KeyGroup::gkeys;
    else if (s == "fkeys") out_group = LedKeyboard::KeyGroup::fkeys;
    else if (s == "modifiers") out_group = LedKeyboard::KeyGroup::modifiers;
    else if (s == "functions") out_group = LedKeyboard::KeyGroup::functions;
    else if (s == "arrows") out_group = LedKeyboard::KeyGroup::arrows;
    else if (s == "numeric") out_group = LedKeyboard::KeyGroup::numeric;
    else if (s == "keys") out_group = LedKeyboard::KeyGroup::keys;
    else return false;
    return true;
}

int kbd_set_group_keys(void* handle, const char* group_name, uint8_t r, uint8_t g, uint8_t b) {
    if (!handle || !group_name) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    LedKeyboard::KeyGroup group;
    if (!map_group_name(std::string(group_name), group)) return 0;
    return kbd->setGroupKeys(group, LedKeyboard::Color{r, g, b}) ? 1 : 0;
}

static bool map_key_name(const std::string& key_str, LedKeyboard::Key& out_key) {
    std::string s = key_str;
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);

    // Special & Indicators
    if (s == "logo") out_key = LedKeyboard::Key::logo;
    else if (s == "logo2") out_key = LedKeyboard::Key::logo2;
    else if (s == "backlight" || s == "light") out_key = LedKeyboard::Key::backlight;
    else if (s == "game") out_key = LedKeyboard::Key::game;
    else if (s == "caps") out_key = LedKeyboard::Key::caps;
    else if (s == "scroll") out_key = LedKeyboard::Key::scroll;
    else if (s == "num") out_key = LedKeyboard::Key::num;

    // Multimedia
    else if (s == "next") out_key = LedKeyboard::Key::next;
    else if (s == "prev" || s == "previous") out_key = LedKeyboard::Key::prev;
    else if (s == "stop") out_key = LedKeyboard::Key::stop;
    else if (s == "play" || s == "play_pause") out_key = LedKeyboard::Key::play;
    else if (s == "mute") out_key = LedKeyboard::Key::mute;

    // Control & Whitespace
    else if (s == "space") out_key = LedKeyboard::Key::space;
    else if (s == "enter") out_key = LedKeyboard::Key::enter;
    else if (s == "esc" || s == "escape") out_key = LedKeyboard::Key::esc;
    else if (s == "tab") out_key = LedKeyboard::Key::tab;
    else if (s == "backspace" || s == "back") out_key = LedKeyboard::Key::backspace;
    else if (s == "caps_lock" || s == "capslock") out_key = LedKeyboard::Key::caps_lock;

    // Modifiers
    else if (s == "ctrl_left" || s == "ctrlleft" || s == "ctrll") out_key = LedKeyboard::Key::ctrl_left;
    else if (s == "shift_left" || s == "shiftleft" || s == "shiftl") out_key = LedKeyboard::Key::shift_left;
    else if (s == "alt_left" || s == "altleft" || s == "altl") out_key = LedKeyboard::Key::alt_left;
    else if (s == "win_left" || s == "winleft" || s == "winl" || s == "meta_left" || s == "metaleft") out_key = LedKeyboard::Key::win_left;
    else if (s == "ctrl_right" || s == "ctrlright" || s == "ctrlr") out_key = LedKeyboard::Key::ctrl_right;
    else if (s == "shift_right" || s == "shiftright" || s == "shiftr") out_key = LedKeyboard::Key::shift_right;
    else if (s == "alt_right" || s == "altright" || s == "altr" || s == "altgr") out_key = LedKeyboard::Key::alt_right;
    else if (s == "win_right" || s == "winright" || s == "winr" || s == "meta_right" || s == "metaright") out_key = LedKeyboard::Key::win_right;
    else if (s == "menu") out_key = LedKeyboard::Key::menu;

    // Navigation & Editing
    else if (s == "arrow_left" || s == "arrowleft" || s == "left") out_key = LedKeyboard::Key::arrow_left;
    else if (s == "arrow_right" || s == "arrowright" || s == "right") out_key = LedKeyboard::Key::arrow_right;
    else if (s == "arrow_top" || s == "arrowtop" || s == "top" || s == "arrow_up" || s == "up") out_key = LedKeyboard::Key::arrow_top;
    else if (s == "arrow_bottom" || s == "arrowbottom" || s == "bottom" || s == "arrow_down" || s == "down") out_key = LedKeyboard::Key::arrow_bottom;
    else if (s == "insert" || s == "ins") out_key = LedKeyboard::Key::insert;
    else if (s == "delete" || s == "del") out_key = LedKeyboard::Key::del;
    else if (s == "home") out_key = LedKeyboard::Key::home;
    else if (s == "end") out_key = LedKeyboard::Key::end;
    else if (s == "page_up" || s == "pageup") out_key = LedKeyboard::Key::page_up;
    else if (s == "page_down" || s == "pagedown") out_key = LedKeyboard::Key::page_down;
    else if (s == "print_screen" || s == "printscreen" || s == "printscr" || s == "print") out_key = LedKeyboard::Key::print_screen;
    else if (s == "scroll_lock" || s == "scrolllock") out_key = LedKeyboard::Key::scroll_lock;
    else if (s == "pause_break" || s == "pausebreak" || s == "pause" || s == "break") out_key = LedKeyboard::Key::pause_break;

    // Punctuation & Symbols
    else if (s == "tilde" || s == "~") out_key = LedKeyboard::Key::tilde;
    else if (s == "minus" || s == "-") out_key = LedKeyboard::Key::minus;
    else if (s == "equal" || s == "=") out_key = LedKeyboard::Key::equal;
    else if (s == "open_bracket" || s == "[") out_key = LedKeyboard::Key::open_bracket;
    else if (s == "close_bracket" || s == "]") out_key = LedKeyboard::Key::close_bracket;
    else if (s == "backslash" || s == "\\") out_key = LedKeyboard::Key::backslash;
    else if (s == "semicolon" || s == ";") out_key = LedKeyboard::Key::semicolon;
    else if (s == "quote" || s == "\"") out_key = LedKeyboard::Key::quote;
    else if (s == "dollar" || s == "$") out_key = LedKeyboard::Key::dollar;
    else if (s == "comma" || s == ",") out_key = LedKeyboard::Key::comma;
    else if (s == "period" || s == ".") out_key = LedKeyboard::Key::period;
    else if (s == "slash" || s == "/") out_key = LedKeyboard::Key::slash;
    else if (s == "intl_backslash" || s == "<") out_key = LedKeyboard::Key::intl_backslash;
    else if (s == "abnt_slash" || s == "abnt_c1") out_key = LedKeyboard::Key::abnt_slash;

    // Keypad (NumPad)
    else if (s == "num_lock" || s == "numlock") out_key = LedKeyboard::Key::num_lock;
    else if (s == "num/" || s == "num_slash" || s == "numslash") out_key = LedKeyboard::Key::num_slash;
    else if (s == "num*" || s == "num_asterisk" || s == "numasterisk") out_key = LedKeyboard::Key::num_asterisk;
    else if (s == "num-" || s == "num_minus" || s == "numminus") out_key = LedKeyboard::Key::num_minus;
    else if (s == "num+" || s == "num_plus" || s == "numplus") out_key = LedKeyboard::Key::num_plus;
    else if (s == "numenter" || s == "num_enter") out_key = LedKeyboard::Key::num_enter;
    else if (s == "num." || s == "num_period" || s == "numperiod" || s == "num_dot" || s == "numdot") out_key = LedKeyboard::Key::num_dot;
    else if (s == "num0" || s == "num_0") out_key = LedKeyboard::Key::num_0;
    else if (s == "num1" || s == "num_1") out_key = LedKeyboard::Key::num_1;
    else if (s == "num2" || s == "num_2") out_key = LedKeyboard::Key::num_2;
    else if (s == "num3" || s == "num_3") out_key = LedKeyboard::Key::num_3;
    else if (s == "num4" || s == "num_4") out_key = LedKeyboard::Key::num_4;
    else if (s == "num5" || s == "num_5") out_key = LedKeyboard::Key::num_5;
    else if (s == "num6" || s == "num_6") out_key = LedKeyboard::Key::num_6;
    else if (s == "num7" || s == "num_7") out_key = LedKeyboard::Key::num_7;
    else if (s == "num8" || s == "num_8") out_key = LedKeyboard::Key::num_8;
    else if (s == "num9" || s == "num_9") out_key = LedKeyboard::Key::num_9;

    // G-Keys
    else if (s == "g1") out_key = LedKeyboard::Key::g1;
    else if (s == "g2") out_key = LedKeyboard::Key::g2;
    else if (s == "g3") out_key = LedKeyboard::Key::g3;
    else if (s == "g4") out_key = LedKeyboard::Key::g4;
    else if (s == "g5") out_key = LedKeyboard::Key::g5;
    else if (s == "g6") out_key = LedKeyboard::Key::g6;
    else if (s == "g7") out_key = LedKeyboard::Key::g7;
    else if (s == "g8") out_key = LedKeyboard::Key::g8;
    else if (s == "g9") out_key = LedKeyboard::Key::g9;

    // Single Characters: letters
    else if (s.size() == 1 && s[0] >= 'a' && s[0] <= 'z') {
        out_key = static_cast<LedKeyboard::Key>(static_cast<uint16_t>(LedKeyboard::Key::a) + (s[0] - 'a'));
    }
    // Single Characters: numbers
    else if (s.size() == 1 && s[0] >= '0' && s[0] <= '9') {
        if (s[0] == '0') out_key = LedKeyboard::Key::n0;
        else out_key = static_cast<LedKeyboard::Key>(static_cast<uint16_t>(LedKeyboard::Key::n1) + (s[0] - '1'));
    }
    // Function Keys: F1 to F12
    else if (s.size() >= 2 && s[0] == 'f' && isdigit(s[1])) {
        int fnum = std::stoi(s.substr(1));
        if (fnum >= 1 && fnum <= 12) {
            out_key = static_cast<LedKeyboard::Key>(static_cast<uint16_t>(LedKeyboard::Key::f1) + (fnum - 1));
        } else return false;
    }
    else return false;

    return true;
}

int kbd_set_key(void* handle, const char* key_name, uint8_t r, uint8_t g, uint8_t b) {
    if (!handle || !key_name) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    LedKeyboard::Key key;
    if (!map_key_name(std::string(key_name), key)) return 0;
    return kbd->setKey(LedKeyboard::KeyValue{key, LedKeyboard::Color{r, g, b}}) ? 1 : 0;
}

int kbd_set_startup_mode(void* handle, const char* mode_name) {
    if (!handle || !mode_name) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    std::string s = mode_name;
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    LedKeyboard::StartupMode mode;
    if (s == "wave") mode = LedKeyboard::StartupMode::wave;
    else if (s == "color") mode = LedKeyboard::StartupMode::color;
    else return 0;
    return kbd->setStartupMode(mode) ? 1 : 0;
}

int kbd_set_native_effect(void* handle, const char* effect_name, const char* target_name, uint16_t period_ms, uint8_t r, uint8_t g, uint8_t b) {
    if (!handle || !effect_name || !target_name) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);

    std::string eff = effect_name;
    std::transform(eff.begin(), eff.end(), eff.begin(), ::tolower);
    LedKeyboard::NativeEffect effect;
    if (eff == "color") effect = LedKeyboard::NativeEffect::color;
    else if (eff == "breathing") effect = LedKeyboard::NativeEffect::breathing;
    else if (eff == "cycle") effect = LedKeyboard::NativeEffect::cycle;
    else if (eff == "waves") effect = LedKeyboard::NativeEffect::waves;
    else if (eff == "hwave") effect = LedKeyboard::NativeEffect::hwave;
    else if (eff == "vwave") effect = LedKeyboard::NativeEffect::vwave;
    else if (eff == "cwave") effect = LedKeyboard::NativeEffect::cwave;
    else return 0;

    std::string tgt = target_name;
    std::transform(tgt.begin(), tgt.end(), tgt.begin(), ::tolower);
    LedKeyboard::NativeEffectPart part;
    if (tgt == "all") part = LedKeyboard::NativeEffectPart::all;
    else if (tgt == "keys") part = LedKeyboard::NativeEffectPart::keys;
    else if (tgt == "logo") part = LedKeyboard::NativeEffectPart::logo;
    else return 0;

    std::chrono::duration<uint16_t, std::milli> period(period_ms);
    return kbd->setNativeEffect(effect, part, period, LedKeyboard::Color{r, g, b}, LedKeyboard::NativeEffectStorage::none) ? 1 : 0;
}

int kbd_list_devices(void* handle, C_DeviceInfo* out_devices, int max_count) {
    if (!handle || !out_devices || max_count <= 0) return 0;
    auto* kbd = static_cast<LedKeyboard*>(handle);
    auto list = kbd->listKeyboards();
    int count = std::min((int)list.size(), max_count);
    for (int i = 0; i < count; ++i) {
        std::strncpy(out_devices[i].manufacturer, list[i].manufacturer.c_str(), 63);
        out_devices[i].manufacturer[63] = '\0';
        std::strncpy(out_devices[i].product, list[i].product.c_str(), 127);
        out_devices[i].product[127] = '\0';
        snprintf(out_devices[i].vendor_id, 8, "%04x", list[i].vendorID);
        snprintf(out_devices[i].product_id, 8, "%04x", list[i].productID);
        std::strncpy(out_devices[i].serial_number, list[i].serialNumber.c_str(), 127);
        out_devices[i].serial_number[127] = '\0';
    }
    return count;
}

}
