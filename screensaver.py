import time
import state
import display
import wifi_server

active = False
_last_update = 0.0
_last_scroll  = 0.0
_scroll_offset = 0
_cached_rssi = None

_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_MONTHS   = ["Jan", "Feb", "M\xe4r", "Apr", "Mai", "Jun",
             "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

_TRACK_VISIBLE = 16   # chars visible at scale=2 (≈192 px)
_SCROLL_STEP   = 0.35  # seconds per character scroll


def _time_str():
    t = time.localtime()
    return "{:02d}:{:02d}".format(t.tm_hour, t.tm_min)


def _date_str():
    t = time.localtime()
    return "{}, {}. {} {}".format(
        _WEEKDAYS[t.tm_wday], t.tm_mday, _MONTHS[t.tm_mon - 1], t.tm_year
    )


def _track_str():
    title = state.track_title
    if not title:
        return ""
    if len(title) <= _TRACK_VISIBLE:
        return title
    padded = title + "    "
    offset = _scroll_offset % len(padded)
    doubled = padded + padded
    return doubled[offset : offset + _TRACK_VISIBLE]


def _wifi_str():
    if not wifi_server.active:
        return "WiFi aus"
    ip_addr = wifi_server.ip()
    if wifi_server.mode == "sta":
        if _cached_rssi is not None:
            return "STA  {}dBm".format(_cached_rssi)
        return "STA " + ip_addr
    return "AP " + ip_addr


def _render():
    display.show_screensaver(
        _time_str(), _date_str(), _track_str(),
        state.profile_labels[state.current_profile],
        _wifi_str(),
        _cached_rssi,
    )


def _scan_rssi():
    global _cached_rssi
    if wifi_server.mode != "sta":
        return
    try:
        import wifi as _w
        ssid = state.wifi_ssid
        for net in _w.radio.start_scanning_networks():
            if net.ssid == ssid:
                _cached_rssi = net.rssi
                break
        _w.radio.stop_scanning_networks()
    except Exception:
        pass


def draw():
    global active, _last_update, _last_scroll, _scroll_offset
    active = True
    _scroll_offset = 0
    _last_update = time.monotonic()
    _last_scroll  = time.monotonic()
    _scan_rssi()
    display.set_brightness(20)
    _render()


def update():
    global _last_update, _last_scroll, _scroll_offset
    now = time.monotonic()
    need_redraw = False
    if state.track_title and now - _last_scroll > _SCROLL_STEP:
        _scroll_offset += 1
        _last_scroll = now
        need_redraw = True
    if now - _last_update > 29:
        _last_update = now
        need_redraw = True
    if need_redraw:
        _render()


def dismiss():
    global active
    active = False
    state.last_activity = time.monotonic()
    display.set_brightness(state.brightness)
    display.draw_menu()
