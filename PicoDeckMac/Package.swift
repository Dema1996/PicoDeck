// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PicoDeckMac",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(name: "PicoDeckMac", targets: ["PicoDeckMac"]),
    ],
    targets: [
        .executableTarget(
            name: "PicoDeckMac",
            path: "Sources"
        ),
    ]
)
