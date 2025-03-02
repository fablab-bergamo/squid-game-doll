import cv2
import numpy as np

# Generato da https://www.mdpi.com/1424-8220/14/11/20112 con ChatGPT


def compute_gradients(image):
    """
    Compute the gradients of the input image using Sobel operators.
    Returns:
      - mag: gradient magnitude (float32)
      - angle: gradient orientation in radians (float32)
    """
    # Compute gradients in x and y directions.
    grad_x = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)

    # Compute magnitude and angle (in radians)q
    mag, angle = cv2.cartToPolar(grad_x, grad_y, angleInDegrees=False)
    return mag, angle


def accumulate_candidates_vectorized(mag, angle, R, Th):
    """
    Create an accumulator image using vectorized operations.
    For every pixel (x,y) with gradient magnitude > Th, a vote is added
    to each candidate center computed along the gradient direction for radii 1...R.

    Args:
      mag: gradient magnitude (2D numpy array)
      angle: gradient orientation (2D numpy array, in radians)
      R: maximum expected radius (integer)
      Th: magnitude threshold (float)

    Returns:
      acc: accumulator array (same shape as input image, dtype=uint32)
    """
    height, width = mag.shape
    acc = np.zeros((height, width), dtype=np.uint32)

    # Find indices of pixels where the gradient magnitude exceeds the threshold.
    ys, xs = np.where(mag > Th)
    if len(xs) == 0:
        return acc  # No votes if no pixel passes threshold.

    # Get corresponding gradient angles.
    valid_angles = angle[ys, xs]

    # For each radius from 1 to R, compute candidate positions and vote.
    for r in range(1, R + 1):
        # Compute offset for each valid pixel
        offset_x = np.round(r * np.cos(valid_angles)).astype(np.int32)
        offset_y = np.round(r * np.sin(valid_angles)).astype(np.int32)

        candidate_x = xs + offset_x
        candidate_y = ys + offset_y

        # Filter out indices that fall outside the image boundaries.
        valid = (
            (candidate_x >= 0)
            & (candidate_x < width)
            & (candidate_y >= 0)
            & (candidate_y < height)
        )
        candidate_x = candidate_x[valid]
        candidate_y = candidate_y[valid]

        # Use numpy’s advanced indexing with np.add.at to accumulate votes.
        np.add.at(acc, (candidate_y, candidate_x), 1)

    return acc


def group_candidates(candidates, group_radius=5):
    """
    Group nearby candidates that are within group_radius pixels.
    Merges candidates by computing the weighted average of their positions and
    summing their weights.

    Args:
      candidates: list of candidate dicts {'position': (x,y), 'weight': weight}
      group_radius: maximum distance for candidates to be considered overlapping.

    Returns:
      grouped: list of grouped candidate dicts.
    """
    grouped = []
    candidates = candidates.copy()  # shallow copy of list
    while candidates:
        # Pop the first candidate.
        base = candidates.pop(0)
        bx, by = base["position"]
        cluster = [base]
        remain = []
        for cand in candidates:
            cx, cy = cand["position"]
            if np.hypot(cx - bx, cy - by) <= group_radius:
                cluster.append(cand)
            else:
                remain.append(cand)
        candidates = remain

        total_weight = sum(c["weight"] for c in cluster)
        if total_weight == 0:
            avg_x, avg_y = bx, by
        else:
            avg_x = sum(c["position"][0] * c["weight"] for c in cluster) / total_weight
            avg_y = sum(c["position"][1] * c["weight"] for c in cluster) / total_weight
        grouped.append(
            {"position": (int(round(avg_x)), int(round(avg_y))), "weight": total_weight}
        )
    # Optionally, sort the grouped candidates by weight.
    grouped = sorted(grouped, key=lambda c: c["weight"], reverse=True)
    return grouped


def detect_laser_spots(image, R=10, Th=20):
    """
    Detect candidate laser spot centers in the input image using vectorized operations.

    Args:
      image: input grayscale image (numpy array)
      R: maximum expected radius of the laser spot
      Th: threshold on gradient magnitude

    Returns:
      candidates: a list of dictionaries with keys:
           'position': (x,y) tuple,
           'weight': candidate weight.
      The list is sorted in descending order of weight.
      acc: the accumulator image.
    """
    # Ensure the image is grayscale and float32.
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    gray = np.float32(gray)

    # Step 1: Compute gradients.
    mag, angle = compute_gradients(gray)

    # Step 2: Create accumulator space using vectorized accumulation.
    acc = accumulate_candidates_vectorized(mag, angle, R, Th)

    # Step 3: Use non-maximum suppression (via dilation) to find peaks in the accumulator.
    kernel_size = 2 * R + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    # Convert accumulator to float32 for dilation
    acc_float = acc.astype(np.float32)
    acc_dilated = cv2.dilate(acc_float, kernel)
    acc_peaks = (acc_float == acc_dilated) & (acc > 0)

    # For image peaks (laser spots are expected to be bright).
    gray_dilated = cv2.dilate(gray, kernel)
    image_peaks = gray == gray_dilated

    # Combine conditions: candidate must be a local maximum in both the accumulator and the image.
    candidates_mask = acc_peaks & image_peaks

    # Get candidate coordinates.
    cand_y, cand_x = np.where(candidates_mask)

    # Compute the candidate weight by summing the accumulator values in a window (using a box filter).
    acc_sum = cv2.boxFilter(acc_float, ddepth=-1, ksize=(kernel_size, kernel_size))
    weights = acc_sum[cand_y, cand_x].astype(np.int32)

    # Build candidate list and sort by descending weight.
    candidates = [
        {"position": (int(x), int(y)), "weight": int(w)}
        for x, y, w in zip(cand_x, cand_y, weights)
    ]
    candidates = sorted(candidates, key=lambda c: c["weight"], reverse=True)

    return candidates, acc


def draw_candidates(image, candidates):
    """
    Draw circles and candidate weights on the image.
    """
    if image.ndim == 2:
        output = cv2.cvtColor(np.uint8(image), cv2.COLOR_GRAY2BGR)
    else:
        output = image.copy()

    for candidate in candidates:
        x, y = candidate["position"]
        weight = candidate["weight"]
        cv2.circle(output, (x, y), 5, (0, 0, 255), 2)
        cv2.putText(
            output,
            str(weight),
            (x + 5, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
    return output


def test_gradient(image: cv2.UMat) -> list:
    # Parameters (adjust these as needed)
    R = 10  # Maximum expected radius of the laser spot.
    Th = 15  # Gradient magnitude threshold.

    # Detect laser spot candidates.
    candidates, acc = detect_laser_spots(image, R, Th)
    print("Detected {} candidates.".format(len(candidates)))
    for idx, candidate in enumerate(candidates):
        print(
            "Candidate {}: position={}, weight={}".format(
                idx + 1, candidate["position"], candidate["weight"]
            )
        )

    # Group nearby candidates.
    grouped_candidates = group_candidates(candidates, group_radius=R / 2)
    print("\nAfter grouping, {} candidates:".format(len(grouped_candidates)))
    for idx, candidate in enumerate(grouped_candidates, start=1):
        print(
            "Grouped Candidate {}: position={}, weight={}".format(
                idx, candidate["position"], candidate["weight"]
            )
        )

    # Draw candidates on the image.
    output = draw_candidates(image, grouped_candidates)
    cv2.imshow("Laser Spot Candidates", output)

    # Normalize accumulator for visualization.
    acc_norm = cv2.normalize(acc.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
    cv2.imshow("Accumulator", acc_norm.astype(np.uint8))

    return grouped_candidates


def group_candidates(candidates, group_radius=5):
    """
    Group nearby candidates that are within group_radius pixels.
    Merges candidates by computing the weighted average of their positions and
    summing their weights.

    Args:
      candidates: list of candidate dicts {'position': (x,y), 'weight': weight}
      group_radius: maximum distance for candidates to be considered overlapping.

    Returns:
      grouped: list of grouped candidate dicts.
    """
    grouped = []
    candidates = candidates.copy()  # shallow copy of list
    while candidates:
        # Pop the first candidate.
        base = candidates.pop(0)
        bx, by = base["position"]
        cluster = [base]
        remain = []
        for cand in candidates:
            cx, cy = cand["position"]
            if np.hypot(cx - bx, cy - by) <= group_radius:
                cluster.append(cand)
            else:
                remain.append(cand)
        candidates = remain

        total_weight = sum(c["weight"] for c in cluster)
        if total_weight == 0:
            avg_x, avg_y = bx, by
        else:
            avg_x = sum(c["position"][0] * c["weight"] for c in cluster) / total_weight
            avg_y = sum(c["position"][1] * c["weight"] for c in cluster) / total_weight
        grouped.append(
            {"position": (int(round(avg_x)), int(round(avg_y))), "weight": total_weight}
        )
    # Optionally, sort the grouped candidates by weight.
    grouped = sorted(grouped, key=lambda c: c["weight"], reverse=True)
    return grouped


def main():
    # Read input image. Replace 'input.jpg' with your image file.
    image_path = "pictures\\frame-50.jpg"
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print("Error: Could not read image from", image_path)
        return

    # Parameters (adjust these as needed)
    R = 11  # Maximum expected radius of the laser spot.
    Th = 25  # Gradient magnitude threshold.

    # Detect laser spot candidates.
    candidates, acc = detect_laser_spots(image, R, Th)
    print("Detected {} candidates.".format(len(candidates)))
    for idx, candidate in enumerate(candidates):
        print(
            "Candidate {}: position={}, weight={}".format(
                idx + 1, candidate["position"], candidate["weight"]
            )
        )

    # Draw candidates on the image.
    output = draw_candidates(image, candidates)
    cv2.imshow("Laser Spot Candidates", output)

    # Normalize accumulator for visualization.
    acc_norm = cv2.normalize(acc.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
    cv2.imshow("Accumulator", acc_norm.astype(np.uint8))

    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
