#!/usr/bin/env python3
"""Stage 1-2: turn a capture into a numbered frame directory.

Two modes, chosen by what --input points at:

  video file  -> decode and keep every --every-th frame
  directory   -> re-sample an existing frame directory

Typical use:

    # all frames out of the walkaround video
    python src/extract_frames.py --input data/raw/walk.mov --out data/frames/

    # subsample those down to the capture set
    python src/extract_frames.py --input data/frames/ --out data/selected/ --every 15

Frames are written zero-padded (frame_0000.jpg) so lexical order is capture
order for every downstream stage. An index.json is written alongside them
recording where each output frame came from -- evaluate.py needs that mapping
to line synthesized frames up against real held-out frames.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")


def list_images(directory):
    return sorted(
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.lower().endswith(IMAGE_EXTS)
    )


def resize_to_width(img, width):
    if width is None or img.shape[1] == width:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)


def save(img, out_dir, out_index, quality):
    name = f"frame_{out_index:04d}.jpg"
    cv2.imwrite(os.path.join(out_dir, name), img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return name


def from_video(args):
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        sys.exit(f"Could not open video: {args.input}")

    fps = cap.get(cv2.CAP_PROP_FPS) or None
    entries = []
    source_index = 0
    out_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        keep = source_index >= args.start and (source_index - args.start) % args.every == 0
        if args.end is not None and source_index > args.end:
            break
        if keep:
            name = save(resize_to_width(frame, args.width), args.out, out_index, args.quality)
            entries.append({"file": name, "source_index": source_index, "source": args.input})
            out_index += 1
        source_index += 1

    cap.release()
    return entries, {"kind": "video", "fps": fps, "frames_read": source_index}


def from_directory(args):
    paths = list_images(args.input)
    if not paths:
        sys.exit(f"No images found in: {args.input}")

    entries = []
    out_index = 0
    for source_index, path in enumerate(paths):
        if source_index < args.start:
            continue
        if args.end is not None and source_index > args.end:
            break
        if (source_index - args.start) % args.every != 0:
            continue
        img = cv2.imread(path)
        if img is None:
            print(f"  skipped unreadable image: {path}")
            continue
        name = save(resize_to_width(img, args.width), args.out, out_index, args.quality)
        entries.append({"file": name, "source_index": source_index, "source": path})
        out_index += 1

    return entries, {"kind": "directory", "images_seen": len(paths)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="video file, or a directory of images")
    p.add_argument("--out", required=True, help="output frame directory")
    p.add_argument("--every", type=int, default=1, help="keep every Nth frame (default: 1)")
    p.add_argument("--start", type=int, default=0, help="first source index to consider")
    p.add_argument("--end", type=int, default=None, help="last source index to consider (inclusive)")
    p.add_argument("--width", type=int, default=None, help="resize output to this width, keeping aspect")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality (default: 95)")
    args = p.parse_args()

    if args.every < 1:
        sys.exit("--every must be >= 1")

    os.makedirs(args.out, exist_ok=True)

    if os.path.isdir(args.input):
        entries, meta = from_directory(args)
    elif os.path.isfile(args.input):
        entries, meta = from_video(args)
    else:
        sys.exit(f"No such input: {args.input}")

    index = {
        "input": args.input,
        "every": args.every,
        "start": args.start,
        "width": args.width,
        "n_frames": len(entries),
        "frames": entries,
        **meta,
    }
    with open(os.path.join(args.out, "index.json"), "w") as fh:
        json.dump(index, fh, indent=2)

    print(f"Wrote {len(entries)} frames to {args.out}")
    if entries:
        print(f"  {entries[0]['file']} .. {entries[-1]['file']}")
    print(f"  index.json maps each output frame back to its source index")


if __name__ == "__main__":
    main()
