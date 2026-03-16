import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def find_document_contour(image: np.ndarray):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edged = cv2.dilate(edged, kernel, iterations=2)

    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 4:
            area = cv2.contourArea(approx)
            image_area = image.shape[0] * image.shape[1]
            if area > image_area * 0.1:
                logger.info("[SCANNER] Document contour found (area=%.1f%%)", (area / image_area) * 100)
                return approx.reshape(4, 2)

    logger.info("[SCANNER] No 4-corner contour found, skipping crop")
    return None


def remove_shadows(image: np.ndarray) -> np.ndarray:
    rgb_planes = cv2.split(image)
    result_planes = []

    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        normalized = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        result_planes.append(normalized)

    return cv2.merge(result_planes)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def process_receipt(input_path: str, output_path: str) -> str:
    logger.info("[SCANNER] Processing %s", input_path)
    image = cv2.imread(input_path)

    if image is None:
        raise ValueError(f"Could not read image: {input_path}")

    contour = find_document_contour(image)

    if contour is not None:
        image = four_point_transform(image, contour)
        logger.info("[SCANNER] Perspective warp applied")

    image = remove_shadows(image)
    logger.info("[SCANNER] Shadow removal applied")

    image = enhance_contrast(image)
    logger.info("[SCANNER] Contrast enhancement applied")

    cv2.imwrite(output_path, image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info("[SCANNER] Saved processed image to %s", output_path)

    return output_path
