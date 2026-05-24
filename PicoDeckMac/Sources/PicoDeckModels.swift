import Foundation

struct PicoDeckEnvelope: Decodable {
    let type: String
    let ok: Bool?
    let error: String?
    let status: PicoDeckStatus?
    let actions: [String]?
}

struct PicoDeckStatus: Decodable {
    let currentMenu: String
    let menuStack: [String]
    let selectedIndex: Int
    let profile: String
    let profileLabel: String
    let profiles: [String]
    let profileLabels: [String: String]
    let buttonActions: [String: String]
    let buttonOrder: [String]
    let brightness: Int
    let dimBrightness: Int
    let idleMode: String
    let screensaverTimeout: Int
    let menuTimeout: Int
    let theme: String
    let encoderMode: String
    let encoderReversed: Bool
    let encoderThreshold: Int
    let buttonAssignHoldTime: Double
    let displayInverted: Bool
    let displayRotation: Int
    let trackTitle: String
    let localVolume: Int
    let localMacBrightness: Int
    let wifiActive: Bool
    let wifiMode: String
    let wifiIP: String
    let wifiSSID: String
    let timeSyncSource: String
    let bleAvailable: Bool
    let bleActive: Bool
    let bleConnected: Bool
    let bleStatus: String
    let lastException: String
    let lastExceptionLog: [String]
    let screensaverActive: Bool
    let screensaverDimmed: Bool
    let menuItems: [PicoDeckMenuItem]
    let actions: [String]

    enum CodingKeys: String, CodingKey {
        case currentMenu = "current_menu"
        case menuStack = "menu_stack"
        case selectedIndex = "selected_index"
        case profile
        case profileLabel = "profile_label"
        case profiles
        case profileLabels = "profile_labels"
        case buttonActions = "button_actions"
        case buttonOrder = "button_order"
        case brightness
        case dimBrightness = "dim_brightness"
        case idleMode = "idle_mode"
        case screensaverTimeout = "screensaver_timeout"
        case menuTimeout = "menu_timeout"
        case theme
        case encoderMode = "encoder_mode"
        case encoderReversed = "encoder_reversed"
        case encoderThreshold = "encoder_threshold"
        case buttonAssignHoldTime = "button_assign_hold_time"
        case displayInverted = "display_inverted"
        case displayRotation = "display_rotation"
        case trackTitle = "track_title"
        case localVolume = "local_volume"
        case localMacBrightness = "local_mac_brightness"
        case wifiActive = "wifi_active"
        case wifiMode = "wifi_mode"
        case wifiIP = "wifi_ip"
        case wifiSSID = "wifi_ssid"
        case timeSyncSource = "time_sync_source"
        case bleAvailable = "ble_available"
        case bleActive = "ble_active"
        case bleConnected = "ble_connected"
        case bleStatus = "ble_status"
        case lastException = "last_exception"
        case lastExceptionLog = "last_exception_log"
        case screensaverActive = "screensaver_active"
        case screensaverDimmed = "screensaver_dimmed"
        case menuItems = "menu_items"
        case actions
    }
}

struct PicoDeckLogEntry: Identifiable {
    enum Kind: String, CaseIterable {
        case all
        case error
        case firmware
        case json
        case ack
        case status
    }

    let id = UUID()
    let line: String
    let kind: Kind
    let envelopeType: String?

    var isJSON: Bool { envelopeType != nil }

    static func from(_ line: String) -> PicoDeckLogEntry {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("{"), let data = trimmed.data(using: .utf8) else {
            let lowered = trimmed.lowercased()
            if lowered.contains("error") || lowered.contains("failed") || lowered.contains("traceback") {
                return PicoDeckLogEntry(line: line, kind: .error, envelopeType: nil)
            }
            return PicoDeckLogEntry(line: line, kind: .firmware, envelopeType: nil)
        }

        if let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let type = object["type"] as? String {
            if type == "error" || object["ok"] as? Bool == false || object["error"] != nil {
                return PicoDeckLogEntry(line: line, kind: .error, envelopeType: type)
            }
            if type == "ack" || type == "pong" {
                return PicoDeckLogEntry(line: line, kind: .ack, envelopeType: type)
            }
            if type == "status" {
                return PicoDeckLogEntry(line: line, kind: .status, envelopeType: type)
            }
            return PicoDeckLogEntry(line: line, kind: .json, envelopeType: type)
        }

        return PicoDeckLogEntry(line: line, kind: .json, envelopeType: nil)
    }
}

struct PicoDeckMenuItem: Decodable, Identifiable {
    let index: Int
    let label: String
    let selected: Bool

    var id: Int { index }
}

struct PicoDeckActionGroup: Identifiable {
    let title: String
    let items: [PicoDeckActionOption]

    var id: String { title }
}

struct PicoDeckActionOption: Identifiable, Hashable {
    let value: String
    let label: String
    let category: String

    var id: String { value }

    static func buildGroups(from actions: [String], filter: String) -> [PicoDeckActionGroup] {
        let needle = filter.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let options = actions
            .map(Self.from)
            .filter { option in
                guard !needle.isEmpty else { return true }
                return option.label.lowercased().contains(needle) || option.value.lowercased().contains(needle)
            }
            .sorted {
                if $0.category == $1.category {
                    return $0.label.localizedCaseInsensitiveCompare($1.label) == .orderedAscending
                }
                return $0.category.localizedCaseInsensitiveCompare($1.category) == .orderedAscending
            }

        var grouped: [String: [PicoDeckActionOption]] = [:]
        for option in options {
            grouped[option.category, default: []].append(option)
        }

        return grouped.keys.sorted().map { key in
            PicoDeckActionGroup(title: key, items: grouped[key] ?? [])
        }
    }

    static func from(_ value: String) -> PicoDeckActionOption {
        PicoDeckActionOption(
            value: value,
            label: friendlyLabel(for: value),
            category: category(for: value)
        )
    }

    private static func category(for value: String) -> String {
        if value.hasPrefix("text:") { return "Text" }
        if value.hasPrefix("profile:") { return "Profile" }
        if value.hasPrefix("nav_") || value == "back" { return "Navigation" }
        if value.contains("wifi") || value.contains("bt_") { return "Verbindungen" }
        if value.contains("track") || value.contains("volume") || value.contains("mute") || value.contains("play") {
            return "Medien"
        }
        if value.contains("brightness") || value.contains("theme") || value.contains("encoder") || value.contains("hold_time") {
            return "Geraet"
        }
        if value.hasPrefix("vscode_") || value == "open_vscode" || value == "command_palette" || value == "toggle_terminal" || value == "format_document" || value == "new_terminal" || value == "open_whisper" {
            return "Coding"
        }
        if value == "spotlight" || value == "lock_mac" || value == "screenshot" || value == "mission_control" || value == "show_desktop" || value == "app_switcher" || value == "previous_app" || value == "close_window" || value == "full_screen" || value == "minimize" || value == "hide_window" || value == "emoji_picker" {
            return "macOS"
        }
        if value == "undo" || value == "redo" || value == "copy" || value == "cut" || value == "paste" || value == "select_all" || value == "save" || value == "find" || value == "zoom_in" || value == "zoom_out" {
            return "Bearbeiten"
        }
        if value == "new_tab" || value == "close_tab" || value == "prev_tab" || value == "next_tab" || value == "reload" {
            return "Browser"
        }
        return "Sonstiges"
    }

    private static func friendlyLabel(for value: String) -> String {
        if value.hasPrefix("text:") {
            let text = String(value.dropFirst(5))
            return text.isEmpty ? "Text-Makro" : "Text: \(text)"
        }
        if value.hasPrefix("profile:") {
            return "Profil: " + value.split(separator: ":", maxSplits: 1).last.map(String.init).unwrapOr(value)
        }

        let custom: [String: String] = [
            "nav_back": "Navigation Zurueck",
            "nav_up": "Navigation Hoch",
            "nav_down": "Navigation Runter",
            "nav_select": "Navigation OK",
            "spotlight": "Spotlight",
            "lock_mac": "Mac sperren",
            "screenshot": "Screenshot",
            "mission_control": "Mission Control",
            "show_desktop": "Desktop anzeigen",
            "app_switcher": "App-Wechsler",
            "previous_app": "Vorherige App",
            "close_window": "Fenster schliessen",
            "full_screen": "Vollbild",
            "minimize": "Minimieren",
            "hide_window": "Fenster ausblenden",
            "emoji_picker": "Emoji-Picker",
            "command_palette": "Command Palette",
            "toggle_terminal": "Terminal umschalten",
            "format_document": "Dokument formatieren",
            "new_terminal": "Neues Terminal",
            "open_vscode": "VS Code oeffnen",
            "open_whisper": "Whisper oeffnen",
            "play_pause": "Play/Pause",
            "previous_track": "Vorheriger Titel",
            "next_track": "Naechster Titel",
            "volume_up": "Lautstaerke +",
            "volume_down": "Lautstaerke -",
            "mac_brightness_up": "Mac-Helligkeit +",
            "mac_brightness_down": "Mac-Helligkeit -",
            "encoder_navigate": "Encoder Navigation",
            "encoder_volume": "Encoder Lautstaerke",
            "encoder_brightness": "Encoder Helligkeit",
            "encoder_mac_brightness": "Encoder Mac-Helligkeit",
            "toggle_wifi": "WLAN umschalten",
            "wifi_status": "WLAN-Status",
            "wifi_start_ap": "WLAN Access Point",
            "bt_toggle": "Bluetooth umschalten",
            "toggle_encoder_dir": "Encoder-Richtung umschalten",
            "encoder_speed_slow": "Encoder langsam",
            "encoder_speed_normal": "Encoder normal",
            "encoder_speed_fast": "Encoder schnell",
            "hold_time_05": "Hold-Zeit 0.5 s",
            "hold_time_10": "Hold-Zeit 1.0 s",
            "hold_time_20": "Hold-Zeit 2.0 s",
        ]

        if let label = custom[value] {
            return label
        }

        return value
            .split(separator: "_")
            .map { chunk in
                let lower = chunk.lowercased()
                if lower == "mac" { return "Mac" }
                if lower == "vscode" { return "VS Code" }
                return lower.prefix(1).uppercased() + lower.dropFirst()
            }
            .joined(separator: " ")
    }
}

private extension Optional where Wrapped == String {
    func unwrapOr(_ fallback: String) -> String {
        self ?? fallback
    }
}
