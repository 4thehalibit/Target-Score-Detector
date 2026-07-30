"""
Single-photo scorer for the Rinehart 18-1 "clover" face.

Stage 1 (this file): detect the face geometry from a straight-on photo of the
green clover disc -- its center, radius, and the four black clover dots -- and
render a scoring overlay so the zones/points can be confirmed visually.

Arrow detection (stage 2) is added later once we have test photos with arrows.
"""
import cv2
import numpy as np

# ---- tunables -------------------------------------------------------------
GREEN_LOWER = np.array([25, 60, 60])
GREEN_UPPER = np.array([90, 255, 255])

# Physical size of the clover disc, edge to edge. Used to convert pixel
# distances into real inches (for grouping / spread stats).
FACE_DIAMETER_IN = 15.0

# radial scoring rings as (fraction_of_radius, points), checked inner->outer.
# You aim at the black center hub (= the top score). Edit values/boundaries
# to taste; add rows for more rings.
RINGS = [
    (0.15, 6),   # black center hub (aim point)
    (0.45, 5),
    (0.75, 4),
    (1.00, 3),   # rest of the disc, out to the edge
]
MISS = 0


def segment_green(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    return mask


def find_disc(green_mask):
    """Fit the disc over ALL the green paint.

    The black clover fragments the green into several arcs/wedges, so the
    largest single contour is only a piece of the disc. Instead we enclose
    every sizable green fragment together, which recovers the true circle.
    """
    cnts = cv2.findContours(green_mask, cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)[-2:][0]
    biggest = max(cv2.contourArea(c) for c in cnts)
    keep = [c for c in cnts if cv2.contourArea(c) >= 0.05 * biggest]
    allpts = np.vstack(keep)
    (cx, cy), R = cv2.minEnclosingCircle(allpts)
    # disc mask = convex hull of all kept green (spans the enclosed black clover)
    filled = np.zeros(green_mask.shape, np.uint8)
    cv2.drawContours(filled, [cv2.convexHull(allpts)], -1, 255, cv2.FILLED)
    return int(cx), int(cy), int(R), filled


def find_clover_dots(img, disc_mask, cx, cy, R):
    """Black blobs inside the disc = the four clover dots."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, dark = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY_INV)
    dark = cv2.bitwise_and(dark, disc_mask)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, k)
    cnts = cv2.findContours(dark, cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)[-2:][0]
    dots = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < 0.002 * (np.pi * R * R):   # ignore specks
            continue
        (x, y), r = cv2.minEnclosingCircle(c)
        dots.append((int(x), int(y), int(r), a))
    dots.sort(key=lambda d: d[3], reverse=True)
    return dots[:6]


def score_hit(cx, cy, R, x, y):
    d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    frac = d / R
    for f, pts in RINGS:
        if frac <= f:
            return pts
    return MISS


def render(img, cx, cy, R, hits=None, rings=None):
    vis = img.copy()
    # scoring rings, labelled with their point value
    for f, pts in (rings or RINGS):
        cv2.circle(vis, (cx, cy), int(f * R), (255, 255, 255), 1)
        cv2.putText(vis, str(pts), (cx + int(f * R) - 16, cy - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    # center / aim point
    cv2.drawMarker(vis, (cx, cy), (0, 0, 255), cv2.MARKER_CROSS, 16, 2)
    # scored hits, if any were passed in
    for (x, y, pts) in (hits or []):
        cv2.circle(vis, (x, y), 5, (0, 0, 255), 2)
        cv2.putText(vis, str(pts), (x + 6, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
    return vis


def main(path, out):
    img = cv2.imread(path)
    green = segment_green(img)
    cx, cy, R, disc = find_disc(green)
    px_to_in = FACE_DIAMETER_IN / (2.0 * R)
    print(f"disc center=({cx},{cy}) R={R}px  scale={px_to_in:.4f} in/px "
          f"({FACE_DIAMETER_IN}\" face)")
    vis = render(img, cx, cy, R)
    cv2.imwrite(out, vis)
    print("wrote", out)


if __name__ == '__main__':
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else 'res/input/clover_face_crop.png'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'res/output/clover_zones.png'
    main(src, dst)
