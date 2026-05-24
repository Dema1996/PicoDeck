import Foundation
import Darwin

final class SerialPort: @unchecked Sendable {
    enum SerialError: Error, LocalizedError {
        case openFailed(String)
        case configFailed(String)
        case writeFailed(String)

        var errorDescription: String? {
            switch self {
            case .openFailed(let path):
                return "Konnte Port nicht öffnen: \(path)"
            case .configFailed(let path):
                return "Konnte Port nicht konfigurieren: \(path)"
            case .writeFailed(let message):
                return "Schreiben fehlgeschlagen: \(message)"
            }
        }
    }

    let path: String
    private let fileDescriptor: Int32
    private var readSource: DispatchSourceRead?
    private var inputBuffer = Data()
    var onLine: ((String) -> Void)?
    var onDisconnect: (() -> Void)?

    init(path: String, baudRate: speed_t = speed_t(B115200)) throws {
        self.path = path
        let fd = open(path, O_RDWR | O_NOCTTY | O_NONBLOCK)
        guard fd >= 0 else {
            throw SerialError.openFailed(path)
        }

        var options = termios()
        guard tcgetattr(fd, &options) == 0 else {
            Darwin.close(fd)
            throw SerialError.configFailed(path)
        }

        cfmakeraw(&options)
        options.c_cflag |= tcflag_t(CLOCAL | CREAD)
        options.c_cflag &= ~tcflag_t(CSTOPB | PARENB | CRTSCTS)
        options.c_cflag &= ~tcflag_t(CSIZE)
        options.c_cflag |= tcflag_t(CS8)
        cfsetspeed(&options, baudRate)

        guard tcsetattr(fd, TCSANOW, &options) == 0 else {
            Darwin.close(fd)
            throw SerialError.configFailed(path)
        }

        _ = fcntl(fd, F_SETFL, 0)

        self.fileDescriptor = fd
        let source = DispatchSource.makeReadSource(fileDescriptor: fd, queue: DispatchQueue.global(qos: .userInitiated))
        source.setEventHandler { [weak self] in
            self?.readAvailable()
        }
        source.setCancelHandler {
            Darwin.close(fd)
        }
        self.readSource = source
        source.resume()
    }

    deinit {
        close()
    }

    func close() {
        readSource?.cancel()
        readSource = nil
    }

    func sendLine(_ line: String) throws {
        guard let data = (line + "\n").data(using: .utf8) else {
            throw SerialError.writeFailed("Ungültige UTF-8 Daten")
        }
        let result = data.withUnsafeBytes { ptr in
            write(fileDescriptor, ptr.baseAddress, ptr.count)
        }
        if result < 0 {
            if errno == EIO || errno == EBADF || errno == ENXIO {
                onDisconnect?()
            }
            throw SerialError.writeFailed(String(cString: strerror(errno)))
        }
    }

    private func consume(data: Data) {
        guard !data.isEmpty else {
            onDisconnect?()
            return
        }
        inputBuffer.append(data)
        while let newline = inputBuffer.firstIndex(of: 0x0A) {
            let lineData = inputBuffer.prefix(upTo: newline)
            inputBuffer.removeSubrange(...newline)
            guard let line = String(data: lineData, encoding: .utf8) else {
                continue
            }
            onLine?(line.trimmingCharacters(in: .whitespacesAndNewlines))
        }
    }

    private func readAvailable() {
        var buf = [UInt8](repeating: 0, count: 512)
        while true {
            let count = Darwin.read(fileDescriptor, &buf, buf.count)
            if count > 0 {
                consume(data: Data(buf.prefix(count)))
                if count < buf.count {
                    return
                }
                continue
            }
            if count == 0 {
                onDisconnect?()
                return
            }
            if errno == EAGAIN || errno == EWOULDBLOCK {
                return
            }
            onDisconnect?()
            return
        }
    }

    static func discoverPorts() -> [String] {
        let devURL = URL(fileURLWithPath: "/dev")
        let items = (try? FileManager.default.contentsOfDirectory(
            at: devURL,
            includingPropertiesForKeys: nil
        )) ?? []
        return items
            .map(\.path)
            .filter { path in
                path.contains("cu.usbmodem")
                || path.contains("cu.usbserial")
                || path.contains("tty.usbmodem")
                || path.contains("tty.usbserial")
            }
            .sorted()
    }
}
