// Offscreen renderer for checking reconstructed meshes without a GUI.
//   swiftc -O usdz_snap.swift -o usdz_snap
//   ./usdz_snap <in.usdz> <out-prefix> [azimuths-degrees...]
// Writes <out-prefix>_<az>.png for each azimuth, orbiting at a gentle
// downward tilt around the mesh's bounding-box centre.
import Foundation
import SceneKit
import AppKit

let a = CommandLine.arguments
guard a.count >= 3 else { print("usage: usdz_snap <in.usdz> <out-prefix> [az...]"); exit(2) }
let azimuths = a.count > 3 ? Array(a[3...]).compactMap { Double($0) } : [0, 90, 180, 270]

guard let scene = try? SCNScene(url: URL(fileURLWithPath: a[1]), options: nil) else {
    print("could not load \(a[1])"); exit(1)
}
var mn = SCNVector3Zero, mx = SCNVector3Zero
scene.rootNode.__getBoundingBoxMin(&mn, max: &mx)
let c = SCNVector3((mn.x+mx.x)/2, (mn.y+mx.y)/2, (mn.z+mx.z)/2)
let ext = max(mx.x-mn.x, max(mx.y-mn.y, mx.z-mn.z))
let dist = CGFloat(ext) * 1.35

scene.rootNode.addChildNode({ let n = SCNNode(); n.light = SCNLight(); n.light!.type = .ambient
    n.light!.intensity = 600; return n }())

let renderer = SCNRenderer(device: MTLCreateSystemDefaultDevice(), options: nil)
renderer.scene = scene
renderer.autoenablesDefaultLighting = true

for az in azimuths {
    let cam = SCNNode(); cam.camera = SCNCamera(); cam.camera!.zFar = Double(dist) * 10
    let r = az * .pi / 180, elev = 18.0 * .pi / 180
    cam.position = SCNVector3(c.x + CGFloat(cos(elev)*sin(r))*dist,
                              c.y + CGFloat(sin(elev))*dist,
                              c.z + CGFloat(cos(elev)*cos(r))*dist)
    cam.look(at: c)
    scene.rootNode.addChildNode(cam)
    renderer.pointOfView = cam
    let img = renderer.snapshot(atTime: 0, with: CGSize(width: 1280, height: 900),
                                antialiasingMode: .multisampling4X)
    let out = "\(a[2])_\(Int(az)).png"
    if let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
       let png = rep.representation(using: .png, properties: [:]) {
        try? png.write(to: URL(fileURLWithPath: out)); print("wrote \(out)")
    }
    cam.removeFromParentNode()
}
