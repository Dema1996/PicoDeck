import Foundation
import Combine

@MainActor
final class PicoDeckViewModel: ObservableObject {
    let themeOptions = ["dark", "dracula", "matrix", "amber"]
    let idleModeOptions = ["screensaver", "dim"]
    let encoderModeOptions = ["navigate", "volume", "brightness", "mac_brightness"]
    let encoderThresholdOptions = [1, 2, 4]
    let holdTimeOptions: [Double] = [0.5, 1.0, 2.0]
    let rotationOptions = [0, 90, 180, 270]

    @Published var availablePorts: [String] = []
    @Published var selectedPort: String = ""
    @Published var isConnected = false
    @Published var isReconnecting = false
    @Published var connectionText = "Nicht verbunden"
    @Published var lastError = ""
    @Published var status: PicoDeckStatus?
    @Published var rawLog: [PicoDeckLogEntry] = []
    @Published var logFilter = ""
    @Published var hideJSONLogs = false
    @Published var logTextMode = true
    @Published var selectedLogKind: PicoDeckLogEntry.Kind = .all
    @Published var actionFilter = ""
    @Published var buttonSelections: [String: String] = [:]
    @Published var newProfileLabel = ""
    @Published var wifiSSID = ""
    @Published var wifiPassword = ""
    @Published var hostTrackTitle = ""
    @Published var hostVolume = 50.0
    @Published var hostBrightness = 50.0
    @Published var brightness = 100.0
    @Published var dimBrightness = 20.0
    @Published var screensaverTimeout = 9999.0
    @Published var menuTimeout = 30.0
    @Published var selectedTheme = "dark"
    @Published var selectedIdleMode = "screensaver"
    @Published var selectedEncoderMode = "navigate"
    @Published var encoderThreshold = 2
    @Published var buttonAssignHoldTime = 1.0
    @Published var displayRotation = 0
    @Published var encoderReversed = false
    @Published var displayInverted = false
    @Published var isEditingSettings = false
    @Published var isEditingWiFi = false
    @Published var isEditingProfiles = false
    @Published var isEditingMappings = false

    private var serialPort: SerialPort?
    private let decoder = JSONDecoder()
    private var didHydrateSettings = false
    private var didHydrateWiFi = false
    private var hostStateTimer: Timer?
    private var reconnectTask: Task<Void, Never>?
    private var shouldAutoReconnect = false

    var isUserEditing: Bool {
        isEditingSettings || isEditingWiFi || isEditingProfiles || isEditingMappings
    }

    init() {
        refreshPorts()
    }

    func refreshPorts() {
        availablePorts = SerialPort.discoverPorts()
        if selectedPort.isEmpty || !availablePorts.contains(selectedPort) {
            selectedPort = availablePorts.first ?? ""
        }
    }

    func connect() {
        guard !selectedPort.isEmpty else {
            lastError = "Kein serieller Port ausgewählt"
            return
        }
        let preserveAutoReconnect = shouldAutoReconnect || isReconnecting
        reconnectTask?.cancel()
        reconnectTask = nil
        disconnect()
        shouldAutoReconnect = preserveAutoReconnect
        isReconnecting = preserveAutoReconnect
        do {
            let port = try SerialPort(path: selectedPort)
            port.onLine = { [weak self] line in
                Task { @MainActor in
                    self?.handleIncomingLine(line)
                }
            }
            port.onDisconnect = { [weak self] in
                Task { @MainActor in
                    self?.handlePortDisconnect()
                }
            }
            serialPort = port
            isConnected = true
            isReconnecting = false
            shouldAutoReconnect = true
            connectionText = "Verbunden mit \(selectedPort)"
            lastError = ""
            send(["cmd": "ping"])
            requestStatus()
            refreshHostStateFromSystem(send: true)
            startHostStatePolling()
        } catch {
            lastError = error.localizedDescription
            connectionText = preserveAutoReconnect ? "Reconnect fehlgeschlagen" : "Verbindung fehlgeschlagen"
            if preserveAutoReconnect {
                scheduleReconnect()
            }
        }
    }

    func disconnect() {
        reconnectTask?.cancel()
        reconnectTask = nil
        shouldAutoReconnect = false
        let port = serialPort
        serialPort = nil
        port?.onDisconnect = nil
        port?.onLine = nil
        port?.close()
        isConnected = false
        isReconnecting = false
        status = nil
        connectionText = "Nicht verbunden"
        didHydrateSettings = false
        didHydrateWiFi = false
        hostStateTimer?.invalidate()
        hostStateTimer = nil
    }

    func requestStatus() {
        send(["cmd": "status"])
    }

    func sendAction(_ action: String) {
        send(["cmd": "action", "value": action])
    }

    func switchProfile(_ profile: String) {
        send(["cmd": "switch_profile", "profile": profile])
    }

    func rebootDevice() {
        send(["cmd": "reboot"])
    }

    func assignButton(_ button: String) {
        guard let action = buttonSelections[button], !action.isEmpty else {
            lastError = "Button und Action auswählen"
            return
        }
        send(["cmd": "set_button", "button": button, "action": action])
    }

    func assignAllButtons() {
        guard let status else {
            lastError = "Kein Status geladen"
            return
        }
        var mapping: [String: String] = [:]
        for button in status.buttonOrder {
            guard let action = buttonSelections[button], !action.isEmpty else {
                lastError = "Für \(button.uppercased()) fehlt eine Action"
                return
            }
            mapping[button] = action
        }
        send(["cmd": "set_buttons", "mapping": mapping])
        isEditingMappings = false
    }

    func createProfile() {
        let label = newProfileLabel.trimmingCharacters(in: .whitespacesAndNewlines)
        var payload: [String: Any] = ["cmd": "create_profile"]
        if !label.isEmpty {
            payload["label"] = label
        }
        send(payload)
        newProfileLabel = ""
        isEditingProfiles = false
    }

    func deleteCurrentProfile() {
        guard let status else {
            return
        }
        send(["cmd": "delete_profile", "profile": status.profile])
    }

    func saveWiFi() {
        let ssid = wifiSSID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !ssid.isEmpty else {
            lastError = "SSID fehlt"
            return
        }
        send(["cmd": "save_wifi", "ssid": ssid, "password": wifiPassword])
        wifiPassword = ""
        isEditingWiFi = false
    }

    func sendHostState() {
        let now = Date()
        let cal = Calendar.current
        let payload: [String: Any] = [
            "cmd": "host_state",
            "title": hostTrackTitle,
            "volume": Int(hostVolume),
            "mac_brightness": Int(hostBrightness),
            "unix_time": Int(Date().timeIntervalSince1970),
            "year": cal.component(.year, from: now),
            "month": cal.component(.month, from: now),
            "day": cal.component(.day, from: now),
            "hour": cal.component(.hour, from: now),
            "minute": cal.component(.minute, from: now),
            "second": cal.component(.second, from: now),
            "weekday": (cal.component(.weekday, from: now) + 5) % 7,
        ]
        send(payload)
    }

    func refreshHostStateFromSystem(send: Bool = false) {
        if let volume = HostSystemState.outputVolumePercent() {
            hostVolume = Double(volume)
        }
        if let brightness = HostSystemState.displayBrightnessPercent() {
            hostBrightness = Double(brightness)
        }
        if send && isConnected {
            sendHostState()
        }
    }

    func saveSettings() {
        let values: [String: Any] = [
            "brightness": Int(brightness),
            "dim_brightness": Int(dimBrightness),
            "screensaver_timeout": Int(screensaverTimeout),
            "menu_timeout": Int(menuTimeout),
            "theme": selectedTheme,
            "idle_mode": selectedIdleMode,
            "encoder_mode": selectedEncoderMode,
            "encoder_reversed": encoderReversed,
            "encoder_threshold": encoderThreshold,
            "button_assign_hold_time": buttonAssignHoldTime,
            "display_inverted": displayInverted,
            "display_rotation": displayRotation,
        ]
        send(["cmd": "set", "values": values])
        isEditingSettings = false
    }

    private func send(_ payload: [String: Any]) {
        guard let serialPort else {
            lastError = "Kein aktiver Port"
            return
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: payload)
            guard let line = String(data: data, encoding: .utf8) else {
                lastError = "JSON konnte nicht kodiert werden"
                return
            }
            try serialPort.sendLine(line)
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func handleIncomingLine(_ line: String) {
        guard !line.isEmpty else {
            return
        }
        rawLog.append(PicoDeckLogEntry.from(line))
        if rawLog.count > 40 {
            rawLog.removeFirst(rawLog.count - 40)
        }
        guard line.hasPrefix("{"), let data = line.data(using: .utf8) else {
            return
        }
        do {
            let envelope = try decoder.decode(PicoDeckEnvelope.self, from: data)
            if envelope.ok == true {
                lastError = ""
            }
            if let error = envelope.error {
                lastError = error
            }
            if let status = envelope.status {
                self.status = status
                apply(status: status)
            }
        } catch {
            lastError = "Antwort konnte nicht gelesen werden"
        }
    }

    private func apply(status: PicoDeckStatus) {
        if !isEditingMappings {
            buttonSelections = status.buttonActions
        }
        if !didHydrateWiFi || !isEditingWiFi {
            wifiSSID = status.wifiSSID
            didHydrateWiFi = true
        }
        hostTrackTitle = status.trackTitle
        hostVolume = Double(status.localVolume)
        hostBrightness = Double(status.localMacBrightness)
        if !didHydrateSettings || !isEditingSettings {
            brightness = Double(status.brightness)
            dimBrightness = Double(status.dimBrightness)
            screensaverTimeout = Double(status.screensaverTimeout)
            menuTimeout = Double(status.menuTimeout)
            selectedTheme = status.theme
            selectedIdleMode = status.idleMode
            selectedEncoderMode = status.encoderMode
            encoderThreshold = status.encoderThreshold
            buttonAssignHoldTime = status.buttonAssignHoldTime
            displayRotation = status.displayRotation
            encoderReversed = status.encoderReversed
            displayInverted = status.displayInverted
            didHydrateSettings = true
        }
    }

    private func startHostStatePolling() {
        hostStateTimer?.invalidate()
        hostStateTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.isConnected else { return }
                self.refreshHostStateFromSystem(send: true)
            }
        }
    }

    private func handlePortDisconnect() {
        guard serialPort != nil || isConnected else { return }
        if isConnected {
            lastError = "Serielle Verbindung getrennt"
        }
        let port = serialPort
        serialPort = nil
        port?.onDisconnect = nil
        port?.onLine = nil
        port?.close()
        isConnected = false
        status = nil
        connectionText = "Verbindung verloren"
        didHydrateSettings = false
        didHydrateWiFi = false
        hostStateTimer?.invalidate()
        hostStateTimer = nil
        scheduleReconnect()
    }

    private func scheduleReconnect() {
        guard shouldAutoReconnect, !selectedPort.isEmpty else { return }
        reconnectTask?.cancel()
        isReconnecting = true
        connectionText = "Verbinde neu mit \(selectedPort)..."
        reconnectTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled && self.shouldAutoReconnect && !self.isConnected {
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                if Task.isCancelled || !self.shouldAutoReconnect || self.isConnected {
                    return
                }
                self.refreshPorts()
                guard self.availablePorts.contains(self.selectedPort) else {
                    continue
                }
                self.connect()
            }
        }
    }
}
