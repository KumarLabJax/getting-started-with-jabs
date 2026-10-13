"""Generate the mouse keypoint reference diagram for the Data Ingestion notebook.

The diagram is used in static_build_notebooks/01_data_ingestion.ipynb
(assets/keypoint_diagram.svg).

Instructor/developer-run tooling - the output SVG is what ships to students,
not this script. Draws a single real frame from data/toy/, cropped tight to
the mouse, with each of the JABS 12-point pose model's keypoints distinctly
colored and labeled. Labels are placed on a "starburst" ring around the
mouse, spaced apart with a robust overlap-removal pass (cut the circle at its
largest gap, unroll to a line, then repeatedly push any two labels closer
than --min-label-gap apart) - naive radial-offset-from-centroid placement
clusters labels for keypoints that sit close together (e.g. nose, base_neck,
and the front paws), so the more robust approach is needed for readability.

Usage:
    python developer/scripts/make_keypoint_diagram.py
    python developer/scripts/make_keypoint_diagram.py --session 2013 --frame 500
"""

import argparse
from pathlib import Path

import cv2
import h5py
import matplotlib.pyplot as plt
import numpy as np
from jabs.core.abstract.pose_est import PoseEstimation

REPO = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT = REPO / "student_notebooks" / "assets" / "keypoint_diagram.svg"

KEYPOINT_NAMES = [k.name.lower() for k in PoseEstimation.KeypointIndex]
SKELETON_EDGES = [
    (int(s), int(e))
    for chain in PoseEstimation.FULL_CONNECTED_SEGMENTS
    for s, e in zip(chain, chain[1:])
]

# Distinct color per keypoint, grouped by body region.
COLORS = {
    "nose": "#E63946",
    "left_ear": "#457B9D",
    "right_ear": "#1D3557",
    "base_neck": "#6A4C93",
    "left_front_paw": "#2A9D8F",
    "right_front_paw": "#52B788",
    "center_spine": "#333333",
    "left_rear_paw": "#F4A261",
    "right_rear_paw": "#E76F51",
    "base_tail": "#F72585",
    "mid_tail": "#B5179E",
    "tip_tail": "#7209B7",
}


def load_frame(session: str, frame: int) -> tuple[np.ndarray, np.ndarray]:
    """Load the keypoints and the matching video frame for one toy session.

    Reads data/toy/<session>_pose_est_v6.h5 and data/toy/<session>.avi.

    Args:
        session: Toy session id (file stem), for example "2013".
        frame: Zero-based frame index to read from both pose and video.

    Returns:
        A tuple of (keypoints, frame_rgb). keypoints is a float array of shape
        (12, 2) in (y, x) order for the first animal; frame_rgb is the RGB
        video frame as an image array.

    Raises:
        RuntimeError: If the video frame cannot be read.
    """
    pose_path = REPO / "data" / "toy" / f"{session}_pose_est_v6.h5"
    video_path = REPO / "data" / "toy" / f"{session}.avi"

    with h5py.File(str(pose_path), "r") as f:
        points = f["poseest/points"][frame, 0, :, :].astype(float)

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, img = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"could not read frame {frame} from {video_path}")
    return points, cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def crop_to_keypoints(img: np.ndarray, xs: np.ndarray, ys: np.ndarray, pad: int):
    """Crop an image to the keypoint bounding box plus padding.

    Args:
        img: Image array of shape (height, width, ...).
        xs: Keypoint x coordinates in full-image pixels.
        ys: Keypoint y coordinates in full-image pixels.
        pad: Padding in pixels added on every side, clamped to the image bounds.

    Returns:
        A tuple of (crop, xs_local, ys_local): the cropped image and the keypoint
        coordinates shifted into the crop's coordinate frame.
    """
    h, w = img.shape[:2]
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(w, int(xs.max()) + pad)
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(h, int(ys.max()) + pad)
    return img[y0:y1, x0:x1], xs - x0, ys - y0


def place_labels_on_ring(xs: np.ndarray, ys: np.ndarray, min_gap_deg: float) -> dict[int, tuple[float, float]]:
    """Angularly space one label per keypoint around the body centroid.

    Naive placement (offset each label directly away from the centroid) makes
    labels overlap whenever two keypoints are close together spatially (their
    raw angles from the centroid end up close too). This instead: computes
    each keypoint's raw angle, cuts the circle at its single largest gap so
    the ring becomes a line (avoids the two ends of an angular cluster fighting
    across the wrap-around point), then repeatedly pushes any two
    now-linearly-ordered labels that are closer than min_gap_deg apart to
    exactly min_gap_deg apart. This is a small, guaranteed-convergent version
    of isotonic-regression-style overlap removal - reliable for the N=12
    keypoints here, unlike naive per-pair circular nudging (which can leave
    two labels stuck on top of each other for a tight 3+ point cluster).

    Args:
        xs: Keypoint x coordinates (crop-local pixels).
        ys: Keypoint y coordinates (crop-local pixels).
        min_gap_deg: Minimum angular gap between adjacent labels, in degrees.

    Returns:
        A tuple of (centroid, angles). centroid is a (y, x) array of the mean
        keypoint position; angles is an array of label angles in radians, indexed
        by keypoint. The caller applies the ring radius.
    """
    n = len(xs)
    centroid = np.array([ys.mean(), xs.mean()])
    min_gap = np.radians(min_gap_deg)

    raw_angles = np.array([np.arctan2(ys[i] - centroid[0], xs[i] - centroid[1]) for i in range(n)])
    order = np.argsort(raw_angles)
    sorted_angles = raw_angles[order]

    ext = np.concatenate([sorted_angles, sorted_angles[:1] + 2 * np.pi])
    cut = np.argmax(np.diff(ext))
    unrolled_order = np.concatenate([order[cut + 1:], order[: cut + 1]])
    unrolled_angles = raw_angles[unrolled_order].copy()
    for i in range(1, n):
        while unrolled_angles[i] < unrolled_angles[i - 1]:
            unrolled_angles[i] += 2 * np.pi

    seq = unrolled_angles.copy()
    for _ in range(200):
        violated = False
        for i in range(n - 1):
            gap = seq[i + 1] - seq[i]
            if gap < min_gap:
                shift = (min_gap - gap) / 2
                seq[i] -= shift
                seq[i + 1] += shift
                violated = True
        if not violated:
            break

    final_angles = np.zeros(n)
    final_angles[unrolled_order] = seq
    return centroid, final_angles


def render(session: str, frame: int, pad: int, min_gap_deg: float, marker_size: float, output: Path) -> None:
    """Render the labeled keypoint diagram and save it as an SVG.

    Draws the cropped frame with the skeleton, colored keypoints, and labels on a
    ring around the mouse. Creates the output's parent directory if needed and
    prints the saved path.

    Args:
        session: Toy session id (file stem), for example "2013".
        frame: Zero-based frame index to draw.
        pad: Crop padding in pixels around the keypoint bounding box.
        min_gap_deg: Minimum angular gap between labels, in degrees.
        marker_size: Keypoint marker size passed to matplotlib scatter.
        output: Destination SVG path.
    """
    points, img_rgb = load_frame(session, frame)
    ys, xs = points[:, 0], points[:, 1]
    crop, xs_c, ys_c = crop_to_keypoints(img_rgb, xs, ys, pad)
    crop_h, crop_w = crop.shape[:2]

    centroid, angles = place_labels_on_ring(xs_c, ys_c, min_gap_deg)
    label_radius = max(crop_w, crop_h) * 0.62
    label_pos = {
        i: (centroid[1] + label_radius * np.cos(angles[i]), centroid[0] + label_radius * np.sin(angles[i]))
        for i in range(12)
    }

    fig, ax = plt.subplots(figsize=(11, 11))
    ax.imshow(crop, extent=(0, crop_w, crop_h, 0))
    for s, e in SKELETON_EDGES:
        ax.plot([xs_c[s], xs_c[e]], [ys_c[s], ys_c[e]], "-", color="#FFD65A", alpha=0.9, linewidth=2.5, zorder=4)
    for i, name in enumerate(KEYPOINT_NAMES):
        color = COLORS[name]
        px, py = xs_c[i], ys_c[i]
        ax.scatter(px, py, s=marker_size, c=color, zorder=6, edgecolors="white", linewidths=1.2)
        lx, ly = label_pos[i]
        ax.plot([px, lx], [py, ly], "-", color=color, alpha=0.75, linewidth=1.1, zorder=5)
        ax.annotate(
            name.replace("_", " "), (lx, ly), fontsize=12, fontweight="bold", color="white",
            ha="center", va="center", zorder=7,
            bbox=dict(boxstyle="round,pad=0.35", fc=color, ec="white", lw=1.3, alpha=0.97),
        )
    ax.set_title("Mouse Keypoint Positions (JABS 12-point pose model)", fontsize=14, fontweight="bold", pad=16)
    ax.axis("off")
    margin = label_radius * 0.55
    ax.set_xlim(-margin, crop_w + margin)
    ax.set_ylim(crop_h + margin, -margin)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, format="svg")
    plt.close(fig)
    print(f"Saved {output}")


def main() -> None:
    """Parse command-line arguments and render the keypoint diagram."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session", default="2013", help="toy session id (default: 2013)")
    parser.add_argument("--frame", type=int, default=2840,
                         help="frame index - chosen for session 2013 as centered, high-confidence, "
                              "straight body (tail curls, which is fine) (default: 2840)")
    parser.add_argument("--pad", type=int, default=15, help="crop padding in pixels around the keypoint bounding box")
    parser.add_argument("--min-label-gap", type=float, default=28.0, help="minimum angular gap between labels, in degrees")
    parser.add_argument("--marker-size", type=float, default=90.0,
                         help="keypoint marker size (default: 90 - smaller than the original 150 so "
                              "tightly-clustered points like the ears/front paws don't visually collide)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.session, args.frame, args.pad, args.min_label_gap, args.marker_size, args.output)


if __name__ == "__main__":
    main()
