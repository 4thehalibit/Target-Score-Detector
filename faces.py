"""
Target face profiles for the live scorer.

Each Face knows two things:
  * detect(frame) -> (cx, cy, R, mask) | None   -- find the face + its area
  * how to score a hit by radial ring (self.rings, self.score)

Add a new single-face target by writing a detector and a rings list, then
appending a Face to FACES. The live scorer's TARGET button cycles FACES.
"""
import cv2
import numpy as np

import clover_scorer as clover


class Face:
    def __init__(self, key, name, rings, diameter_in, detect):
        self.key = key
        self.name = name
        self.rings = rings              # [(fraction_of_radius, points), ...] inner->outer
        self.diameter_in = diameter_in  # physical face size, for spread stats
        self._detect = detect

    def detect(self, frame):
        try:
            return self._detect(frame)
        except Exception:
            return None

    def score(self, cx, cy, R, x, y):
        if not R:
            return 0
        frac = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / R
        for f, pts in self.rings:
            if frac <= f:
                return pts
        return 0


# --- detectors -------------------------------------------------------------

def _detect_clover(frame):
    """Rinehart 18-1 clover: the hi-vis green disc."""
    green = clover.segment_green(frame)
    cx, cy, R, mask = clover.find_disc(green)
    if R < 20:
        return None
    return cx, cy, R, mask


def _detect_standard(frame):
    """Standard round paper face: the dominant circle via Hough transform."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 5)
    h, w = gray.shape
    lo = min(h, w)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=lo,
        param1=120, param2=55,
        minRadius=int(0.15 * lo), maxRadius=int(0.60 * lo))
    if circles is None:
        return None
    x, y, r = np.round(circles[0][0]).astype(int)
    mask = np.zeros((h, w), np.uint8)
    cv2.circle(mask, (int(x), int(y)), int(r), 255, -1)
    return int(x), int(y), int(r), mask


# --- ring definitions ------------------------------------------------------

# Standard 10-ring face: 10 at center dropping to 1 at the edge, equal width.
STANDARD_RINGS = [((i + 1) / 10.0, 10 - i) for i in range(10)]


FACES = [
    Face('clover', 'Clover 18-1', clover.RINGS, clover.FACE_DIAMETER_IN,
         _detect_clover),
    Face('standard', 'Standard 10-ring', STANDARD_RINGS, 40.0 / 2.54,
         _detect_standard),
]


def get(key):
    for f in FACES:
        if f.key == key:
            return f
    return FACES[0]
