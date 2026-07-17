import warnings

import numpy as np
import skimage as ski
from skimage.feature import canny


def analyze_payload_image(image_path):
    """
    Analyze a single payload test image for focus/aberration metrics.

    Args:
        image_path: path to a single test image (e.g. .jpg)

    Returns:
        dict with focus_metric, sharpness, astigmatism_ratio, edge_count
    """
    image = ski.io.imread(image_path)
    grey = ski.color.rgb2gray(image)

    # Edge sharpness
    edges = canny(grey, sigma=1.0)
    edge_count = int(np.sum(edges))

    # Laplacian variance (focus metric)
    laplacian = ski.filters.laplace(grey)
    focus_metric = float(np.var(laplacian))

    # Gradient magnitude (detail / sharpness)
    gx, gy = np.gradient(grey)
    gradient_mag = np.sqrt(gx**2 + gy**2)
    sharpness = float(np.mean(gradient_mag))

    # Astigmatism: ratio of horizontal to vertical gradient strength.
    # ~1.0 = no astigmatism. High variance across angles for a fixed
    # target usually means target tilt rather than optical astigmatism
    # (see analyze_astigmatism_by_angle in batch.py).
    h_strength = np.mean(np.abs(gx))
    v_strength = np.mean(np.abs(gy))
    astigmatism_ratio = float(max(h_strength, v_strength) / min(h_strength, v_strength))

    return {
        "focus_metric": focus_metric,
        "sharpness": sharpness,
        "astigmatism_ratio": astigmatism_ratio,
        "edge_count": edge_count,
    }


def log_focus_score(image_path, sigma=1.0, quantile=0.999):
    """
    Compute a LoG (Laplacian of Gaussian) based focus score for one image.

    This is a second, independent focus metric (vs. the Laplacian-variance
    one in analyze_payload_image) used as a cross-check.

    Args:
        image_path: path to a single test image
        sigma: Gaussian sigma for the LoG filter
        quantile: quantile of |LoG| used as the score (default 99.9%)

    Returns:
        float focus score
    """
    from PIL import Image
    from scipy import ndimage

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        img = Image.open(image_path).convert("L")
        img_array = np.array(img, dtype=np.float32)
        log_filtered = ndimage.gaussian_laplace(img_array, sigma=sigma)
        return float(np.quantile(np.abs(log_filtered), quantile))
