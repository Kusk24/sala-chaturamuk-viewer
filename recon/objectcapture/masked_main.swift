// Photogrammetry with per-image sky masks.
//
//   swiftc -O recon/objectcapture/masked_main.swift -o recon/objectcapture/photogrammetry_masked
//   ./recon/objectcapture/photogrammetry_masked <image-dir> <mask-dir> <output.usdz> [detail]
//
// Second attempt at the Apple-photogrammetry arm of the comparison. The first
// run (main.swift, folder input) reconstructed the overcast sky as geometry --
// a white sheet draped over the pavilion roof. The folder-based API offers no
// way to say "ignore these pixels", but the sample-based API does:
// PhotogrammetrySample.objectMask, 0 = ignore, nonzero = object.
//
// Masks come from make_masks.py: one PNG per photograph, same basename.
// Samples are built lazily -- 146 photographs at 4032x3024 as pixel buffers
// would be ~7 GB if loaded eagerly.

import Foundation
import RealityKit
import CoreVideo
import ImageIO
import CoreGraphics

let args = CommandLine.arguments
guard args.count >= 4 else {
    print("usage: photogrammetry_masked <image-dir> <mask-dir> <output.usdz> [detail]")
    exit(2)
}
let imageDir = URL(fileURLWithPath: args[1], isDirectory: true)
let maskDir = URL(fileURLWithPath: args[2], isDirectory: true)
let outputURL = URL(fileURLWithPath: args[3])
let detailArg = args.count >= 5 ? args[4].lowercased() : "medium"
let detail: PhotogrammetrySession.Request.Detail
switch detailArg {
case "preview": detail = .preview
case "reduced": detail = .reduced
case "medium":  detail = .medium
case "full":    detail = .full
case "raw":     detail = .raw
default: print("unknown detail '\(detailArg)'"); exit(2)
}

func cgImage(_ url: URL) -> CGImage? {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
    return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

func pixelBuffer(_ cg: CGImage, gray: Bool) -> CVPixelBuffer? {
    var pb: CVPixelBuffer?
    let fmt = gray ? kCVPixelFormatType_OneComponent8 : kCVPixelFormatType_32BGRA
    CVPixelBufferCreate(nil, cg.width, cg.height, fmt,
                        [kCVPixelBufferCGImageCompatibilityKey: true] as CFDictionary, &pb)
    guard let buf = pb else { return nil }
    CVPixelBufferLockBaseAddress(buf, [])
    defer { CVPixelBufferUnlockBaseAddress(buf, []) }
    let space = gray ? CGColorSpaceCreateDeviceGray() : CGColorSpaceCreateDeviceRGB()
    let info = gray ? CGImageAlphaInfo.none.rawValue
                    : CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue
    guard let ctx = CGContext(data: CVPixelBufferGetBaseAddress(buf),
                              width: cg.width, height: cg.height, bitsPerComponent: 8,
                              bytesPerRow: CVPixelBufferGetBytesPerRow(buf),
                              space: space, bitmapInfo: info) else { return nil }
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: CGFloat(cg.width), height: CGFloat(cg.height)))
    return buf
}

let jpgs = (try! FileManager.default.contentsOfDirectory(atPath: imageDir.path))
    .filter { $0.lowercased().hasSuffix(".jpg") }.sorted()
guard !jpgs.isEmpty else { print("no jpgs in \(imageDir.path)"); exit(1) }
print("images: \(jpgs.count)   detail: \(detailArg)   masks: \(maskDir.lastPathComponent)")

// Lazy sequence: one photograph + mask in memory at a time.
let samples = AnySequence<PhotogrammetrySample> {
    var idx = 0
    return AnyIterator {
        while idx < jpgs.count {
            let name = jpgs[idx]; let id = idx; idx += 1
            let maskName = (name as NSString).deletingPathExtension + ".png"
            guard let img = cgImage(imageDir.appendingPathComponent(name)),
                  let ibuf = pixelBuffer(img, gray: false) else {
                print("  skipping unreadable \(name)"); continue
            }
            var sample = PhotogrammetrySample(id: id, image: ibuf)
            if let mcg = cgImage(maskDir.appendingPathComponent(maskName)),
               let mbuf = pixelBuffer(mcg, gray: true) {
                sample.objectMask = mbuf
            } else {
                print("  no mask for \(name), using full frame")
            }
            return sample
        }
        return nil
    }
}

var config = PhotogrammetrySession.Configuration()
config.sampleOrdering = .sequential      // one ordered walk; see main.swift
config.featureSensitivity = .high
config.isObjectMaskingEnabled = false    // OUR masks, not Apple's auto-isolation

let session: PhotogrammetrySession
do { session = try PhotogrammetrySession(input: samples, configuration: config) }
catch { print("could not start session: \(error)"); exit(1) }

let done = DispatchSemaphore(value: 0)
var failed = false
Task {
    do {
        var lastShown = -1
        for try await output in session.outputs {
            switch output {
            case .requestProgress(_, let f):
                let pct = Int(f * 100)
                if pct >= lastShown + 5 { lastShown = pct; print("  \(pct)%"); fflush(stdout) }
            case .requestComplete(_, let r):
                if case .modelFile(let url) = r { print("wrote \(url.path)") }
            case .requestError(_, let e): print("request failed: \(e)"); failed = true
            case .processingComplete: done.signal()
            case .inputComplete: print("input processed, reconstructing…")
            case .invalidSample(let id, let reason): print("  invalid sample \(id): \(reason)")
            case .skippedSample(let id): print("  skipped \(id)")
            case .automaticDownsampling: print("  note: automatic downsampling")
            case .stitchingIncomplete: print("  WARNING: stitching incomplete — partial mesh")
            case .processingCancelled: failed = true; done.signal()
            @unknown default: break
            }
        }
    } catch { print("session failed: \(error)"); failed = true; done.signal() }
}
do { try session.process(requests: [.modelFile(url: outputURL, detail: detail)]) }
catch { print("could not submit request: \(error)"); exit(1) }
done.wait()
exit(failed ? 1 : 0)
