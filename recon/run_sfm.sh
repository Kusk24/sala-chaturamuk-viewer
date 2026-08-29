#!/usr/bin/env bash
# Structure-from-motion over one capture, as the first half of the 3D
# reconstruction comparison. This recovers where each photograph was taken;
# the neural stage (3D Gaussian splatting / NeRF) consumes these poses.
#
#   ./recon/run_sfm.sh salathai_version2
#
# NOTE ON SCOPE: this is reconstruction, which the image-based rendering
# pipeline in src/ deliberately avoids. It exists to compare the two
# approaches on the same photographs, not to replace the IBR viewer.
#
# Matching is SEQUENTIAL, not exhaustive, for the reason match_features.py
# already documents: the pavilion is four-porched and nearly symmetric under
# 90-degree rotation, so faces that are far apart on the walk look alike.
# Exhaustive matching invites false correspondences between different faces,
# which SfM would resolve as a folded, self-intersecting camera path.
set -euo pipefail

VERSION="${1:?usage: run_sfm.sh <version-name>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGES="$ROOT/data/selected_$VERSION"
WORK="$ROOT/recon/$VERSION"

[ -d "$IMAGES" ] || { echo "No such image directory: $IMAGES" >&2; exit 1; }

mkdir -p "$WORK/sparse"
DB="$WORK/database.db"

echo "==> feature extraction  ($(ls "$IMAGES" | grep -ci jpg) images)"
# single_camera: every frame came from the same phone at the same 1x lens, so
# one shared intrinsic model is both correct and far better conditioned.
# use_gpu 0: COLMAP's GPU SIFT is CUDA-only and this is an Apple silicon Mac.
# Option names are COLMAP 4.x (FeatureExtraction/FeatureMatching); 3.x called
# these SiftExtraction/SiftMatching.
colmap feature_extractor \
    --database_path "$DB" \
    --image_path "$IMAGES" \
    --ImageReader.single_camera 1 \
    --ImageReader.camera_model SIMPLE_RADIAL \
    --FeatureExtraction.use_gpu 0

echo "==> sequential matching"
colmap sequential_matcher \
    --database_path "$DB" \
    --SequentialMatching.overlap 10 \
    --SequentialMatching.quadratic_overlap 1 \
    --FeatureMatching.use_gpu 0

echo "==> mapping (incremental SfM)"
colmap mapper \
    --database_path "$DB" \
    --image_path "$IMAGES" \
    --output_path "$WORK/sparse"

echo
echo "==> result"
for model in "$WORK"/sparse/*/; do
    [ -d "$model" ] || continue
    echo "model $(basename "$model"):"
    colmap model_analyzer --path "$model" 2>&1 | sed 's/^/    /'
done
