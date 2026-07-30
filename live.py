"""
Live camera scorer for the Rinehart 18-1 clover face (v0).

Approach (robust for a fixed / propped camera):
  1. Frame the clean face and press 'b' to set the baseline. We segment the
     green disc to lock the center + radius (the scoring geometry).
  2. Shoot. Each new frame is differenced against the baseline to find newly
     appeared objects (arrows). Each hit is scored by its ring, and the total
     + grouping are drawn live.

Keys:  b = (re)baseline on the clean face   c = clear hits   q/Esc = quit

This is a starting point meant to be tuned against the real target -- arrow
impact estimation (currently the blob centroid) and the diff threshold will
need adjustment once we see it running on the tablet.
"""
import sys
import cv2
import numpy as np

from clover_scorer import (segment_green, find_disc, score_hit, render,
                           RINGS, FACE_DIAMETER_IN)

DIFF_THRESH = 45          # grayscale difference that counts as "changed"
MIN_ARROW_AREA = 60       # px, ignore smaller changed blobs as noise


def find_arrows(baseline, frame, disc_mask):
    """New objects (arrows) inside the disc, as a list of (x, y) impact points."""
    d = cv2.absdiff(cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    _, ch = cv2.threshold(d, DIFF_THRESH, 255, cv2.THRESH_BINARY)
    ch = cv2.bitwise_and(ch, disc_mask)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ch = cv2.morphologyEx(ch, cv2.MORPH_OPEN, k)
    ch = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, k, iterations=2)
    cnts = cv2.findContours(ch, cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)[-2:][0]
    hits = []
    for c in cnts:
        if cv2.contourArea(c) < MIN_ARROW_AREA:
            continue
        M = cv2.moments(c)
        if M['m00'] == 0:
            continue
        hits.append((int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])))
    return hits


def score_frame(frame, baseline, cx, cy, R, disc_mask):
    hits = find_arrows(baseline, frame, disc_mask)
    scored = [(x, y, score_hit(cx, cy, R, x, y)) for (x, y) in hits]
    vis = render(frame, cx, cy, R, scored)
    total = sum(s for _, _, s in scored)
    cv2.putText(vis, f"Arrows: {len(scored)}   Total: {total}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
    return vis, scored, total


def main(cam_index):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"Could not open camera {cam_index}")
        return
    baseline = None
    cx = cy = R = None
    disc_mask = None
    print(__doc__)
    while True:
        ok, frame = cap.read()
        if not ok:
            print("camera read failed")
            break
        if baseline is not None:
            disp, _, _ = score_frame(frame, baseline, cx, cy, R, disc_mask)
        else:
            disp = frame.copy()
            cv2.putText(disp, "Frame the clean face, press 'b' to baseline",
                        (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow('Rinehart 18-1 Live Scorer', disp)
        key = cv2.waitKey(1) & 0xff
        if key in (ord('q'), 27):
            break
        elif key == ord('b'):
            green = segment_green(frame)
            cx, cy, R, disc_mask = find_disc(green)
            baseline = frame.copy()
            px_to_in = FACE_DIAMETER_IN / (2.0 * R)
            print(f"baselined: center=({cx},{cy}) R={R}px "
                  f"scale={px_to_in:.4f} in/px")
        elif key == ord('c'):
            baseline = frame.copy()
            print("hits cleared (re-baselined on current frame)")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(idx)
