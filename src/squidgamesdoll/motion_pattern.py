# motion_analysis.py
import cv2
import numpy as np


def detect_global_motion(Iprev, I, max_corners=200, quality_level=0.01, min_distance=10):
    """
    Estimate the global motion vector between two consecutive frames.

    Steps:
      1. Detect good features to track in Iprev using Shi-Tomasi.
      2. Track these features into I using pyramidal Lucas–Kanade optical flow.
      3. For all successfully tracked points, compute the displacement vectors.
      4. Sort the displacement vectors by their orientation, then select the middle third,
         and finally choose the median (by distance) of that subset as the global motion vector.

    If no features are found or tracked, returns (0, 0).

    Args:
      Iprev: previous frame (grayscale image, numpy array)
      I: current frame (grayscale image, numpy array)
      max_corners: maximum number of features to track.
      quality_level: quality level for feature detection.
      min_distance: minimum distance between features.

    Returns:
      global_motion: tuple (dx, dy) representing the estimated global motion.
    """
    features = cv2.goodFeaturesToTrack(
        Iprev,
        maxCorners=max_corners,
        qualityLevel=quality_level,
        minDistance=min_distance,
    )
    if features is None:
        return (0.0, 0.0)

    features = np.float32(features)
    p1, st, err = cv2.calcOpticalFlowPyrLK(Iprev, I, features, None)

    # Check for valid optical flow output.
    if p1 is None or st is None:
        return (0.0, 0.0)

    st = st.flatten()
    # Reshape features to have shape (-1,2)
    features = features.reshape(-1, 2)
    good_old = features[st == 1]
    good_new = p1[st == 1].reshape(-1, 2)

    if len(good_old) == 0 or len(good_new) == 0:
        return (0.0, 0.0)

    displacements = good_new - good_old  # Expected shape: (n, 2)

    if displacements.size == 0 or displacements.shape[1] < 2:
        return (0.0, 0.0)

    # Compute angles from the displacements.
    angles = np.arctan2(displacements[:, 1], displacements[:, 0])

    # Sort displacement vectors by angle.
    sort_idx = np.argsort(angles)
    displacements_sorted = displacements[sort_idx]

    m = len(displacements_sorted)
    m_third = m // 3
    if m_third == 0:
        global_disp = np.median(displacements, axis=0)
    else:
        mid_section = displacements_sorted[m_third : 2 * m_third]
        mags_mid = np.linalg.norm(mid_section, axis=1)
        median_idx = np.argsort(mags_mid)[len(mags_mid) // 2]
        global_disp = mid_section[median_idx]

    return (float(global_disp[0]), float(global_disp[1]))


def track_candidates(Lprev, Iprev, I):
    """
    Track candidate detections from the previous frame into the current frame.

    Uses pyramidal Lucas–Kanade optical flow.

    Args:
      Lprev: list of candidate dictionaries from the previous frame.
             Each candidate must have a 'position' key with a tuple (x, y).
      Iprev: previous frame (grayscale image)
      I: current frame (grayscale image)

    Returns:
      tracked_positions: list of positions (as (x, y) tuples) corresponding to candidates
                         in Lprev. If a candidate is not successfully tracked, the corresponding
                         entry is None.
    """
    if not Lprev:
        return []

    pts_prev = np.array([cand["position"] for cand in Lprev], dtype=np.float32)
    pts_prev = pts_prev.reshape(-1, 1, 2)

    pts_cur, st, err = cv2.calcOpticalFlowPyrLK(Iprev, I, pts_prev, None)

    tracked_positions = []
    for status, pt in zip(st, pts_cur):
        if status[0] == 1:
            tracked_positions.append((float(pt[0][0]), float(pt[0][1])))
        else:
            tracked_positions.append(None)
    return tracked_positions


def motion_pattern_analysis(L, Lprev, I, Iprev, C1=2.0, C2=0.2, assoc_thresh=10.0, fixed_object=False):
    """
    Analyze the motion pattern of detected candidates to compute temporal weights.

    For each candidate in the current set L:
      - If a candidate from the previous frame Lprev is successfully tracked, the displacement
        vector is computed as the difference between the current candidate position and its previous
        position.
      - Otherwise, for non-associated (or new) candidates, the displacement vector is set to the
        global motion vector (or to zero in fixed-object applications).

    Then, for each candidate, the normalized aberration is computed as:

         d_i = || c_i - g || / d_max,

    where d_max is the maximum aberration over all candidates. Finally, the temporal weight is:

         t_i = C1 * d_i * w_i   if d_i > 0,
         t_i = C2 * w_i         if d_i = 0.

    In applications where the laser pointer marks a fixed object, set fixed_object=True.
    In that case, you might set the displacement vector of untracked candidates to zero so that
    candidates that match the global motion (or remain static) are favored.

    Args:
      L: current frame candidate list (list of dicts with keys 'position' and 'weight')
      Lprev: previous frame candidate list (same format as L)
      I: current frame (grayscale image)
      Iprev: previous frame (grayscale image)
      C1: constant factor for candidates with nonzero aberration (typical range [2,4])
      C2: constant factor for candidates with zero aberration (typical range [0.1,0.3])
      assoc_thresh: maximum distance (in pixels) to associate a candidate in L with a tracked candidate from Lprev.
      fixed_object: if True, untracked candidates are assumed to mark a fixed object and can be set to zero displacement.

    Returns:
      temporal_weights: list of temporal weight values for candidates in L.
      best_candidate: the candidate (dict) with the highest temporal weight.
    """
    # 1. Estimate global motion vector g.
    g_dx, g_dy = detect_global_motion(Iprev, I)
    global_motion = np.array([g_dx, g_dy], dtype=np.float32)

    # 2. Track previous candidates.
    tracked_positions = track_candidates(Lprev, Iprev, I)

    # Build list of (prev_position, tracked_position) for successfully tracked candidates.
    tracked_candidates = []
    for cand, tracked in zip(Lprev, tracked_positions):
        if tracked is not None:
            tracked_candidates.append(
                (
                    np.array(cand["position"], dtype=np.float32),
                    np.array(tracked, dtype=np.float32),
                )
            )

    # 3. For each candidate in L, compute the displacement vector c.
    motion_vectors = []
    for cand in L:
        pos_current = np.array(cand["position"], dtype=np.float32)
        best_dist = float("inf")
        best_prev = None
        # Find the best matching tracked candidate.
        for prev_pos, tracked_pos in tracked_candidates:
            dist = np.linalg.norm(pos_current - tracked_pos)
            if dist < best_dist:
                best_dist = dist
                best_prev = prev_pos
        if best_dist < assoc_thresh and best_prev is not None:
            # Candidate is associated; displacement vector is current - previous.
            c_vec = pos_current - best_prev
        else:
            # Candidate not associated.
            if fixed_object:
                # For fixed-object applications, you might set the displacement to zero.
                c_vec = np.array([0.0, 0.0], dtype=np.float32)
            else:
                # Otherwise, use the global motion vector.
                c_vec = global_motion.copy()
        motion_vectors.append(c_vec)

    # 4. Compute aberrations: d_i = || c_i - g || for each candidate.
    diffs = [np.linalg.norm(c_vec - global_motion) for c_vec in motion_vectors]

    # Determine d_max over all candidates (if all zero, d_max remains 0).
    if diffs:
        d_max = max(diffs)
    else:
        d_max = 1.0  # to avoid division by zero in degenerate cases

    # 5. Compute normalized aberration and temporal weight.
    temporal_weights = []
    for cand, d in zip(L, diffs):
        w_i = cand["weight"]
        # Normalize the aberration.
        if d_max > 0:
            d_norm = d / d_max
        else:
            d_norm = 0.0
        if d_norm > 0:
            t_i = C1 * d_norm * w_i
        else:
            t_i = C2 * w_i
        temporal_weights.append(t_i)

    # 6. (Optional) Sort candidates based on temporal weight and select best candidate.
    if temporal_weights:
        best_index = np.argmax(temporal_weights)
        best_candidate = L[best_index].copy()
        best_candidate["temporal_weight"] = temporal_weights[best_index]
    else:
        best_candidate = None

    return temporal_weights, best_candidate


# ---------------------
# Example usage:
# ---------------------
if __name__ == "__main__":
    # For testing, load two consecutive frames.
    Iprev = cv2.imread("frame_prev.jpg", cv2.IMREAD_GRAYSCALE)
    I = cv2.imread("frame_curr.jpg", cv2.IMREAD_GRAYSCALE)
    if Iprev is None or I is None:
        print("Error: Could not load test frames.")
        exit(1)

    # Example candidate lists.
    # In practice, these come from your detection module.
    Lprev = [
        {"position": (100, 150), "weight": 5},
        {"position": (200, 250), "weight": 4},
    ]
    L = [
        {"position": (105, 155), "weight": 6},
        {"position": (210, 260), "weight": 3},
        {"position": (400, 300), "weight": 2},
    ]

    # Set parameters.
    C1 = 3.0  # e.g., between 2 and 4
    C2 = 0.2  # e.g., between 0.1 and 0.3
    assoc_thresh = 10.0  # pixels

    temporal_weights, best_candidate = motion_pattern_analysis(L, Lprev, I, Iprev, C1, C2, assoc_thresh)
    print("Temporal weights for current candidates:")
    for i, t in enumerate(temporal_weights):
        print(f"Candidate {i+1}: temporal weight = {t}")

    if best_candidate is not None:
        print("\nBest candidate (detected laser spot):")
        print(best_candidate)
    else:
        print("No valid candidate detected.")
