# Target Score Detector
A computer vision tool for target shooting score detection and performance analysis.

It has three parts:

1. **`live.py`** — **live camera scorer** for the **Rinehart 18-1 "clover"
   face**. Prop the camera at the target, press `b` to lock onto the clean
   face, then shoot: it finds each new arrow by frame-differencing and scores
   it by ring in real time. Keys: `b` baseline, `c` clear, `q` quit.
2. **`clover_scorer.py`** — score a single still photo of the clover face, and
   the shared geometry/scoring used by `live.py`.
3. **`Driver.py`** — the original video-file analyzer (upstream from
   [Niv-Kor](https://github.com/Niv-Kor/Target-Score-Detector)) for standard
   concentric-ring archery faces.

Clover face = green disc, black 4-lobe clover, black center you aim at; radial
ring scoring around the black center hub.

### Demo video (original):
<a href="https://www.youtube.com/watch?v=0vi2vHIHs0Q&feature=youtu.be">
  <img src="https://i.imgur.com/wLGcPNi.jpg"
       alt="Target Score Detector" width="675" height="377" border="20"
  />
</a>

## Setup (Pop!_OS / Ubuntu / Debian)

```bash
git clone https://github.com/4thehalibit/Target-Score-Detector.git
cd Target-Score-Detector
./install.sh            # creates .venv and installs OpenCV + NumPy
source .venv/bin/activate
```

Dependencies are just `opencv-python` and `numpy` (see `requirements.txt`).

## Live scoring (camera)

`./install.sh` adds a **"Rinehart 18-1 Scorer"** launcher to your apps menu
(clover icon) — just tap it; no terminal needed. You can drag it to the dock.
To (re)install the shortcut on its own: `./make-shortcut.sh`. To launch from a
terminal instead: `./run.sh` (or `./run.sh 1` to pick camera index 1).

Prop the tablet/webcam so it sees the target face straight-on. It auto-locks on
the clean face after a short countdown; on-screen touch buttons control it — no
keyboard required:

- **BASELINE** — lock onto the clean face now (also discards the current end)
- **SAVE END** — record the current end to `score_history.csv`, then reset
- **CAMERA** — cycle to the next connected camera (e.g. a USB webcam)
- **QUIT** — exit

### Scoring history

Tapping **SAVE END** appends one row per shooting end to `score_history.csv`
(next to the scripts): timestamp, arrow count, total, each arrow's score, and
the group spread in inches. Open it in any spreadsheet. The live window also
shows a running **ends / total** for the current session. A typical loop:
auto-lock on the clean face → shoot → **SAVE END** → pull arrows → it re-locks
for the next end.

Under the hood the launcher just runs:

```bash
python live.py            # or: python live.py 1   to pick camera index 1
```

Frame the clean face, press **`b`** to lock the scoring geometry, then shoot.
Detection threshold and arrow-impact estimation are tunable near the top of
`live.py` (`DIFF_THRESH`, `MIN_ARROW_AREA`) — expect to adjust these against the
real target and lighting.

## Scoring a Rinehart 18-1 clover face

Take a **straight-on** photo of the face (camera square to it, disc filling the
frame, even lighting), then:

```bash
python clover_scorer.py your_photo.jpg out.png
```

It finds the disc center + radius, overlays the scoring rings, and writes an
annotated image. Scoring and calibration are configured at the top of
`clover_scorer.py`:

- `FACE_DIAMETER_IN` — real face size (default `15.0`") for inch-based grouping.
- `RINGS` — `(fraction_of_radius, points)` from center outward. Default is
  `6 / 5 / 4 / 3` with a miss = `0`. Edit values or add rows to taste.

## Notes

Two upstream breakages were fixed for modern libraries:
`np.int0` → `np.intp` (removed in NumPy 2.0), and a `draw_meta_data_block`
call corrected to `draw_data_block`.
