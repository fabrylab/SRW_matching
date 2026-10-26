"""Compare registered callosity edges using Histograms of Oriented Gradients."""
import cv2
import numpy as np
from . import registration


def descriptor(image):
    # 32 x 32 blocks, 16-pixel stride/cells, nine unsigned orientation bins.
    hog = cv2.HOGDescriptor((320, 128), (32, 32), (16, 16), (16, 16), 9)
    pixels = np.clip(image * 255, 0, 255).astype(np.uint8)
    vector = hog.compute(pixels).ravel().astype(np.float32)
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-6 else vector


def prepare(mask_file):
    image = registration.smooth(registration.prepare_edges(mask_file))
    return {"image": image, "vector": descriptor(image)}


def match(query, reference):
    """Return distance and alignment; a smaller distance is a better match."""
    # Reuse descriptors within this pair only. The dictionary avoids evaluating
    # the same transformed query repeatedly during the local search.
    vectors = {(0, 0, 0, 0): query["vector"]}

    def distance_at(transform):
        if transform not in vectors:
            image = registration.transform_image(query["image"], transform)
            vectors[transform] = descriptor(image)
        # For unit-length descriptors, 1 minus their dot product is the cosine distance.
        return 1.0 - float(np.dot(vectors[transform], reference["vector"]))

    # The shared registration search uses distance_at to score each fine alignment.
    return registration.register(query["image"], reference["image"], distance_at)
