import wifi
import socketpool
import time
import state

SSID = "PicoDeck"
_AP_PASSWORD = "picodeck1"
_PORT = 80

_pool = None
_server = None
active = False
mode = "none"   # "ap" or "sta"
needs_redraw = False
needs_reboot = False


def _url_decode(s):
    s = s.replace("+", " ")
    out = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                out.append(chr(int(s[i+1:i+3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(s[i])
        i += 1
    return "".join(out)


def _start_server():
    global _pool, _server
    _pool = socketpool.SocketPool(wifi.radio)
    _server = _pool.socket(_pool.AF_INET, _pool.SOCK_STREAM)
    _server.setsockopt(_pool.SOL_SOCKET, _pool.SO_REUSEADDR, 1)
    _server.bind(("0.0.0.0", _PORT))
    _server.listen(1)
    _server.setblocking(False)


def start_ap():
    global active, mode
    try:
        wifi.radio.start_ap(ssid=SSID, password=_AP_PASSWORD)
        _start_server()
        active = True
        mode = "ap"
        return True
    except Exception as e:
        print("AP start:", e)
        active = False
        return False


def start_sta(ssid, password):
    global active, mode
    try:
        wifi.radio.connect(ssid, password)
        deadline = time.monotonic() + 12
        while not wifi.radio.connected:
            if time.monotonic() > deadline:
                raise RuntimeError("timeout")
            time.sleep(0.2)
        _start_server()
        active = True
        mode = "sta"
        return True
    except Exception as e:
        print("STA start:", e)
        active = False
        return False


def start():
    """Try STA if credentials saved, else start AP."""
    if state.wifi_ssid:
        if start_sta(state.wifi_ssid, state.wifi_password):
            return True
        print("STA failed, falling back to AP")
    return start_ap()


def stop():
    global _server, active, mode
    try:
        if _server:
            _server.close()
            _server = None
        if mode == "ap":
            wifi.radio.stop_ap()
        else:
            wifi.radio.disconnect()
    except Exception:
        pass
    active = False
    mode = "none"


def ip():
    try:
        if mode == "sta":
            return str(wifi.radio.ipv4_address)
        return str(wifi.radio.ipv4_address_ap)
    except Exception:
        return "?"


def _build_page():
    import menus
    valid = sorted(menus.get_valid_actions())
    rows = []
    for btn in state.button_order:
        cur = state.button_actions[btn]
        pin = state.button_pins[btn]
        opts = "".join(
            '<option value="{}"{}>{}</option>'.format(
                a, " selected" if a == cur else "", menus.format_action_label(a)
            )
            for a in valid
        )
        rows.append("<tr><td>{}</td><td><select name='{}'>{}</select></td></tr>".format(pin, btn, opts))

    profile_opts = "".join(
        '<option value="{}"{}>{}</option>'.format(
            p, " selected" if p == state.current_profile else "", state.profile_labels[p]
        )
        for p in state.profile_order
    )

    wifi_mode_str = "STA ({})".format(ip()) if mode == "sta" else "AP (PicoDeck / picodeck1)"
    ssid_val = state.wifi_ssid or ""

    return (
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>PicoDeck</title><style>"
        "body{{font-family:sans-serif;max-width:500px;margin:20px auto;padding:0 12px;"
        "background:#0d1117;color:#c9d1d9}}"
        "h1,h2{{color:#79c0ff}}"
        "h2{{font-size:16px;margin-top:20px}}"
        "label{{display:block;margin-top:10px;color:#8b949e;font-size:13px}}"
        "select,input{{background:#161b22;color:#c9d1d9;border:1px solid #30363d;"
        "padding:6px;width:100%;margin-top:4px;font-size:15px;box-sizing:border-box}}"
        "button{{background:#1f4e8a;color:#fff;border:none;padding:12px;"
        "cursor:pointer;width:100%;margin-top:16px;font-size:16px;border-radius:4px}}"
        "hr{{border-color:#30363d}}"
        "small{{color:#6e7681}}"
        "</style></head><body>"
        "<h1>PicoDeck</h1>"
        "<small>WiFi: {}</small><hr>"
        "<form method=POST action=/save>"
        "<label>Profil</label><select name=__profile>{}</select>"
        "<hr>{}"
        "<button type=submit>Speichern</button>"
        "</form><hr>"
        "<h2>WiFi Verbindung</h2>"
        "<form method=POST action=/wifi>"
        "<label>Heimnetz SSID</label>"
        "<input type=text name=ssid value='{}' autocomplete=off>"
        "<label>Passwort (leer = unveraendert)</label>"
        "<input type=password name=pass placeholder='********'>"
        "<button type=submit>Verbinden &amp; speichern</button>"
        "</form></body></html>"
    ).format(wifi_mode_str, profile_opts, "".join(rows), ssid_val)


def _parse_body(req):
    if "\r\n\r\n" not in req:
        return ""
    return req.split("\r\n\r\n", 1)[1].strip()


def _handle(conn):
    import persistence
    buf = bytearray(2048)
    try:
        n = conn.recv_into(buf, 2048)
    except OSError:
        return
    req = buf[:n].decode("utf-8", "ignore")
    if not req:
        return

    # Read remaining body if Content-Length says there's more
    if "\r\n\r\n" in req:
        content_length = 0
        for line in req.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                break
        header_end = req.index("\r\n\r\n") + 4
        body_received = len(req) - header_end
        while body_received < content_length:
            chunk = bytearray(256)
            try:
                cn = conn.recv_into(chunk, 256)
                if cn == 0:
                    break
                req += chunk[:cn].decode("utf-8", "ignore")
                body_received += cn
            except OSError:
                break

    first = req.split("\r\n", 1)[0].split()
    if len(first) < 2:
        return
    method, path = first[0], first[1]

    if method == "GET":
        page = _build_page()
        enc = page.encode()
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        ).format(len(enc)).encode()
        conn.sendall(header + enc)

    elif method == "POST" and path == "/save":
        conn.sendall(b"HTTP/1.1 303 See Other\r\nLocation: /\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        global needs_redraw
        body = _parse_body(req)
        if body:
            source_profile = state.current_profile
            new_profile = None
            for pair in body.split("&"):
                if "=" not in pair:
                    continue
                k, v = pair.split("=", 1)
                v = _url_decode(v)
                if k == "__profile":
                    new_profile = v
                elif k in state.button_order:
                    state.button_profiles[source_profile][k] = v
            if new_profile and new_profile in state.profile_order:
                state.current_profile = new_profile
            state.button_actions = dict(state.button_profiles[state.current_profile])
            persistence.save_button_actions()
            needs_redraw = True
            print("Saved. Profile:", state.current_profile)

    elif method == "POST" and path == "/wifi":
        reboot_page = (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
            b"<!DOCTYPE html><html><head><meta charset=utf-8>"
            b"<meta name=viewport content='width=device-width,initial-scale=1'>"
            b"<title>PicoDeck</title></head>"
            b"<body style='background:#0d1117;color:#c9d1d9;font-family:sans-serif;"
            b"max-width:500px;margin:40px auto;padding:0 12px;text-align:center'>"
            b"<h1 style='color:#79c0ff'>PicoDeck</h1>"
            b"<p>WiFi-Daten gespeichert. Pico startet neu...</p>"
            b"<p style='color:#6e7681'>Verbinde dich danach mit deinem Heimnetz<br>"
            b"und oeffne die neue IP-Adresse.</p>"
            b"</body></html>"
        )
        conn.sendall(reboot_page)
        body = _parse_body(req)
        if body:
            global needs_reboot
            params = {}
            for pair in body.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = _url_decode(v)
            ssid = params.get("ssid", "").strip()
            password = params.get("pass", "").strip()
            if ssid:
                needs_reboot = True
                try:
                    persistence.save_wifi_config(ssid, password)
                except Exception as e:
                    print("wifi save error:", e)


def poll():
    if not active or _server is None:
        return
    try:
        conn, _ = _server.accept()
        conn.setblocking(True)
        try:
            _handle(conn)
        finally:
            conn.close()
    except OSError:
        pass
    except Exception as e:
        print("poll error:", e)
