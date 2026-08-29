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

VERSION="${1:?usage: run_sfm.sh <version-name> [sequential|exhaustive]}"
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

# Two captures merged into one folder are not one continuous walk, so
# sequential matching alone cannot link them -- it only ever compares
# neighbours in filename order, which never crosses from one set to the other.
# Exhaustive matching is the way to fuse them, accepting the symmetry risk
# above because RANSAC's geometric verification rejects most false pairs and
# the two captures sit at clearly different radii, which disambiguates further.
MATCHER="${2:-sequential}"
if [ "$MATCHER" = "loop" ]; then
    # For two captures merged into one folder. Sequential matching keeps each
    # walk's own links honest (neighbours in filename order), while vocabulary-
    # tree loop detection proposes the cross-capture pairs sequential can never
    # find. Unlike exhaustive it proposes only a bounded number of candidates
    # per image, all of which still face RANSAC verification -- which is what
    # kept exhaustive from working here: given every pair to consider, enough
    # false matches between the pavilion's near-identical faces survived
    # verification to fold the reconstruction.
    VOCAB="${VOCAB_TREE:?set VOCAB_TREE to a downloaded vocab_tree_*.bin}"
    echo "==> sequential + vocabulary-tree loop matching"
    colmap sequential_matcher \
        --database_path "$DB" \
        --SequentialMatching.overlap 10 \
        --SequentialMatching.quadratic_overlap 1 \
        --SequentialMatching.loop_detection 1 \
        --SequentialMatching.loop_detection_period 5 \
        --SequentialMatching.loop_detection_num_images 30 \
        --SequentialMatching.vocab_tree_path "$VOCAB" \
        --FeatureMatching.use_gpu 0
elif [ "$MATCHER" = "exhaustive" ]; then
    echo "==> exhaustive matching (fusing separate captures)"
    colmap exhaustive_matcher \
        --database_path "$DB" \
        --FeatureMatching.use_gpu 0
else
    echo "==> sequential matching"
    colmap sequential_matcher \
        --database_path "$DB" \
        --SequentialMatching.overlap 10 \
        --SequentialMatching.quadratic_overlap 1 \
        --FeatureMatching.use_gpu 0
fi

echo "==> mapping (incremental SfM)"
colmap mapper \
    --database_path "$DB" \
    --image_path "$IMAGES" \
    --output_path "$WORK/sparse"

# 3D Gaussian splatting refuses anything but PINHOLE/SIMPLE_PINHOLE -- it has no
# distortion model of its own. SIMPLE_RADIAL is the better model for SfM itself
# (a phone lens genuinely has radial distortion), so keep it above and remove
# the distortion here instead: image_undistorter rectifies the photographs and
# rewrites the cameras as PINHOLE. undistorted/ is what the notebooks consume.
if [ -d "$WORK/sparse/0" ]; then
    echo
    echo "==> undistorting to PINHOLE (required by 3D Gaussian splatting)"
    rm -rf "$WORK/undistorted"
    colmap image_undistorter \
        --image_path "$IMAGES" \
        --input_path "$WORK/sparse/0" \
        --output_path "$WORK/undistorted" \
        --output_type COLMAP
    # The splatting loaders expect sparse/0/, image_undistorter writes sparse/.
    if [ -d "$WORK/undistorted/sparse" ] && [ ! -d "$WORK/undistorted/sparse/0" ]; then
        mkdir -p "$WORK/undistorted/sparse/0"
        mv "$WORK/undistorted/sparse"/*.bin "$WORK/undistorted/sparse/0/" 2>/dev/null || true
    fi
fi

echo
echo "==> result"
for model in "$WORK"/sparse/*/; do
    [ -d "$model" ] || continue
    echo "model $(basename "$model"):"
    colmap model_analyzer --path "$model" 2>&1 | sed 's/^/    /'
done
