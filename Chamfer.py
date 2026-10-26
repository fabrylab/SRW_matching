"""Symmetric, capped log-chamfer distance between registered callosity edges."""
import math
import cv2
import numpy as np
import Registration

CAP = 30.0  # ROI pixels; distant unmatched edges cannot dominate without limit.


def contour_points(edges):
    """Take at most ten equally arc-length-spaced points from each contour."""
    count, labels = cv2.connectedComponents(edges.astype(np.uint8), connectivity=8)
    samples = []
    for label in range(1, count):
        component = (labels == label).astype(np.uint8) * 255
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            xy = contour[:, 0, :].astype(np.float32)
            if len(xy) <= 10:
                samples.append(xy[:, ::-1])  # Store points as (y, x).
                continue
            closed = np.vstack([xy, xy[0]])
            lengths = np.linalg.norm(np.diff(closed, axis=0), axis=1)
            cumulative = np.r_[0, np.cumsum(lengths)]
            targets = np.linspace(0, float(lengths.sum()), 10, endpoint=False)
            points = np.empty((10, 2), dtype=np.float32)
            for i, target in enumerate(targets):
                segment = int(np.searchsorted(cumulative, target, side="right") - 1)
                segment = max(0, min(segment, len(lengths) - 1))
                fraction = (target - cumulative[segment]) / lengths[segment]
                points[i] = closed[segment] + fraction * (closed[segment + 1] - closed[segment])
            samples.append(points[:, ::-1])
    return np.vstack(samples)


def prepare(mask_file):
    edges = Registration.prepare_edges(mask_file, opening=True)
    # Each pixel stores its distance to the nearest callosity edge.
    distance = cv2.distanceTransform((~edges).astype(np.uint8) * 255, cv2.DIST_L2, 3)
    return {"points": contour_points(edges),
            "distance": np.log1p(np.minimum(distance, CAP)).astype(np.float32),
            "image": Registration.smooth(edges)}


def transform_points(points, transform, inverse=False):
    # Keep the server's chamfer point convention: positive rotation is clockwise
    # in image coordinates (y grows downwards). Inverse maps reference to query.
    angle, scale_step, x_step, y_step = transform
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)
    scale = 1 + 0.01 * scale_step
    # Centre coordinates: y = (128 - 1)/2 = 63.5 and x = (320 - 1)/2 = 159.5.
    # Subtract the centre before rotation/scaling, then add it back afterwards.
    y, x = points[:, 0] - 63.5, points[:, 1] - 159.5
    if inverse:
        y, x = y - 2 * y_step, x - 2 * x_step
        return np.column_stack([(-s * x + c * y) / scale + 63.5,
                                (c * x + s * y) / scale + 159.5])
    return np.column_stack([scale * (s * x + c * y) + 63.5 + 2 * y_step,
                            scale * (c * x - s * y) + 159.5 + 2 * x_step])


def sample_distance(distance, points):
    y, x = np.rint(points).astype(int).T
    inside = (x >= 0) & (x < 320) & (y >= 0) & (y < 128)
    if not inside.any():
        return float(np.log1p(CAP))
    # As in the server, average the valid points, then penalize points that
    # moved outside the image. This discourages shifting features out of view.
    return float(distance[y[inside], x[inside]].mean()) + np.log1p(CAP) * (1 - inside.mean())


def match(query, reference):
    def distance_at(transform):
        forward = transform_points(query["points"], transform)
        backward = transform_points(reference["points"], transform, inverse=True)
        # Average both directions so the comparison is symmetric.
        return 0.5 * (sample_distance(reference["distance"], forward)
                      + sample_distance(query["distance"], backward))

    # The shared registration search uses distance_at to score each fine alignment.
    return Registration.register(query["image"], reference["image"], distance_at)
