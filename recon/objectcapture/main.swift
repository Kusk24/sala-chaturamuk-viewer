// Photogrammetry via Apple's RealityKit PhotogrammetrySession.
//
//   swiftc -O recon/objectcapture/main.swift -o recon/objectcapture/photogrammetry
//   ./recon/objectcapture/photogrammetry <image-dir> <output.usdz> [detail] [--mask]
//
// This is the third arm of the reconstruction comparison, and the only one that
// runs on this machine: 3D Gaussian splatting's rasteriser and COLMAP's dense
// stage are both hand-written CUDA, so neither builds on Apple silicon at any
// speed. PhotogrammetrySession runs on the M2's own GPU/Neural Engine and,
// unlike splatting, emits an actual textured mesh.
//
// It is also a genuinely different method from the other two: Apple does not
// document the internals, so the paper should describe it as a black-box
// commercial photogrammetry pipeline, not claim it is classical MVS.
//
// detail: preview | reduced | medium | full | raw   (default: medium)
//   preview/reduced are quick and coarse; full/raw are slow and produce very
//   heavy meshes. medium is the useful middle for a pavilion.
//
// --mask asks the API to isolate a foreground object from its background. That
// suits a thing on a turntable, not a building standing in front of a lake, so
// it is off by default -- but worth trying if the background swamps the result.

import Foundation
import RealityKit

// MARK: - arguments

let args = CommandLine.arguments
guard args.count >= 3 else {
    print("""
    usage: photogrammetry <image-dir> <output.usdz> [detail] [--mask]
           detail: preview | reduced | medium | full | raw   (default: medium)
    """)
    exit(2)
}

let inputURL = URL(fileURLWithPath: args[1], isDirectory: true)
let outputURL = URL(fileURLWithPath: args[2])
let wantsMask = args.contains("--mask")

let detailArg = args.count >= 4 && !args[3].hasPrefix("--") ? args[3].lowercased() : "medium"
let detail: PhotogrammetrySession.Request.Detail
switch detailArg {
case "preview": detail = .preview
case "reduced": detail = .reduced
case "medium":  detail = .medium
case "full":    detail = .full
case "raw":     detail = .raw
default:
    print("Unknown detail '\(detailArg)'. Use preview|reduced|medium|full|raw.")
    exit(2)
}

let imageCount = (try? FileManager.default.contentsOfDirectory(atPath: inputURL.path))?
    .filter { ["jpg", "jpeg", "png", "heic"].contains(($0 as NSString).pathExtension.lowercased()) }
    .count ?? 0
guard imageCount > 0 else {
    print("No images found in \(inputURL.path)")
    exit(1)
}

// MARK: - configuration

var config = PhotogrammetrySession.Configuration()

// The photographs are a single ordered walk around the pavilion, so telling the
// session they are sequential lets it assume consecutive frames overlap instead
// of comparing every pair. Same reasoning as the sequential matching used for
// COLMAP, and the same reasoning src/match_features.py already documents: the
// pavilion is four-porched and nearly symmetric under 90-degree rotation, so
// unordered comparison invites matches between different faces.
config.sampleOrdering = .sequential

// The gold filigree and pale render carry fine but low-contrast texture, and
// large parts of every frame are flat overcast sky.
config.featureSensitivity = .high

if wantsMask {
    config.isObjectMaskingEnabled = true
}

print("""
    images:   \(imageCount) in \(inputURL.lastPathComponent)
    detail:   \(detailArg)
    ordering: sequential
    masking:  \(wantsMask)
    output:   \(outputURL.path)
    """)

// MARK: - run

let session: PhotogrammetrySession
do {
    session = try PhotogrammetrySession(input: inputURL, configuration: config)
} catch {
    print("Could not start a session: \(error)")
    print("PhotogrammetrySession needs Apple silicon (or a 4GB+ AMD GPU) and macOS 12+.")
    exit(1)
}

let done = DispatchSemaphore(value: 0)
var failed = false

Task {
    do {
        // Progress is reported as a fraction; print it sparsely so a long run
        // leaves a readable log rather than thousands of lines.
        var lastShown = -1
        for try await output in session.outputs {
            switch output {
            case .requestProgress(_, let fraction):
                let pct = Int(fraction * 100)
                if pct >= lastShown + 5 {
                    lastShown = pct
                    print("  \(pct)%")
                    fflush(stdout)
                }
            case .requestComplete(_, let result):
                if case .modelFile(let url) = result {
                    print("wrote \(url.path)")
                }
            case .requestError(_, let error):
                print("request failed: \(error)")
                failed = true
            case .processingComplete:
                done.signal()
            case .inputComplete:
                print("input processed, reconstructing…")
            case .invalidSample(let id, let reason):
                print("  skipped sample \(id): \(reason)")
            case .skippedSample(let id):
                print("  skipped sample \(id)")
            case .automaticDownsampling:
                print("  note: images were downsampled automatically")
            case .stitchingIncomplete:
                // The predicted failure mode for a building rather than a
                // turntable object: some views could not be stitched, so the
                // mesh is partial. Worth surfacing, not swallowing.
                print("  WARNING: stitching incomplete — the mesh will be partial")
            case .processingCancelled:
                print("cancelled")
                failed = true
                done.signal()
            @unknown default:
                break
            }
        }
    } catch {
        print("session failed: \(error)")
        failed = true
        done.signal()
    }
}

do {
    try session.process(requests: [.modelFile(url: outputURL, detail: detail)])
} catch {
    print("Could not submit the request: \(error)")
    exit(1)
}

done.wait()
exit(failed ? 1 : 0)
