# Independent laser targeting: review and implementation plan

Reviewed 2026-10-11. This is a source review and an experiment plan, not a demonstrated targeting solution. No camera, emitter, or ESP32 was exercised. Application and firmware behavior remain unchanged.

## Recommendation

First build a standalone, recorded-video experiment that identifies a deliberately switched laser spot on a matte board. Use native-resolution temporal differencing, timestamped frames, and long on/off plateaus. Prove detection and emitter shutdown before integrating aiming into the game. Then combine calibrated coarse aiming with visual feedback. Training another full-frame detector should follow measured failures of this experiment.

Hardware context: inexpensive AliExpress red or green emitter; switching speed is adjustable; camera frame rate may vary; electrical behavior during ESP32 failure is unknown. Do not assume the two colors, module types, or power circuits have identical switching behavior.

Confirmed game requirement: the user describes the emitters as low power and intends to mark the chest of eliminated players. Chest targeting is the implementation objective; board and clothed mannequin tests are development stages. Actual optical output and electrical failure behavior remain unmeasured.

Confirmed compute constraint: keep the existing Jetson, webcam, ESP32, and servos; add no hardware. The first implementation must retain the existing YOLO/ByteTrack pipeline as its only neural workload. Pose, monocular depth, second cameras, and replacement actuators discussed below are comparisons or possible later alternatives, not part of the authorized baseline.

## How the current game works

| Layer | Actual responsibility |
| --- | --- |
| `run.py`, `game_settings.py`, `config_phase.py` | Select platform/backend, load configuration, set up vision/start/finish areas. |
| `game_camera.py` | Capture webcam frames; preserve an original frame; mask and crop the vision area, optionally enhance contrast/brightness, and resize a separate player inference frame. Return crop metadata. |
| `player_tracker_ul.py` | Ultralytics person detection and persistent ByteTrack IDs; select PyTorch/ONNX/TensorRT models. |
| `player_tracker_hailo.py` | Hailo inference and Supervision ByteTrack alternative. |
| `face_extractor.py` | MediaPipe face detection and portrait extraction/cache. This is not biometric recognition or identity recovery after a track-ID switch. |
| `player.py` | Store track ID, bounding box, portrait, visibility, last-seen time, movement reference, elimination/winner state. |
| `squid_game.py` | Registration, phase timing, movement elimination, winner checks, audio, display, doll commands, and optional laser sequence. |
| `laser_finder.py`, `laser_finder_nn.py` | Classical spot detection or pretrained YOLOv5 laser detection. |
| `laser_tracker.py`, `laser_shooter.py` | Intended detector/controller coordination and TCP ESP32 communication. |
| `esp32/tracker.py`, `esp32/Servo.py` | GPIO laser switching, servo PWM, doll head/eyes, command server. |

Registration lasts 15 seconds and waits until at least one player registers. Players need a face and intersection with the start area. Green light updates movement references. Red light has a 0.5-second grace period; movement is displacement of the detected bounding-box center against the stored reference, not optical flow or skeletal motion. The default threshold is 15 pixels in the current player coordinate space. A player unseen for more than 60 seconds can also be eliminated. Finish-area intersection can mark a non-eliminated player as a winner. All players resolved produces victory or game over.

Player coordinates originate in the cropped/resized inference frame, despite comments in `Player` describing original webcam dimensions. The game already transforms them for start/finish checks. Targeting must explicitly do the same transformation.

## Source findings that block targeting

1. **Tracking does not run:** `LaserTracker.shall_run` starts false and `start()` never sets it true. The worker exits without entering its loop.
2. **Aiming is unimplemented:** the loop only detects/annotates; it never calls a aiming method, checks arrival, or sets `_shot_done` true. Existing shooter PID code is not connected to elimination.
3. **Coordinate mismatch:** `Player.get_target()` returns inference-frame coordinates. `LaserFinderNN` returns purported full-frame coordinates, but its NN-frame path merely multiplies by full-frame/inference dimensions. It ignores the crop origin and crop size. Comparing these outputs cannot work reliably.
4. **Elimination blocks the game:** the five-second inner loop captures frames but does not update player tracks, render the normal display, or handle events. The target becomes stale; further eliminations are serialized through this delay.
5. **Firmware starts in test mode:** `main()` enables `test_movement()` and `rotate_head()`; `run_tracking()`, `head_positionning()`, and `pulse_eyes()` are not scheduled. Commands can be acknowledged without the commanded tracking movement taking place. Even the unused tracking loop randomly jitters when idle.
6. **Laser commands disagree:** the host sends uppercase `ON`/`OFF`; firmware accepts lowercase `on`/`off`. `_send_msg()` ignores the acknowledgement content. Several caught socket errors also fall through to a successful return. A reported shutdown is therefore not proof of shutdown.
7. **No dependable failure shutdown:** the firmware treats high GPIO as off, but the module wiring is unverified. There is no communication watchdog that forces the emitter off. Boot/reset/high-impedance GPIO behavior and separate emitter power require physical investigation.
8. **Thread/socket handling needs redesign:** frames and targets have no atomic snapshot, frame ID, timestamp, or lock. The worker could reprocess an old frame repeatedly. Doll and laser commands share a socket without transaction serialization. TCP reads are treated as whole messages even though TCP can split/coalesce them.
9. **Calibration is insufficient:** `Calibrator` is an older four-corner workflow using a different camera API. `compute()` mixes axis indices and does not advance its previous point. Fixed pixels-per-degree values cannot describe the whole offset/depth-dependent geometry.
10. **Physical resolution is coarse:** `Servo.__angle_to_u10_duty()` converts angle to integer duty using roughly 98 counts across 180 degrees. The effective command increments are roughly 1.8 degrees; at 10 m, that angular step corresponds to about 32 cm near perpendicular incidence. Two decimal places in the angle command do not provide two-decimal mechanical precision. Measure real repeatability before tuning control; finer PWM or a different actuator may be necessary.

The older `LASER-NATIVE-FLOAT-REWRITE.md` proposal incorrectly equates normalized camera coordinates with servo position. Normalization is useful for API consistency; it does not remove calibration, parallax, or depth ambiguity.

## Why current dot detection struggles

The classical detector thresholds the red channel, which also responds to white highlights, then dilates four times and searches for circles with a narrow radius range. It requires essentially one candidate. A real spot may be tiny, clipped white, irregular on fabric, motion blurred, or weaker than ambient highlights. Color is useful evidence, but cannot uniquely identify the emitter.

The NN path uses the enhanced, downsampled player frame when supplied. Tiny spots can disappear during resizing, and enhancements alter their appearance. Selecting the highest-confidence detection does not establish that it is this device's spot. The external pretrained model is a useful baseline, not evidence of accuracy in this venue.

Two inspected repository images illustrate the limitations of the available examples: `laser-1.jpg` depicts a conspicuous spot with a beam-like line; `laser-8.png` has an AI watermark and a bright facial spot. Neither establishes performance on raw webcam video at game distances. The existing real-model test skips on broad exceptions, so a skip is not a successful detection benchmark.

## Detection experiment: variable FPS without exact synchronization

Control the signal that the camera is looking for. This is the proposed engineering experiment, not a claimed validated result.

1. Hold the servos stationary. Lock exposure, gain, white balance, and focus where the camera supports it; verify those settings actually take effect. Choose exposure short enough to avoid widespread clipping while retaining adequate player visibility. Record native frames with monotonic receive timestamps, frame IDs, camera settings, host command/ack timestamps, and ESP32 sequence/state information. Prefer capture timestamps when available: host receive time alone does not reveal sensor exposure time.
2. Begin with off/on/off plateaus of approximately 300–500 ms, adjusted to the measured frame rate and buffering. These are initial experiment settings, not guaranteed optimal values. Require multiple usable frames in each plateau; lengthen plateaus or reject incomplete cycles during frame-rate drops.
3. An acknowledgement confirms the command was processed, not that a particular camera frame saw it. Measure emitter turn-on/off delay, camera buffering, and jitter empirically. Exclude transition frames with a conservative delay margin. Flush/drain stale capture buffers through continuous capture; do not just timestamp an old buffered frame as fresh.
4. Compute a robust off reference from neighboring off plateaus. Compare the on plateau to that reference in signed floating-point channel values. Local background removal and motion compensation reduce broad lighting changes and moving edges. Start with a stationary board before attempting moving fabric.
5. Extract small connected bright components; score differential brightness, local contrast, plausible size, and color excess. Accept white saturated centers if they have the expected temporal change. Do not require a perfect circle or a fixed radius.
6. Confirm the candidate disappears in the following off plateau and recurs in additional cycles. Later, use a known non-periodic binary pattern and correlate intensities with delayed command states. Estimate the delay from data; avoid a single fixed blinking frequency that may alias or coincide with room lighting.
7. Return raw full-frame coordinates, confidence, frame/cycle timestamps, ambiguity, and candidate list. No new observation must never be treated as a new successful detection. Preserve raw observations for control and diagnostics; smoothing belongs in a timestamp-aware estimator.

At low FPS, several plateaus necessarily introduce significant latency. Measure that tradeoff rather than promising sub-second acquisition. If movement destroys differencing or latency is too high, consider hardware-triggered capture and timed modulation, or a dedicated fixed observation camera. A second camera needs its own calibration; adding one does not solve correspondence by itself.

The emitter's GPIO polarity and rise/fall behavior must be measured for each module. A cheap green module may behave differently from a red diode module; nominal marketing labels are not timing specifications. Start at unchanged optical power. A narrowband filter on a dedicated spot camera is an optional experiment only after measuring wavelength and signal/background contrast; putting it on the player camera may degrade person detection.

## Geometry for a device away from the webcam

One image pixel specifies a viewing ray, not a unique point in space. With a camera/laser baseline, objects on that ray at different depths require different laser angles. A normalized `(x, y)` or a single wall calibration cannot resolve that ambiguity.

Use one explicit full-frame coordinate system for both the player observation and spot observation:

```text
x_full = crop_x + x_inference * crop_width / inference_width
y_full = crop_y + y_inference * crop_height / inference_height
```

If additional letterboxing is introduced, account for that padding too. Keep raw camera image transforms separate from display scaling.

For chest targeting, use person pose landmarks and, where useful, segmentation to define an interior torso region, rather than relying only on the existing bounding-box point at one-third height. Shoulders and hips can define the torso, but uncertain or occluded landmarks must invalidate the target. Track the region by the eliminated player's ID and update it as the person moves or turns.

Use metric depth/stereo or a constrained known plane to obtain coarse aiming. Then correct residual error using a spot visible in the same camera. Monocular learned depth can provide a hypothesis, but scale and uncertainty must be measured; it should not be the sole basis for precise open-loop aiming. A floor homography can help estimate location from a ground-contact point, but does not directly map a chest point: torso height, posture, and camera geometry are additional unknowns.

First validate on a clothed mannequin at several positions and depths. Include dark, red, patterned, and reflective fabrics and partial occlusion. A chest target must be visible from both camera and emitter; another player can obstruct the emitter even when the webcam sees the target clearly. If available, a camera near the emitter can help verify its view, but requires calibrated correspondence to the main camera's player ID.

Visual feedback can correct an offset mount without a complete depth model while a suitable spot is visible. However, matching spot and player pixels does not prove they are on the same physical surface: a background spot can line up in the image. Occlusion, mount-side visibility, depth, and surface constraints still matter.

For feedback on test surfaces, measure a local 2×2 Jacobian relating small pan/tilt changes to image displacement. This handles axis sign, cross-coupling, and local scale better than two global constants. Use bounded proportional corrections based on this Jacobian, allow settling, and consume only new valid observations. Estimate across a calibration grid and depth range. Introduce integral/derivative control only if measurements justify it.

### Ground calibration versus neural depth

A checkerboard with measured square size can establish camera pose relative to a flat floor, together with camera intrinsics. It need not remain under each player after calibration if the camera and floor relationship stays fixed. Several measured floor markers spread across the play area can also provide planar correspondences. A visible foot contact point can then be mapped into metric floor coordinates; ankle landmarks or a bounding-box bottom are only estimates of that contact point. Feet hidden by other players invalidate this estimate.

For an upright player, use that ground position as an approximate torso range and intersect the camera's chest viewing ray with a plausible vertical plane through the player. This is a coarse initialization: leaning, turning, and foot/torso offsets introduce error. It does not require knowing every player's exact height, but does require calibrated camera geometry and a defensible plane estimate.

Pose estimation is the most directly useful NN addition: locate shoulders, hips, and ankles and track a chest region. Metric monocular depth is a second candidate for coarse initialization when feet are obscured. Standard relative-depth output is not distance in meters; use a metric model and validate range error and temporal stability on venue recordings. Compare the indoor metric Depth Anything V2 baseline with ground-derived estimates before adopting it. Depth Pro is another research baseline; its published runtime is not a runtime guarantee on this project's hardware.

The fast loop should not wait for a full depth network on every correction. Run person/pose/range estimation at a sustainable rate and run native-resolution spot observations in a smaller ROI as quickly as capture and emitter timing allow. On test surfaces, define image error `e = chest_target - observed_spot` and update angles with a bounded, damped Jacobian correction `delta_angles = gain * pseudoinverse(J) * e`. Apply only to fresh observations after the preceding command has settled. Update the local Jacobian from accepted command/spot displacement pairs; reject pairs spanning target-surface changes, occlusion, or ambiguous detections. Depth primarily improves the first placement and local gain estimate; observed error provides the correction.

Temporal acquisition and precision tracking can use different observation windows. Use several on/off plateaus to establish which spot belongs to the emitter, then evaluate shorter modulation windows and local association for tracking. Continuous-on tracking may reduce identification overhead, but loses temporal confirmation and must expire promptly on ambiguity. Measure capture-to-command-to-settle latency and missed observations before selecting either mode. Higher detector FPS cannot overcome stale buffered frames or slow actuator response.

Closed-loop control cannot remove the present PWM quantization floor, backlash, or actuator deadband. Investigate finer pulse-width APIs supported by the exact MicroPython board/firmware and measure actual effective resolution. Do not use rapid angle dithering to claim a precise stationary spot: it can alternate between two visibly separated positions. Accept a stable interior chest region rather than an unnecessarily exact pixel, and measure whether actuator resolution supports that region across the full play distance.

## Shutdown investigation

Perform these tests with the beam contained on a matte board and no people in its path. Record both optical output and relevant supply/GPIO behavior; an LED status or software acknowledgement alone is insufficient.

| Test | Question to answer |
| --- | --- |
| Explicit off command | Is off accepted, how long until optical output stops, and is high GPIO actually off? |
| Host termination / Wi-Fi loss | Does the controller disable output within a measured bounded timeout? |
| ESP32 reset / watchdog / brownout | Does output remain off during boot and high-impedance pin states? |
| Remove ESP32 power while emitter remains powered | Can the emitter turn on due to floating input, module defaults, or power backfeed? |
| Disconnect control wire / restore power | Is the default electrical state off? |

Implement a verified default-off hardware drive and firmware watchdog. Firmware cannot guarantee shutdown when it has lost power or execution. Design pull resistors and switching circuitry according to the actual active-high/active-low module; do not prescribe polarity before measuring it. Require an explicit arm after reconnect/reset and do not resume emission automatically.

The README's suggestion that a 5 mW green laser is safer for eyes is unsupported and should be corrected separately. FDA guidance says not to direct laser pointers at people. The user's intended effect is chest targeting; a low-power description alone does not establish exposure conditions. Software face masking does not guarantee the beam avoids eyes from the emitter's different viewpoint. Validate geometry and shutdown on boards and mannequins before any live deployment.

## Implementation sequence and acceptance gates

### Compute budget with the existing Jetson

`JETSON_ORIN.md` documents YOLO11l TensorRT at 47.1 ms inference, approximately 20 ms tracking, and 68–72 ms total processing (14–16 FPS). YOLO11n is documented at 25–40 ms total. These are explicitly Orin measurements; the README and platform utility mix Nano/Orin names, and the utility only tests for a Tegra installation. Do not treat the documented numbers as original Jetson Nano benchmarks or proof of the currently deployed model. The source game loop also explicitly caps itself at 15 FPS.

Baseline architecture under the user's constraint:

- Capture once continuously. Publish latest raw frame metadata and a resized inference view; do not open the same webcam separately for each worker or accumulate frame queues.
- Keep one GPU YOLO/ByteTrack worker at its sustainable current cadence. Reuse its boxes and identities. Do not load the separate YOLOv5l6 laser model for this mode.
- Initially define a conservative chest region from the existing person box; this is approximate and fails on some poses. Optional sparse optical flow on a small torso patch can update translation between detections, with limited lifetime, confidence checks, and reset on each new detection. It does not create fresh ByteTrack identity observations.
- Use native-resolution CPU ROI subtraction, thresholding, and connected components for spot feedback; start with a patch around the last validated spot and expand only within a bounded acquisition region if necessary. Initial acquisition may need a larger region than tracking because the coarse aim can miss the chest. A 160×160 patch is about 1.2% of a 1920×1080 frame, but this pixel ratio is not a measured runtime speedup.
- Ground calibration is performed during setup. Runtime planar transforms and coarse aiming lookup/interpolation are small arithmetic workloads. Approximate feet from the bottom of a visible person box initially; record uncertainty rather than claiming pose-quality ground contact.
- A single device-I/O owner handles short bounded command transactions, separate from capture and UI. CPU workers still contend with tracking and frame preprocessing; threads provide scheduling separation, not extra compute capacity. Benchmark with the full game running.

Prioritize raw frame age and end-to-end correction latency over moving small ROI operations onto CUDA. Existing CUDA helpers can introduce transfers and compete with person inference. CPU OpenCV is the first baseline; optimize only measured hotspots. Avoid repeated full-frame copies, debug annotation, and full-frame Hough searches in the correction path.

The existing host exposes a nominal 10 Hz shooter frequency and the unused firmware tracking loop sleeps 100 ms after commands; these require review when setting cadence. Neither a 30 FPS webcam nor a fast ROI detector establishes 30 Hz settled servo correction. Preserve elimination detection cadence and rules while optimizing targeting; skipping YOLO frames indiscriminately could miss brief violations.

### Responsiveness requirement

The user requires a prompt chest marker: small player movements must not make acquisition obsolete. The existing five-second targeting pause is unsuitable. The 300–500 ms plateaus above are diagnostic settings for proving signal visibility and timing, not the production targeting cadence.

Maintain player/pose tracking continuously before elimination. Cache current chest regions, approximate range, velocity, observation age, and calibrated coarse aiming predictions for each player. On elimination, select the latest valid prediction immediately; do not load a model, recalibrate, or start a long depth inference job. Refresh the target throughout acquisition. Physical prepositioning with the emitter off is optional and only useful if choosing a likely next target actually reduces measured onset time.

Use a dedicated continuous capture path and latest-frame handoff, with no accumulating processing queue. The laser observer should consume raw native-resolution ROIs, separately from the downsampled player inference path. Model selection and inference cadence must leave processing capacity for capture, observation, control, and UI. Slow range estimates can update asynchronously; stale or uncertain tracks must be rejected rather than silently reused.

Predict chest position at the estimated time the commanded servo movement will take effect, using recent velocity and measured capture/network/settling delay. Prediction only compensates moderate smooth motion; sudden direction changes, ID ambiguity, and occlusion still require reacquisition or abort. Confirm a region hit using fresh observations rather than chasing an exact chest-center pixel.

Provisional targets for bench validation: first valid marker within 300 ms of elimination, followed by fresh correction observations approximately every 33–67 ms where actual capture and actuator behavior permit it. These are desired acceptance targets, not measured capabilities or a guarantee that the current hardware can meet them. For context, 0.5 m/s torso motion causes 5 cm displacement during 100 ms of delay. A camera delivering 15 FPS already has a 67 ms frame interval before buffering, inference, networking, and settling are added.

Record elimination-to-first-valid-marker latency, capture-to-settled-correction latency, percentile jitter, and time inside a moving chest-sized test region. Test smooth motion and sudden changes on a moving clothed target. If temporal confirmation cannot meet the latency target, evaluate shorter identified modulation windows, higher-rate capture, or hardware-triggered observation. If actuator resolution or settling cannot meet it, change the PWM driver/actuator. A NN upgrade alone cannot remove those bottlenecks.

1. **Establish hardware behavior.** Correct protocol casing, parse acknowledgements, frame requests/responses reliably, bound transaction time, serialize communication, disable firmware test motion, remove idle jitter, and add watchdog/default-off behavior. Investigate PWM resolution and bidirectional mechanical repeatability. Gate: command execution and shutdown physically verified, including independent power loss.
2. **Build capture/replay and temporal detection.** Keep this independent of the game, person inference, and NN downloads. Record raw frames plus sidecar state/timing metadata. Compare temporal detection against the classical and pretrained baselines using annotated recordings. Gate: separately report recall, false acceptance in laser-off/decoy scenes, pixel localization error, acquisition latency, and invalid cycles across actual lighting, distances, and frame-rate drops.
3. **Calibrate on boards and clothed mannequins.** Measure camera distortion, mount geometry, reachable region, actuator direction, response delay, backlash, and command resolution. Use many samples and held-out chest positions at several depths. Gate: repeatable targeting error fits within the chosen interior torso region and spot detection works on representative clothing; do not infer precision from PWM command decimal places.
4. **Implement a controller state machine.** Suggested states: IDLE, COARSE_AIM, SETTLE, ACQUIRE, CORRECT, CONFIRM, COMPLETE, ABORT. Use frame snapshots and cancellation rather than a busy loop; one owner handles device transactions. Timeout, stale frame, ambiguous spot, lost target, disconnect, or invalid calibration aborts and disables output. Require several fresh successful observations before completion.
5. **Integrate nonblocking elimination.** Queue an event by player ID; continue camera capture, player tracking, rendering, and event handling. Resolve the target from its latest fresh track every cycle. Treat tracking-ID changes and occlusion as uncertainty rather than recovering identity from a stored portrait. Do not target a player eliminated only because their last-known track expired. Cancellation on green light, restart, exit, and exceptions must be explicit.
6. **Evaluate whether AI training is needed.** Label real spot-on/off recordings and difficult negatives. Split by recording session/lighting/surface, not adjacent frames. Consider a small classifier on native-resolution differential candidate patches or a temporal model before another full-frame YOLO model. AI can reject ambiguous components; it cannot reconstruct an optically absent signal.

Provisional performance goals should be set after the first recording session. Report percentile latency and failure rate, not only average FPS or cherry-picked successful images. Reserve sub-second acquisition as a later target if the measured camera/emitter timing supports it.

Focused software checks should cover crop/resize round trips, variable-timing replay, missing/duplicate frames, saturated spots, multiple candidates, false reflections, acknowledgement failures, cancellation and watchdog behavior. Hardware measurements are required for optical shutdown, settling, backlash and accuracy; mocks cannot establish those properties.

## References

- [OpenCV homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html): planar geometry and limits of planar mappings.
- [ADVRHumanoids laser tracking repository](https://github.com/ADVRHumanoids/nn_laser_spot_tracking) and [model release](https://zenodo.org/records/10471835): provenance of the existing neural baseline.
- [Depth Anything V2 metric models](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth) and [Depth Pro](https://github.com/apple-aiml-research/ml-depth-pro): candidate monocular metric-depth baselines for coarse initialization; neither has been benchmarked in this project.
- [Target Detection Based on Variable Frame Rate Sampling of Active Light Source](https://www.jstage.jst.go.jp/article/jaciii/26/1/26_83/_pdf): related primary research on modulated active-light detection. That paper deliberately controls camera sampling and emitter switching together; it does not establish tolerance to an unsynchronized webcam's variable FPS. The plateau/timestamp experiment above is our proposal for that constraint.
- [FDA: Illuminating Facts About Laser Pointers](https://www.fda.gov/radiation-emitting-products/alerts-and-notices/illuminating-facts-about-laser-pointers): direct exposure guidance.
