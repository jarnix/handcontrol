# Changelog

All notable changes to HandControl. Dates are the day the work landed on the branch.

## Unreleased (v1.1, in development)

### Gestures
- Volume up: open hand, fingers pointing up, repeats while held (default on).
- Volume down: open hand, fingers pointing down (default on, but see Known limitations).
- Bomb: fist held briefly then opened into a flat hand presses the Windows key (off by default).
- Rock-on held opens YouTube in the default browser (off by default).
- Middle finger held presses Win+D, show desktop (off by default).
- Two-finger natural scroll of the focused window (off by default).
- `[gestures].enabled` in the config chooses which gestures run.

### Engine
- Gestures consume a scene of up to two hands; generic hold, repeat and transition gestures plus scene predicates replace bespoke state machines.
- Actions generalised to key taps or chords, wheel scroll and open-URL.
- Hand width (index knuckle to pinky knuckle) is the single motion unit, so thresholds hold at any distance from the camera.

### Finger classifier (measured, not guessed)
- The first rule, a 3-D bend angle of 150 degrees or more from MediaPipe world landmarks, read real open hands as fists on a webcam.
- Replaced by: bend of 130 degrees or more, or, for a hand that is not foreshortened, fingertip 20% farther from the wrist than the knuckle in the image. On three guided recordings the volume-up condition holds on 74-100% of well-framed open-hand frames and 0% of fists.
- The repeat gesture tolerates three misread frames before stopping.

### Tooling
- `--record PATH` logs everything the pipeline sees per frame as JSON Lines.
- `tools/record_poses.py` walks through labelled poses with on-screen prompts, records raw landmarks and snapshots, and compares candidate classifiers.
- GitHub Actions runs the test suite on Windows on every push.

### Known limitations
- MediaPipe cannot track an open hand with the fingers pointing down from a desk webcam, so volume down needs a different pose.
- Two hands pressed palm to palm are edge-on to the camera and rarely both detected; the clap gesture was dropped for that reason.
- The webcam negotiates 1920x1080 whatever resolution is requested; harmless, inference cost barely depends on resolution.

## v1.0 (2026-09-22)

- Tray app with webcam pipeline, MediaPipe hand landmarks, open-palm upward swipe for the Start menu and two-finger scroll.
- Replaced the same day by v1.1 after live testing.
