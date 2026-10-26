"""Common mask preparation and the two-stage image-registration search.

A transform is (angle, scale_step, x_step, y_step): degrees, 1% scale
increments, and 2-pixel shifts. All transformations act on a 320 x 128 ROI.
There is no database, model training, parallel processing, or disk cache.
"""
from pathlib import Path
import cv2
import numpy as np


def clear_border(image):
    image = image.copy()
    image[[0, -1], :] = 0
    image[:, [0, -1]] = 0
    return image


def prepare_edges(mask_file, opening=False):
    """Read a white-on-black, 1200 x 1000 callosity mask; extract ROI edges."""
    mask = cv2.imdecode(np.frombuffer(Path(mask_file).read_bytes(), np.uint8), 0)
    if mask is None or mask.shape != (1000, 1200):
        raise ValueError(f"Expected a 1200 x 1000 mask: {mask_file}")
    mask = (mask > 127).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    if opening:  # Chamfer removes isolated foreground pixels; HOG does not.
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # Find edges BEFORE cropping, so the crop boundary is not a callosity edge.
    edges = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel,
                             borderType=cv2.BORDER_REPLICATE)
    # Crop the 750 x 300 head region, then reduce it to the 320 x 128 matching ROI.
    edges = clear_border(edges > 0)[350:650, 225:975].astype(np.float32)
    edges = cv2.resize(edges, (320, 128), interpolation=cv2.INTER_AREA) > 1e-6
    edges = clear_border(edges)
    if not edges.any():
        raise ValueError(f"No callosity edges inside the ROI: {mask_file}")
    return edges


def smooth(edges):
    return clear_border(cv2.GaussianBlur(edges.astype(np.float32), (3, 3), 0))


def transform_image(image, transform):
    angle, scale_step, x_step, y_step = transform
    height, width = image.shape
    # Rotate and scale about the image centre; pixel coordinates start at zero.
    matrix = cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2),
                                    angle, 1 + 0.01 * scale_step)
    matrix[:, 2] += (2 * x_step, 2 * y_step)
    return clear_border(cv2.warpAffine(image, matrix, (width, height),
                                       flags=cv2.INTER_LINEAR))


def correlation_start(query, reference):
    """Find a coarse alignment using normalized correlation at 80 x 32 pixels."""
    query = cv2.resize(query, (80, 32), interpolation=cv2.INTER_AREA)
    reference = cv2.resize(reference, (80, 32), interpolation=cv2.INTER_AREA)
    # Fifteen coarse pixels equal 60 pixels in the full ROI.
    padded = np.pad(reference, 15).astype(np.float32)
    best_score = -np.inf
    best = (0, 0, 0, 0)
    for angle in range(-5, 6):
        for scale_step in range(-20, 21, 5):
            template = transform_image(query, (angle, scale_step, 0, 0))
            response = cv2.matchTemplate(padded, template, cv2.TM_CCOEFF_NORMED)
            _, score, _, (x, y) = cv2.minMaxLoc(response)
            if score > best_score:
                best_score = score
                # One coarse pixel is four ROI pixels, or two 2-pixel shift steps.
                best = (angle, scale_step, 2 * (x - 15), 2 * (y - 15))
    return best


def register(query, reference, distance_at):
    """Minimize the supplied HOG/chamfer distance from two starting positions.

    First obtain a correlation start. Then refine both that start and the
    identity transform: translations, rotation, scale, repeated until stable.
    This is a local search, not an exhaustive search over all combinations.
    """
    starts = [(0, 0, 0, 0)]  # Also refine the original, untransformed alignment.
    # Coarse registration starts: find an initial alignment by image correlation.
    coarse = correlation_start(query, reference)
    # Coarse registration ends; the returned shifts now refer to the 320 x 128 ROI.
    if coarse != starts[0]:
        starts.append(coarse)
    starts = sorted(starts, key=distance_at)
    best = starts[0]
    best_distance = distance_at(best)
    # Fine registration starts: minimize HOG or log-chamfer distance at 320 x 128.
    # Translation is limited to +/-60 px; scale to 0.80-1.20; angle to +/-5 deg.
    limits = (5, 20, 30, 30)
    # Each cycle tries 2-pixel translations, then 1-degree rotations, then 1% scale changes.
    phases = [[(0, 0, x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if x or y],
              [(-1, 0, 0, 0), (1, 0, 0, 0)],
              [(0, -1, 0, 0), (0, 1, 0, 0)]]
    for start in starts:
        current = start
        value = distance_at(current)
        for iteration in range(120):
            improved = False
            for steps in phases:
                next_transform, next_value = current, value
                for step in steps:
                    candidate = tuple(max(-limit, min(limit, p + d))
                                      for p, d, limit in zip(current, step, limits))
                    trial = distance_at(candidate)
                    if trial < next_value - 1e-7:
                        next_transform, next_value = candidate, trial
                improved = improved or next_transform != current
                current, value = next_transform, next_value
            if not improved:
                # Stop this starting point when a complete cycle finds no improvement.
                break
        if value < best_distance:
            best, best_distance = current, value
    # Fine registration ends: retain the better result from the two starting points.
    return best_distance, best
