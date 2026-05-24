import wifi, time, microcontroller, json

print("--- WiFi Diagnose ---")
try:
    raw = bytes(microcontroller.nvm[:2048]).split(b"\x00", 1)[0]
    cfg = json.loads(raw.decode())
    ssid = cfg.get("wifi_ssid", "")
    pw = cfg.get("wifi_password", "")
    print("SSID:", repr(ssid))
    print("Pass:", repr(pw))
except Exception as e:
    print("NVM fehler:", e)
    ssid = pw = ""

if not ssid:
    print("Keine Credentials in NVM.")
else:
    print("Stoppe AP + trenne STA...")
    try: wifi.radio.stop_ap()
    except Exception as e: print("stop_ap:", e)
    try: wifi.radio.disconnect()
    except Exception as e: print("disconnect:", e)
    time.sleep(2)

    print("Verbinde (ohne radio-reset)...")
    try:
        wifi.radio.connect(ssid, pw)
        deadline = time.monotonic() + 20
        while not wifi.radio.connected:
            if time.monotonic() > deadline:
                print("Timeout!")
                break
            time.sleep(0.5)
        if wifi.radio.connected:
            print("OK! IP:", wifi.radio.ipv4_address)
        else:
            print("Fehlgeschlagen ohne reset, versuche mit reset...")
            wifi.radio.enabled = False
            time.sleep(2)
            wifi.radio.enabled = True
            time.sleep(3)
            wifi.radio.connect(ssid, pw)
            deadline = time.monotonic() + 20
            while not wifi.radio.connected:
                if time.monotonic() > deadline:
                    print("Timeout 2!")
                    break
                time.sleep(0.5)
            if wifi.radio.connected:
                print("OK mit reset! IP:", wifi.radio.ipv4_address)
            else:
                print("Beide Versuche fehlgeschlagen.")
    except Exception as e:
        print("Fehler:", e)
