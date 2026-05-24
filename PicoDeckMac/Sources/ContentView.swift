import AppKit
import Foundation
import SwiftUI

struct ContentView: View {
    private enum FocusField: Hashable {
        case profileName
        case actionFilter
        case wifiSSID
        case wifiPassword
        case logFilter
    }

    @StateObject private var model = PicoDeckViewModel()
    @FocusState private var focusedField: FocusField?
    @State private var isLogExpanded = false
    @State private var autoFollowLog = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                connectionSection
                statusSection
                HStack(alignment: .top, spacing: 16) {
                    VStack(alignment: .leading, spacing: 16) {
                        controlSection
                        profileSection
                        buttonMappingSection
                    }
                    VStack(alignment: .leading, spacing: 16) {
                        settingsSection
                        hostStateSection
                        wifiSection
                    }
                }
                logSection
            }
            .padding(20)
        }
        .frame(minWidth: 1060, minHeight: 860)
        .onChange(of: focusedField) { field in
            model.isEditingProfiles = field == .profileName
            model.isEditingWiFi = field == .wifiSSID || field == .wifiPassword
            model.isEditingMappings = field == .actionFilter
        }
    }

    private var connectionSection: some View {
        GroupBox("Verbindung") {
            HStack {
                Picker("Port", selection: $model.selectedPort) {
                    ForEach(model.availablePorts, id: \.self) { port in
                        Text(port).tag(port)
                    }
                }
                .labelsHidden()
                .frame(maxWidth: 320)

                Button("Ports neu laden") {
                    model.refreshPorts()
                }

                Button(model.isConnected ? "Trennen" : "Verbinden") {
                    if model.isConnected {
                        model.disconnect()
                    } else {
                        model.connect()
                    }
                }
                .keyboardShortcut(.defaultAction)

                Button("Reset") {
                    model.rebootDevice()
                }
                .disabled(!model.isConnected)

                Spacer()

                Text(model.connectionText)
                    .foregroundStyle(model.isConnected ? .green : .secondary)
            }

            if !model.lastError.isEmpty {
                Text(model.lastError)
                    .font(.caption)
                    .foregroundStyle(.red)
            }
        }
    }

    private var statusSection: some View {
        GroupBox("Status") {
            if let status = model.status {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        statusPill("Profil", status.profileLabel)
                        statusPill("Menü", status.currentMenu)
                        statusPill("WLAN", "\(status.wifiMode.uppercased()) \(status.wifiIP)")
                        statusPill("Zeit", timeSourceLabel(status.timeSyncSource))
                        statusPill("BLE", status.bleStatus)
                        statusPill("Encoder", status.encoderMode)
                    }

                    HStack {
                        statusPill("Helligkeit", "\(status.brightness)%")
                        statusPill("Host Vol", "\(status.localVolume)%")
                        statusPill("Host Hell", "\(status.localMacBrightness)%")
                        statusPill("Theme", status.theme)
                        statusPill("Screensaver", status.screensaverActive ? "Aktiv" : "Aus")
                    }

                    statusPill("Track", status.trackTitle.isEmpty ? "Kein Titel" : status.trackTitle)

                    if !status.lastException.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LETZTER FIRMWARE-FEHLER")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            Text(status.lastException)
                                .font(.system(size: 11, weight: .regular, design: .monospaced))
                                .foregroundStyle(.red)
                            ForEach(status.lastExceptionLog, id: \.self) { line in
                                Text(line)
                                    .font(.system(size: 10, weight: .regular, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.red.opacity(0.06))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(status.menuItems) { item in
                            HStack {
                                Text(item.selected ? ">" : " ")
                                    .font(.system(.body, design: .monospaced))
                                Text(item.label)
                            }
                            .foregroundStyle(item.selected ? Color.accentColor : Color.primary)
                        }
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.black.opacity(0.06))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                }
            } else {
                Text("Noch kein Status geladen")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var controlSection: some View {
        GroupBox("Fernsteuerung") {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 12) {
                    Button("Zurück") { model.sendAction("back") }
                    Button("Hoch") { model.sendAction("up") }
                    Button("Runter") { model.sendAction("down") }
                    Button("OK") { model.sendAction("select") }
                    Button("Status") { model.requestStatus() }
                }

                if let status = model.status {
                    Text("Makro-Tasten")
                        .font(.headline)

                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3), spacing: 10) {
                        ForEach(status.buttonOrder, id: \.self) { button in
                            Button {
                                model.sendAction(button)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(button.uppercased())
                                        .font(.headline)
                                    Text(status.buttonActions[button] ?? "")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(2)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(10)
                            }
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var profileSection: some View {
        GroupBox("Profile") {
            VStack(alignment: .leading, spacing: 12) {
                if let status = model.status {
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2), spacing: 10) {
                        ForEach(status.profiles, id: \.self) { profile in
                            Button(status.profileLabels[profile] ?? profile) {
                                model.switchProfile(profile)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(profile == status.profile ? .accentColor : .gray)
                        }
                    }

                    HStack {
                        TextField("Neues Profil", text: $model.newProfileLabel)
                            .focused($focusedField, equals: .profileName)
                        Button("Anlegen") {
                            model.createProfile()
                            focusedField = nil
                        }
                    }

                    HStack {
                        Text("Aktiv: \(status.profileLabel)")
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button("Aktives Profil löschen") {
                            model.deleteCurrentProfile()
                        }
                        .disabled(["default", "coding", "media", "system"].contains(status.profile))
                    }
                } else {
                    Text("Profile werden nach dem Verbinden geladen")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var buttonMappingSection: some View {
        GroupBox("Button-Mapping") {
            VStack(alignment: .leading, spacing: 12) {
                if let status = model.status {
                    TextField("Action suchen", text: $model.actionFilter)
                        .textFieldStyle(.roundedBorder)
                        .focused($focusedField, equals: .actionFilter)

                    Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 10) {
                        GridRow {
                            Text("Taste")
                                .font(.headline)
                            Text("Action")
                                .font(.headline)
                            Text("")
                        }

                        ForEach(status.buttonOrder, id: \.self) { button in
                            GridRow {
                                Text(button.uppercased())
                                    .frame(width: 34, alignment: .leading)
                                Picker(
                                    button.uppercased(),
                                    selection: Binding(
                                        get: { model.buttonSelections[button] ?? status.buttonActions[button] ?? "" },
                                        set: { newValue in
                                            model.buttonSelections[button] = newValue
                                            model.isEditingMappings = true
                                        }
                                    )
                                ) {
                                    ForEach(groupedActions(status.actions)) { group in
                                        Section(group.title) {
                                            ForEach(group.items) { action in
                                                Text(action.label).tag(action.value)
                                            }
                                        }
                                    }
                                }
                                .labelsHidden()
                                .frame(maxWidth: .infinity)

                                Button("Speichern") {
                                    model.assignButton(button)
                                    model.isEditingMappings = false
                                }
                                .buttonStyle(.bordered)
                            }
                        }
                    }

                    HStack {
                        Spacer()
                        Button("Alle speichern") {
                            model.assignAllButtons()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                } else {
                    Text("Mappings werden nach dem Verbinden geladen")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var settingsSection: some View {
        GroupBox("Einstellungen") {
            VStack(alignment: .leading, spacing: 12) {
                settingsSliderRow(
                    title: "Helligkeit",
                    value: $model.brightness,
                    range: 10...100,
                    step: 10,
                    format: "%.0f%%"
                )
                settingsSliderRow(
                    title: "Dimm-Helligkeit",
                    value: $model.dimBrightness,
                    range: 10...50,
                    step: 10,
                    format: "%.0f%%"
                )
                settingsSliderRow(
                    title: "Screensaver Timeout",
                    value: $model.screensaverTimeout,
                    range: 15...9999,
                    step: 15,
                    format: "%.0f s"
                )
                settingsSliderRow(
                    title: "Menü Timeout",
                    value: $model.menuTimeout,
                    range: 0...120,
                    step: 15,
                    format: "%.0f s"
                )

                HStack {
                    Picker("Theme", selection: $model.selectedTheme) {
                        ForEach(model.themeOptions, id: \.self) { item in
                            Text(item).tag(item)
                        }
                    }
                    .onChange(of: model.selectedTheme) { _ in
                        model.isEditingSettings = true
                    }
                    Picker("Idle", selection: $model.selectedIdleMode) {
                        ForEach(model.idleModeOptions, id: \.self) { item in
                            Text(item).tag(item)
                        }
                    }
                    .onChange(of: model.selectedIdleMode) { _ in
                        model.isEditingSettings = true
                    }
                }

                HStack {
                    Picker("Encoder", selection: $model.selectedEncoderMode) {
                        ForEach(model.encoderModeOptions, id: \.self) { item in
                            Text(item).tag(item)
                        }
                    }
                    .onChange(of: model.selectedEncoderMode) { _ in
                        model.isEditingSettings = true
                    }
                    Picker("Speed", selection: $model.encoderThreshold) {
                        ForEach(model.encoderThresholdOptions, id: \.self) { item in
                            Text("\(item)").tag(item)
                        }
                    }
                    .onChange(of: model.encoderThreshold) { _ in
                        model.isEditingSettings = true
                    }
                }

                HStack {
                    Picker("Hold", selection: $model.buttonAssignHoldTime) {
                        ForEach(model.holdTimeOptions, id: \.self) { item in
                            Text(String(format: "%.1f s", item)).tag(item)
                        }
                    }
                    .onChange(of: model.buttonAssignHoldTime) { _ in
                        model.isEditingSettings = true
                    }
                    Picker("Rotation", selection: $model.displayRotation) {
                        ForEach(model.rotationOptions, id: \.self) { item in
                            Text("\(item)°").tag(item)
                        }
                    }
                    .onChange(of: model.displayRotation) { _ in
                        model.isEditingSettings = true
                    }
                }

                Toggle("Encoder invertieren", isOn: $model.encoderReversed)
                    .onChange(of: model.encoderReversed) { _ in
                        model.isEditingSettings = true
                    }
                Toggle("Display invertieren", isOn: $model.displayInverted)
                    .onChange(of: model.displayInverted) { _ in
                        model.isEditingSettings = true
                    }

                HStack {
                    Spacer()
                    Button("Einstellungen speichern") {
                        model.saveSettings()
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var wifiSection: some View {
        GroupBox("WLAN") {
            VStack(alignment: .leading, spacing: 12) {
                TextField("SSID", text: $model.wifiSSID)
                    .focused($focusedField, equals: .wifiSSID)
                SecureField("Passwort", text: $model.wifiPassword)
                    .focused($focusedField, equals: .wifiPassword)
                HStack {
                    Spacer()
                    Button("WLAN speichern") {
                        model.saveWiFi()
                        focusedField = nil
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var hostStateSection: some View {
        GroupBox("Host-Status") {
            VStack(alignment: .leading, spacing: 12) {
                TextField("Laufender Titel", text: $model.hostTrackTitle)

                HStack {
                    Text("Mac Lautstärke")
                    Spacer()
                    Text("\(Int(model.hostVolume))%")
                        .foregroundStyle(.secondary)
                }
                HStack {
                    Text("Mac Helligkeit")
                    Spacer()
                    Text("\(Int(model.hostBrightness))%")
                        .foregroundStyle(.secondary)
                }

                Text("Lautstärke und Helligkeit werden beim Verbinden und danach alle 5 Sekunden vom System gelesen.")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack {
                    Button("Vom System holen") {
                        model.refreshHostStateFromSystem(send: true)
                    }
                    Spacer()
                    Button("An Pico senden") {
                        model.sendHostState()
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var logSection: some View {
        GroupBox("Serielles Log") {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    TextField("Filter", text: $model.logFilter)
                        .textFieldStyle(.roundedBorder)
                        .focused($focusedField, equals: .logFilter)
                    Picker("Typ", selection: $model.selectedLogKind) {
                        Text("Alle").tag(PicoDeckLogEntry.Kind.all)
                        Text("Fehler").tag(PicoDeckLogEntry.Kind.error)
                        Text("Firmware").tag(PicoDeckLogEntry.Kind.firmware)
                        Text("ACK").tag(PicoDeckLogEntry.Kind.ack)
                        Text("Status").tag(PicoDeckLogEntry.Kind.status)
                        Text("JSON").tag(PicoDeckLogEntry.Kind.json)
                    }
                    .labelsHidden()
                    .frame(width: 120)
                    Toggle("JSON ausblenden", isOn: $model.hideJSONLogs)
                        .toggleStyle(.checkbox)
                    Toggle("Textmodus", isOn: $model.logTextMode)
                        .toggleStyle(.checkbox)
                    Toggle("Auto folgen", isOn: $autoFollowLog)
                        .toggleStyle(.checkbox)
                    Button("Kopieren") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(filteredLogText, forType: .string)
                    }
                    .disabled(filteredLogEntries.isEmpty)
                    Button(isLogExpanded ? "Kleiner" : "Größer") {
                        isLogExpanded.toggle()
                    }
                    Button("Leeren") {
                        model.logFilter = ""
                    }
                    .disabled(model.logFilter.isEmpty)
                }

                ScrollViewReader { proxy in
                    ScrollView {
                        if model.logTextMode {
                            Text(filteredLogText)
                                .font(.system(size: 11, weight: .regular, design: .monospaced))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .textSelection(.enabled)
                        } else {
                            LazyVStack(alignment: .leading, spacing: 6) {
                                ForEach(filteredLogEntries) { entry in
                                    logRow(entry)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        Color.clear
                            .frame(height: 1)
                            .id("log-bottom")
                    }
                    .simultaneousGesture(TapGesture().onEnded {
                        autoFollowLog = false
                    })
                    .onChange(of: filteredLogText) { _ in
                        guard autoFollowLog else { return }
                        DispatchQueue.main.async {
                            withAnimation(.easeOut(duration: 0.15)) {
                                proxy.scrollTo("log-bottom", anchor: .bottom)
                            }
                        }
                    }
                    .onAppear {
                        guard autoFollowLog else { return }
                        DispatchQueue.main.async {
                            proxy.scrollTo("log-bottom", anchor: .bottom)
                        }
                    }
                }
                .frame(height: isLogExpanded ? 260 : 110)
            }
        }
    }

    private var filteredLogEntries: [PicoDeckLogEntry] {
        model.rawLog.filter { entry in
            if model.hideJSONLogs && entry.isJSON {
                return false
            }
            if model.selectedLogKind != .all && entry.kind != model.selectedLogKind {
                return false
            }
            let needle = model.logFilter.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !needle.isEmpty else {
                return true
            }
            return entry.line.lowercased().contains(needle.lowercased())
        }
    }

    private var filteredLogText: String {
        filteredLogEntries.map(\.line).joined(separator: "\n")
    }

    private func groupedActions(_ actions: [String]) -> [PicoDeckActionGroup] {
        PicoDeckActionOption.buildGroups(from: actions, filter: model.actionFilter)
    }

    @ViewBuilder
    private func logRow(_ entry: PicoDeckLogEntry) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 8) {
                Text(logLabel(for: entry))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if let envelopeType = entry.envelopeType {
                    Text(envelopeType)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            Text(entry.line)
                .font(.system(size: 11, weight: .regular, design: .monospaced))
                .foregroundStyle(logColor(for: entry))
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.vertical, 4)
        .padding(.horizontal, 8)
        .background(Color.black.opacity(0.04))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func statusPill(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title.uppercased())
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color.black.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func settingsSliderRow(
        title: String,
        value: Binding<Double>,
        range: ClosedRange<Double>,
        step: Double,
        format: String
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                Spacer()
                Text(String(format: format, value.wrappedValue))
                    .foregroundStyle(.secondary)
            }
            Slider(
                value: Binding(
                    get: { value.wrappedValue },
                    set: { newValue in
                        model.isEditingSettings = true
                        value.wrappedValue = newValue
                    }
                ),
                in: range,
                step: step
            )
        }
    }

    private func timeSourceLabel(_ value: String) -> String {
        switch value {
        case "host":
            return "Host"
        case "ntp_udp":
            return "NTP"
        case "ntp_http":
            return "HTTP"
        default:
            return "Unsynced"
        }
    }

    private func logLabel(for entry: PicoDeckLogEntry) -> String {
        switch entry.kind {
        case .all:
            return "ALL"
        case .error:
            return "ERROR"
        case .firmware:
            return "FW"
        case .json:
            return "JSON"
        case .ack:
            return "ACK"
        case .status:
            return "STATUS"
        }
    }

    private func logColor(for entry: PicoDeckLogEntry) -> Color {
        switch entry.kind {
        case .error:
            return .red
        case .ack:
            return .green
        case .status:
            return .blue
        case .firmware:
            return .primary
        case .json:
            return .secondary
        case .all:
            return .primary
        }
    }
}
