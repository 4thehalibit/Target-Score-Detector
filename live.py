"""
Live camera scorer for the Rinehart 18-1 clover face (v0).

Approach (robust for a fixed / propped camera):
  1. Frame the clean face. It auto-locks onto the disc after a short countdown
     (or tap BASELINE / press 'b' to do it now).
  2. Shoot. Each new frame is differenced against the baseline to find newly
     appeared objects (arrows). Each hit is scored by its ring, and the total
     is drawn live.

No keyboard needed: tap the on-screen BASELINE / CLEAR / QUIT buttons (the
tablet touchscreen registers taps as clicks). Keys b / c / q still work too.

This is a starting point meant to be tuned against the real target -- arrow
impact estimation (currently the blob centroid) and the diff threshold will
need adjustment once we see it running on the tablet.
"""
import sys
import time
import cv2
import numpy as np

from clover_scorer import (segment_green, find_disc, score_hit, render,
                           RINGS, FACE_DIAMETER_IN)

DIFF_THRESH = 45          # grayscale difference that counts as "changed"
MIN_ARROW_AREA = 60       # px, ignore smaller changed blobs as noise
AUTO_BASELINE_SEC = 3.0   # auto-lock this long after a clean disc is visible

FONT = cv2.FONT_HERSHEY_SIMPLEX
_ui = {'buttons': {}, 'action': None}


def _on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        for name, (x1, y1, x2, y2) in param['buttons'].items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                param['action'] = name


def button_layout(w, h):
    bw, bh, m = min(150, (w - 40) // 3), 44, 10
    y1 = h - bh - m
    return {
        'baseline': (m, y1, m + bw, y1 + bh),
        'clear': (2 * m + bw, y1, 2 * m + 2 * bw, y1 + bh),
        'quit': (3 * m + 2 * bw, y1, 3 * m + 3 * bw, y1 + bh),
    }


def draw_buttons(img, buttons):
    labels = {'baseline': 'BASELINE', 'clear': 'CLEAR', 'quit': 'QUIT'}
    for name, (x1, y1, x2, y2) in buttons.items():
        cv2.rectangle(img, (x1, y1), (x2, y2), (50, 50, 50), -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
        cv2.putText(img, labels[name], (x1 + 12, y1 + 30), FONT, 0.55,
                    (255, 255, 255), 2, cv2.LINE_AA)


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
                (10, 26), FONT, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
    return vis, scored, total


def try_lock(frame):
    """Attempt to find the disc in a frame; return (cx,cy,R,mask) or None."""
    try:
        green = segment_green(frame)
        cx, cy, R, mask = find_disc(green)
        if R < 20:              # too small to be the face
            return None
        return cx, cy, R, mask
    except Exception:
        return None


def _do_baseline(frame):
    lock = try_lock(frame)
    if lock is None:
        print("no clover disc detected yet -- reframe the face")
        return None
    cx, cy, R, mask = lock
    print(f"baselined: center=({cx},{cy}) R={R}px "
          f"scale={FACE_DIAMETER_IN / (2.0 * R):.4f} in/px")
    return (frame.copy(), cx, cy, R, mask)


def open_camera(preferred):
    """Try the preferred index first, then scan others for a working camera."""
    order = [preferred] + [i for i in range(0, 6) if i != preferred]
    for idx in order:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                print(f"using camera index {idx}")
                return cap
            cap.release()
    return None


def main(cam_index):
    cap = open_camera(cam_index)
    if cap is None:
        print("Could not open any camera (tried indices 0-5). "
              "Is another app using it, or is camera permission blocked?")
        return
    win = 'Rinehart 18-1 Live Scorer'
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, _on_mouse, _ui)

    baseline = None
    cx = cy = R = disc_mask = None
    disc_seen_since = None
    print(__doc__)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("camera read failed")
            break
        h, w = frame.shape[:2]
        _ui['buttons'] = button_layout(w, h)

        if baseline is not None:
            disp, _, _ = score_frame(frame, baseline, cx, cy, R, disc_mask)
        else:
            disp = frame.copy()
            lock = try_lock(frame)
            if lock is not None:
                lcx, lcy, lR, _ = lock
                cv2.circle(disp, (lcx, lcy), lR, (0, 255, 255), 2)
                if disc_seen_since is None:
                    disc_seen_since = time.time()
                left = AUTO_BASELINE_SEC - (time.time() - disc_seen_since)
                if left <= 0:
                    _ui['action'] = 'baseline'
                else:
                    cv2.putText(disp, f"Auto-locking in {left:.0f}s "
                                f"(or tap BASELINE)", (10, 26), FONT, 0.7,
                                (0, 255, 255), 2, cv2.LINE_AA)
            else:
                disc_seen_since = None
                cv2.putText(disp, "Point at the clean clover face...",
                            (10, 26), FONT, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

        draw_buttons(disp, _ui['buttons'])
        cv2.imshow(win, disp)
        key = cv2.waitKey(1) & 0xff

        action = _ui['action']
        _ui['action'] = None
        if key == ord('b'):
            action = 'baseline'
        elif key == ord('c'):
            action = 'clear'
        elif key in (ord('q'), 27):
            action = 'quit'

        if action == 'quit':
            break
        elif action == 'baseline':
            res = _do_baseline(frame)
            if res is not None:
                baseline, cx, cy, R, disc_mask = res
            disc_seen_since = None
        elif action == 'clear':
            baseline = None
            disc_seen_since = None
            print("cleared -- will re-lock on the clean face")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(idx)
