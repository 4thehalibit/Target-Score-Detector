# Target Score Detector
A computer vision tool for target shooting score detection and performance analysis.

It has two parts:

1. **`Driver.py`** — the original video analyzer (upstream from
   [Niv-Kor](https://github.com/Niv-Kor/Target-Score-Detector)): tracks arrows
   across the frames of a video against a standard concentric-ring target face
   and overlays score, arrow count, and grouping.
2. **`clover_scorer.py`** — a single-photo scorer for the **Rinehart 18-1
   "clover" face** (green disc, black 4-lobe clover, black center you aim at).
   Radial ring scoring around the black center hub.

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
