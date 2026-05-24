import AudioToolbox
import CoreAudio
import Foundation
import IOKit
import IOKit.graphics

enum HostSystemState {
    static func outputVolumePercent() -> Int? {
        var deviceID = AudioDeviceID(0)
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var deviceAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        let deviceStatus = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &deviceAddress,
            0,
            nil,
            &size,
            &deviceID
        )
        guard deviceStatus == noErr else {
            return nil
        }

        var volume = Float32(0)
        size = UInt32(MemoryLayout<Float32>.size)
        var volumeAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwareServiceDeviceProperty_VirtualMainVolume,
            mScope: kAudioDevicePropertyScopeOutput,
            mElement: kAudioObjectPropertyElementMain
        )

        let volumeStatus = AudioObjectGetPropertyData(
            deviceID,
            &volumeAddress,
            0,
            nil,
            &size,
            &volume
        )
        guard volumeStatus == noErr else {
            return nil
        }

        let percent = Int((Double(volume) * 100.0).rounded())
        return max(0, min(100, percent))
    }

    static func displayBrightnessPercent() -> Int? {
        guard let service = firstBrightnessService() else {
            return nil
        }
        defer { IOObjectRelease(service) }

        var brightness: Float = 0
        let status = IODisplayGetFloatParameter(
            service,
            0,
            kIODisplayBrightnessKey as CFString,
            &brightness
        )
        guard status == KERN_SUCCESS else {
            return nil
        }

        let percent = Int((Double(brightness) * 100.0).rounded())
        return max(0, min(100, percent))
    }

    private static func firstBrightnessService() -> io_service_t? {
        let matching = IOServiceMatching("IODisplayConnect")
        var iterator: io_iterator_t = 0
        let status = IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iterator)
        guard status == KERN_SUCCESS else {
            return nil
        }
        defer { IOObjectRelease(iterator) }

        while true {
            let service = IOIteratorNext(iterator)
            if service == 0 {
                return nil
            }
            var brightness: Float = 0
            let result = IODisplayGetFloatParameter(
                service,
                0,
                kIODisplayBrightnessKey as CFString,
                &brightness
            )
            if result == KERN_SUCCESS {
                return service
            }
            IOObjectRelease(service)
        }
    }
}
