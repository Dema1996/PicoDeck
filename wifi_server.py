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


def _ntp_query(addr):
    import struct
    packet = bytearray(48)
    packet[0] = 0b00100011
    sock = _pool.socket(_pool.AF_INET, _pool.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(packet, addr)
        sock.recv_into(packet, 48)
    finally:
        sock.close()
    return struct.unpack("!I", packet[40:44])[0]


def _http_time_sync():
    import rtc
    _MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
            "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    try:
        sock = _pool.socket(_pool.AF_INET, _pool.SOCK_STREAM)
        sock.settimeout(10)
        addr = _pool.getaddrinfo("clients3.google.com", 80)[0][4]
        sock.connect(addr)
        sock.sendall(b"HEAD / HTTP/1.1\r\nHost: clients3.google.com\r\nConnection: close\r\n\r\n")
        buf = bytearray(512)
        n = sock.recv_into(buf, 512)
        sock.close()
        for line in buf[:n].decode("utf-8", "ignore").split("\r\n"):
            if line.lower().startswith("date:"):
                p = line[6:].strip().split()
                # "Tue, 20 May 2026 14:35:00 GMT"
                day, mon, year = int(p[1]), _MON.get(p[2], 1), int(p[3])
                hms = p[4].split(":")
                hour = (int(hms[0]) + state.tz_offset) % 24
                t = time.struct_time((year, mon, day, hour, int(hms[1]), int(hms[2]), 0, -1, -1))
                rtc.RTC().datetime = t
                state.ntp_synced = True
                print("HTTP time ok {}-{}-{} {}:{}".format(year, mon, day, hour, int(hms[1])))
                return True
    except Exception as e:
        print("HTTP time error:", e)
    return False


def _ntp_sync():
    import rtc
    gw = str(wifi.radio.ipv4_gateway) if wifi.radio.ipv4_gateway else None
    servers = [s for s in [gw, "pool.ntp.org", "time.google.com", "216.239.35.0"] if s]
    for host in servers:
        try:
            addr = _pool.getaddrinfo(host, 123)[0][4]
            ntp_secs = _ntp_query(addr)
            unix_time = ntp_secs - 2208988800 + state.tz_offset * 3600
            t = time.localtime(unix_time)
            print("NTP ok {} {}-{}-{} {}:{}".format(
                host, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min))
            rtc.RTC().datetime = t
            state.ntp_synced = True
            return
        except Exception as e:
            print("NTP {} failed: {}".format(host, e))
    print("NTP: UDP blocked, trying HTTP fallback...")
    _http_time_sync()


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
        print("IP:", wifi.radio.ipv4_address, "GW:", wifi.radio.ipv4_gateway)
        _ntp_sync()
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


def _stream_page(conn):
    import menus as _m

    def w(s):
        conn.sendall(s if isinstance(s, (bytes, bytearray)) else s.encode())

    w(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
      b"Cache-Control: no-store\r\nConnection: close\r\n\r\n"
      b"<!DOCTYPE html><html><head><meta charset=utf-8>"
      b"<meta name=viewport content='width=device-width,initial-scale=1'>"
      b"<title>PicoDeck</title><style>"
      b"body{font-family:sans-serif;max-width:500px;margin:20px auto;padding:0 12px;"
      b"background:#0d1117;color:#c9d1d9}"
      b"h1,h2{color:#79c0ff}h2{font-size:16px;margin-top:20px}"
      b"label{display:block;margin-top:10px;color:#8b949e;font-size:13px}"
      b"select,input{background:#161b22;color:#c9d1d9;border:1px solid #30363d;"
      b"padding:6px;width:100%;margin-top:4px;font-size:15px;box-sizing:border-box}"
      b"button{background:#1f4e8a;color:#fff;border:none;padding:12px;"
      b"cursor:pointer;width:100%;margin-top:16px;font-size:16px;border-radius:4px}"
      b"hr{border-color:#30363d}small{color:#6e7681}"
      b"</style><script src=/js></script></head><body><h1>PicoDeck</h1>")

    wifi_str = "STA ({})".format(ip()) if mode == "sta" else "AP (PicoDeck / picodeck1)"
    w("<small>WiFi: {}</small><hr><form method=POST action=/save>".format(wifi_str))

    buf = "<label>Profil</label><select name=__profile>"
    for p in state.profile_order:
        sel = " selected" if p == state.current_profile else ""
        buf += '<option value="{}"{}>{}</option>'.format(p, sel, state.profile_labels[p])
    buf += "</select><hr><table width=100%>"
    w(buf)

    valid = sorted(_m.get_valid_actions())
    for btn in state.button_order:
        cur = state.button_actions[btn]
        buf = "<tr><td>{}</td><td><select name='{}'>".format(state.button_pins[btn], btn)
        for a in valid:
            sel = " selected" if a == cur else ""
            buf += '<option value="{}"{}>{}</option>'.format(a, sel, _m.format_action_label(a))
        buf += "</select></td></tr>"
        w(buf)

    w(b"</table><hr><h2>Einstellungen</h2>")

    def setting(lbl, name, pairs, cur):
        s = "<label>{}</label><select name={}>".format(lbl, name)
        for v, vl in pairs:
            sel = " selected" if str(cur) == str(v) else ""
            s += '<option value="{}"{}>{}</option>'.format(v, sel, vl)
        w(s + "</select>")

    setting("Bildschirmschoner", "__ss_timeout",
            [(15,"15 Sek"),(30,"30 Sek"),(60,"1 Minute"),(300,"5 Minuten"),(9999,"Aus")],
            state.screensaver_timeout)
    setting("Helligkeit", "__brightness",
            [(10,"10%"),(20,"20%"),(30,"30%"),(40,"40%"),(50,"50%"),
             (60,"60%"),(70,"70%"),(80,"80%"),(90,"90%"),(100,"100%")],
            state.brightness)
    setting("Encoder Modus", "__enc_mode",
            [("navigate","Navigieren"),("volume","Lautstaerke"),
             ("brightness","Helligkeit"),("mac_brightness","Mac Hellgk.")],
            state.encoder_mode)
    setting("Encoder Richtung", "__enc_dir",
            [(0,"Normal"),(1,"Invertiert")], 1 if state.encoder_reversed else 0)
    setting("Encoder Speed", "__enc_speed",
            [(4,"Langsam"),(2,"Normal"),(1,"Schnell")], state.encoder_threshold)
    setting("Hold-Zeit", "__hold_time",
            [(0.5,"0.5 Sek"),(1.0,"1.0 Sek"),(2.0,"2.0 Sek")],
            state.button_assign_hold_time)
    setting("Invertierung", "__inversion",
            [(0,"Normal"),(1,"Invertiert")], 1 if state.display_inverted else 0)
    setting("Men\xfc-Timeout", "__menu_timeout",
            [(0,"Aus"),(15,"15 Sek"),(30,"30 Sek"),(60,"1 Min"),(120,"2 Min")],
            state.menu_timeout)

    w(b"<button type=submit>Speichern</button></form>"
      b"<hr><h2>Display</h2>"
      b"<div style='margin:0 auto;width:204px;background:#0d1117;"
      b"border:1px solid #30363d;border-radius:6px;overflow:hidden'>"
      b"<div style='background:#161b22;padding:5px 8px;display:flex;"
      b"justify-content:space-between;align-items:center'>"
      b"<span id=lt style='color:#79c0ff;font-size:12px;font-family:monospace'></span>"
      b"<span id=li style='color:#6e7681;font-size:10px;font-family:monospace'></span>"
      b"</div><div id=lr></div></div><hr>")

    w("<h2>WiFi Verbindung</h2><form method=POST action=/wifi>"
      "<label>Heimnetz SSID</label>"
      "<input type=text name=ssid value='{}' autocomplete=off>"
      "<label>Passwort (leer = unveraendert)</label>"
      "<input type=password name=pass placeholder='********'>"
      "<button type=submit>Verbinden &amp; speichern</button>"
      "</form></body></html>".format(state.wifi_ssid or ""))


def _parse_body(req):
    if "\r\n\r\n" not in req:
        return ""
    return req.split("\r\n\r\n", 1)[1].strip()


def _handle(conn):
    import gc
    import persistence
    gc.collect()
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

    if method == "GET" and path == "/status":
        import menus as _m, json
        items = _m.get_menu_items(state.current_menu)
        total = len(items)
        start = max(0, min(state.selected_index - 3, total - 7))
        vis = []
        for i in range(min(7, total - start)):
            idx = start + i
            if idx < total:
                vis.append({"label": items[idx]["label"], "sel": idx == state.selected_index})
        enc_s = {"navigate": "NAV", "volume": "VOL",
                 "brightness": str(state.brightness) + "%",
                 "mac_brightness": "MBRT"}.get(state.encoder_mode, "?")
        hdr_info = (state.profile_labels[state.current_profile][:3].upper()
                    + " " + enc_s + " "
                    + str(state.selected_index + 1) + "/" + str(total))
        data = json.dumps({"hdr": _m.get_menu_header(state.current_menu),
                           "info": hdr_info, "items": vis})
        enc = data.encode()
        conn.sendall(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                      "Content-Length: {}\r\nCache-Control: no-store\r\n"
                      "Connection: close\r\n\r\n").format(len(enc)).encode() + enc)

    elif method == "GET" and path == "/js":
        js = (
            "function u(){"
            "fetch('/status').then(function(r){return r.json();})"
            ".then(function(d){"
            "document.getElementById('lt').textContent=d.hdr;"
            "document.getElementById('li').textContent=d.info;"
            "var h='',i,it;"
            "for(i=0;i<d.items.length;i++){"
            "it=d.items[i];"
            "h+='<div style=\"padding:4px 8px;background:'+(it.sel?'#1f4e8a':'transparent')"
            "+';color:'+(it.sel?'#fff':'#8b949e')"
            "+';font-size:12px;font-family:monospace\">'+(it.sel?'&gt; ':'\\u00a0\\u00a0')"
            "+it.label+'<\\/div>';"
            "}"
            "document.getElementById('lr').innerHTML=h;"
            "}).catch(function(){});}"
            "setInterval(u,1000);u();"
        )
        enc = js.encode()
        conn.sendall(("HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n"
                      "Content-Length: {}\r\nCache-Control: no-store\r\n"
                      "Connection: close\r\n\r\n").format(len(enc)).encode() + enc)

    elif method == "GET" and path == "/":
        gc.collect()
        _stream_page(conn)

    elif method == "GET":
        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")

    elif method == "POST" and path == "/save":
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
                elif k == "__ss_timeout":
                    try:
                        state.screensaver_timeout = int(v)
                    except (ValueError, TypeError):
                        pass
                elif k == "__brightness":
                    try:
                        b = int(v)
                        state.brightness = max(10, min(100, b))
                        import display as _d
                        _d.set_brightness(state.brightness)
                    except (ValueError, TypeError):
                        pass
                elif k == "__enc_mode":
                    if v in ("navigate", "volume", "brightness", "mac_brightness"):
                        state.encoder_mode = v
                elif k == "__enc_dir":
                    state.encoder_reversed = (v == "1")
                elif k == "__enc_speed":
                    try:
                        state.encoder_threshold = int(v)
                    except (ValueError, TypeError):
                        pass
                elif k == "__hold_time":
                    try:
                        state.button_assign_hold_time = float(v)
                    except (ValueError, TypeError):
                        pass
                elif k == "__inversion":
                    import display as _d
                    _d.set_inversion(v == "1")
                elif k == "__menu_timeout":
                    try:
                        state.menu_timeout = int(v)
                    except (ValueError, TypeError):
                        pass
            if new_profile and new_profile in state.profile_order:
                state.current_profile = new_profile
            state.button_actions = dict(state.button_profiles[state.current_profile])
            save_err = None
            try:
                persistence.save_button_actions()
                needs_redraw = True
                print("Saved. Profile:", state.current_profile)
            except Exception as e:
                save_err = str(e)
                print("Save error:", e)
        else:
            save_err = None
        if save_err:
            conn.sendall((
                "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                "Connection: close\r\n\r\n"
                "<!DOCTYPE html><html><head><meta charset=utf-8>"
                "<meta name=viewport content='width=device-width,initial-scale=1'>"
                "<meta http-equiv=refresh content='3;url=/'>"
                "<title>PicoDeck</title>"
                "<style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;"
                "padding:0 12px;background:#0d1117;color:#c9d1d9;text-align:center}}"
                "h1{{color:#79c0ff}}</style></head><body>"
                "<h1>PicoDeck</h1>"
                "<p style='color:#f85149;font-size:48px;margin:16px 0'>&#10007;</p>"
                "<p style='font-size:18px'>Fehler: {}</p>"
                "<p><small style='color:#6e7681'>Weiterleitung in 3 Sek...</small></p>"
                "</body></html>"
            ).format(save_err).encode())
        else:
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                b"Connection: close\r\n\r\n"
                b"<!DOCTYPE html><html><head><meta charset=utf-8>"
                b"<meta name=viewport content='width=device-width,initial-scale=1'>"
                b"<meta http-equiv=refresh content='2;url=/'>"
                b"<title>PicoDeck</title>"
                b"<style>body{font-family:sans-serif;max-width:500px;margin:60px auto;"
                b"padding:0 12px;background:#0d1117;color:#c9d1d9;text-align:center}"
                b"h1{color:#79c0ff}</style></head><body>"
                b"<h1>PicoDeck</h1>"
                b"<p style='color:#3fb950;font-size:48px;margin:16px 0'>&#10003;</p>"
                b"<p style='font-size:18px'>Gespeichert!</p>"
                b"<p><small style='color:#6e7681'>Weiterleitung in 2 Sek...</small></p>"
                b"</body></html>"
            )

    elif method == "POST" and path == "/track":
        conn.sendall(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
        body = _parse_body(req)
        if body:
            params = {}
            for pair in body.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = _url_decode(v)
            state.track_title = params.get("title", "").strip()

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
            b"und \xc3\xb6ffne die neue IP-Adresse.</p>"
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
