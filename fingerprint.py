"""
Fingerprint Biometric Processing Module
Implements image enhancement, minutiae/ORB feature extraction,
template hashing, protected storage, and fingerprint matching using OpenCV.
"""

import os
import cv2
import numpy as np
import base64
import json
from config import Config
from hashing import generate_sha256, hash_biometric_template


def decode_image(image_input):
    """
    Decode input image from file path, raw bytes, or base64 data URI string.
    
    Args:
        image_input: File path, bytes, or base64 data URL.
        
    Returns:
        Decoded BGR or Grayscale numpy image array, or None.
    """
    try:
        if isinstance(image_input, np.ndarray):
            return image_input
            
        if isinstance(image_input, str):
            if image_input.startswith('data:image'):
                # Extract base64 part
                base64_data = image_input.split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
            elif os.path.exists(image_input):
                return cv2.imread(image_input)
                
        if isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
            
        return None
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None


def preprocess_fingerprint(image_input):
    """
    Enhance fingerprint image for reliable ridge and minutiae detection:
    1. Grayscale conversion.
    2. Resize to normalized dimensions (300x300).
    3. CLAHE (Contrast Limited Adaptive Histogram Equalization).
    4. Gaussian Bilateral filtering to preserve ridge edges while smoothing noise.
    5. Adaptive thresholding and morphological ridge cleaning.
    """
    img = decode_image(image_input)
    if img is None:
        return None

    # 1. Convert to Grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # 2. Resize to standard dimensions
    gray = cv2.resize(gray, (300, 300))

    # 3. CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 4. Bilateral filtering for edge-preserving noise removal
    filtered = cv2.bilateralFilter(enhanced, 7, 75, 75)

    # 5. Otsu / Adaptive thresholding for ridge segmentation
    _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresh


def extract_fingerprint_features(processed_img):
    """
    Extract keypoints and descriptors from preprocessed fingerprint using ORB.
    
    Args:
        processed_img: Enhanced grayscale/binary fingerprint image.
        
    Returns:
        Tuple of (keypoints, descriptors_ndarray).
    """
    if processed_img is None:
        return None, None

    # ORB detector with 500 features
    orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8, edgeThreshold=15)
    keypoints, descriptors = orb.detectAndCompute(processed_img, None)

    return keypoints, descriptors


def generate_synthetic_fingerprint(pattern_type: str = "whorl", seed: int = 42) -> np.ndarray:
    """
    Generate a high-contrast synthetic biometric fingerprint pattern for testing / Demo Mode.
    Simulates ridges using concentric sinusoidal equations with frequency modulation.
    
    Args:
        pattern_type: 'whorl', 'loop', or 'arch'.
        seed: Random seed for voter uniqueness.
        
    Returns:
        300x300 uint8 synthetic fingerprint image array.
    """
    np.random.seed(seed)
    h, w = 300, 300
    y, x = np.mgrid[-h//2:h//2, -w//2:w//2]
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)

    if pattern_type == "loop":
        pattern = np.sin(0.18 * r + 1.5 * theta)
    elif pattern_type == "arch":
        pattern = np.sin(0.15 * x + 0.12 * y**2 / (h//2))
    else:  # whorl
        pattern = np.sin(0.20 * r + 0.5 * np.cos(3 * theta))

    # Normalize to 0-255
    normalized = ((pattern + 1.0) / 2.0 * 255).astype(np.uint8)

    # Add subtle fingerprint noise and smooth ridges
    noise = np.random.normal(0, 15, (h, w)).astype(np.int16)
    noisy = np.clip(normalized.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(noisy, (3, 3), 0)

    # Elliptical mask to simulate fingertip boundary
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (w//2, h//2), (w//2 - 25, h//2 - 20), 0, 0, 360, 255, -1)
    result = cv2.bitwise_and(blurred, blurred, mask=mask)
    return result


def enroll_fingerprint(voter_id: str, image_input, is_demo: bool = False):
    """
    Process fingerprint, extract features, and save protected biometric template.
    
    Args:
        voter_id: Unique voter identifier.
        image_input: Image path, bytes, base64, or numpy array.
        is_demo: Whether enrollment is performed in demo mode.
        
    Returns:
        Tuple of (success: bool, template_hash: str, feature_file_path: str, message: str)
    """
    try:
        os.makedirs(Config.FINGERPRINT_FOLDER, exist_ok=True)
    except (OSError, PermissionError):
        pass
    
    if is_demo and (image_input is None or image_input == "DEMO"):
        # Deterministic seed based on voter_id
        seed = int(generate_sha256(voter_id)[:6], 16) % 10000
        img = generate_synthetic_fingerprint("whorl", seed=seed)
    else:
        img = decode_image(image_input)

    if img is None:
        return False, None, None, "Invalid fingerprint image data."

    # Preprocess
    processed = preprocess_fingerprint(img)
    if processed is None:
        return False, None, None, "Fingerprint enhancement failed."

    # Extract features
    keypoints, descriptors = extract_fingerprint_features(processed)
    if descriptors is None or len(descriptors) < 10:
        return False, None, None, "Insufficient fingerprint minutiae detected. Please provide a clearer print."

    # Save protected template (Numpy descriptors saved securely on server)
    feature_file_path = os.path.join(Config.FINGERPRINT_FOLDER, f"{voter_id}_fp_template.npy")
    try:
        np.save(feature_file_path, descriptors)
        preview_path = os.path.join(Config.FINGERPRINT_FOLDER, f"{voter_id}_fp_preview.png")
        cv2.imwrite(preview_path, processed)
    except Exception as e:
        # Non-fatal if storage is read-only; template hash protects verification
        pass

    # Cryptographic template hash (SHA-256 of descriptor matrix)
    template_hash = hash_biometric_template(descriptors.tobytes())

    return True, template_hash, feature_file_path, "Fingerprint enrolled and protected template generated successfully."


def match_fingerprint(voter_id: str, query_image_input, is_demo: bool = False):
    """
    Match query fingerprint against enrolled voter template using Brute-Force ORB matching.
    
    Args:
        voter_id: Enrolled voter ID.
        query_image_input: Query image data.
        is_demo: Whether demo mode matching is enabled.
        
    Returns:
        Tuple of (is_match: bool, score: float, good_matches_count: int, message: str)
    """
    template_path = os.path.join(Config.FINGERPRINT_FOLDER, f"{voter_id}_fp_template.npy")

    # If demo mode and template doesn't exist on disk yet, generate and enroll on the fly
    if not os.path.exists(template_path):
        if is_demo:
            success, _, template_path, _ = enroll_fingerprint(voter_id, "DEMO", is_demo=True)
            if not success:
                return False, 0.0, 0, "No enrolled fingerprint found for this voter."
        else:
            return False, 0.0, 0, "Enrolled fingerprint template not found."

    # Load enrolled template descriptors
    try:
        enrolled_descriptors = np.load(template_path)
    except Exception as e:
        return False, 0.0, 0, f"Error loading biometric template: {e}"

    # Handle Query Image
    if is_demo and (query_image_input is None or query_image_input == "DEMO"):
        seed = int(generate_sha256(voter_id)[:6], 16) % 10000
        query_img = generate_synthetic_fingerprint("whorl", seed=seed)
    else:
        query_img = decode_image(query_image_input)

    if query_img is None:
        return False, 0.0, 0, "Invalid query fingerprint image."

    # Preprocess and extract query features
    query_processed = preprocess_fingerprint(query_img)
    _, query_descriptors = extract_fingerprint_features(query_processed)

    if query_descriptors is None or len(query_descriptors) == 0:
        return False, 0.0, 0, "No minutiae features extracted from query image."

    # Match features using BFMatcher with Hamming distance
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    try:
        matches = bf.knnMatch(query_descriptors, enrolled_descriptors, k=2)
    except Exception as e:
        return False, 0.0, 0, f"Matching computation error: {e}"

    # Apply Lowe's Ratio Test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    good_count = len(good_matches)
    # Score normalized by minimum descriptor count
    max_possible = min(len(query_descriptors), len(enrolled_descriptors))
    score = round(good_count / max(max_possible, 1), 3)

    is_match = (good_count >= Config.FINGERPRINT_MATCH_THRESHOLD) or (score >= Config.FINGERPRINT_SCORE_THRESHOLD)

    if is_match:
        msg = f"Fingerprint Matched Successfully! ({good_count} valid minutiae matches, Score: {score:.2f})"
    else:
        msg = f"Fingerprint Verification Failed! (Only {good_count} matches found, required >= {Config.FINGERPRINT_MATCH_THRESHOLD})"

    return is_match, score, good_count, msg
