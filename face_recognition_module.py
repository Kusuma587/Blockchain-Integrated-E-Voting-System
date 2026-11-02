"""
Face Recognition Biometric Processing Module
Implements OpenCV face detection (Haar Cascade), spatial LBP feature embedding,
cosine similarity matching, and protected facial template storage.
"""

import os
import cv2
import numpy as np
import base64
import json
from config import Config
from hashing import generate_sha256, hash_biometric_template
from fingerprint import decode_image

# Load OpenCV Frontal Face Haar Cascade Classifier
FACE_CASCADE_PATH = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)


def compute_lbp(image_gray):
    """
    Compute Local Binary Pattern (LBP) representation of a grayscale image.
    Transforms pixel neighborhoods into binary texture representations.
    """
    h, w = image_gray.shape
    lbp_img = np.zeros((h - 2, w - 2), dtype=np.uint8)

    # 8-neighbor offsets
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, 1),
        (1, 1), (1, 0), (1, -1),
        (0, -1)
    ]

    center = image_gray[1:h-1, 1:w-1]

    for bit_index, (dy, dx) in enumerate(offsets):
        neighbor = image_gray[1+dy:h-1+dy, 1+dx:w-1+dx]
        # Bit is 1 if neighbor >= center pixel, else 0
        bit_val = (neighbor >= center).astype(np.uint8)
        lbp_img += (bit_val << bit_index)

    return lbp_img


def extract_face_embedding(face_img):
    """
    Extract a normalized biometric feature embedding vector from an aligned face image (128x128).
    Divides face into an 8x8 spatial grid, computes LBP histogram per cell,
    and returns a concatenated, L2-normalized 256-dimensional feature vector.
    
    Args:
        face_img: Aligned face image (128x128 grayscale or BGR).
        
    Returns:
        1D numpy array representing the normalized face embedding.
    """
    if face_img is None:
        return None

    if len(face_img.shape) == 3:
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_img.copy()

    # Standardize size to 128x128
    gray = cv2.resize(gray, (128, 128))

    # Equalize illumination
    gray = cv2.equalizeHist(gray)

    # Compute Local Binary Patterns
    lbp = compute_lbp(gray)  # size ~ 126x126

    # Divide into 4x4 spatial grid cells (each ~31x31 pixels)
    grid_rows, grid_cols = 4, 4
    cell_h = lbp.shape[0] // grid_rows
    cell_w = lbp.shape[1] // grid_cols

    histograms = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            cell = lbp[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            # 16-bin histogram for each local region
            hist, _ = np.histogram(cell, bins=16, range=(0, 256))
            histograms.extend(hist)

    embedding = np.array(histograms, dtype=np.float32)

    # L2 Normalization
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding


def detect_and_align_face(image_input):
    """
    Detect face in image using Haar Cascade and align/crop to 128x128.
    
    Args:
        image_input: File path, base64 data, or numpy array.
        
    Returns:
        Cropped & aligned 128x128 face numpy array, or None if detection fails.
    """
    img = decode_image(image_input)
    if img is None:
        return None

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(60, 60)
    )

    if len(faces) > 0:
        # Choose the largest detected face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]

        # Add modest padding margin around face box
        margin = int(0.1 * w)
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(gray.shape[1], x + w + margin)
        y2 = min(gray.shape[0], y + h + margin)

        cropped = gray[y1:y2, x1:x2]
        return cv2.resize(cropped, (128, 128))
    else:
        # If no face box detected (e.g. already closely cropped or passport photo), resize whole image
        return cv2.resize(gray, (128, 128))


def generate_synthetic_face(seed: int = 1001) -> np.ndarray:
    """
    Generate synthetic face biometric image for Demo Mode / testing.
    
    Args:
        seed: Voter ID derived integer seed.
        
    Returns:
        128x128 grayscale synthetic face image.
    """
    np.random.seed(seed)
    face = np.ones((128, 128), dtype=np.uint8) * 200

    # Draw head oval
    cv2.ellipse(face, (64, 64), (45, 55), 0, 0, 360, 160, -1)

    # Eyes
    cv2.circle(face, (48, 52), 6, 80, -1)
    cv2.circle(face, (80, 52), 6, 80, -1)
    cv2.circle(face, (48, 52), 2, 20, -1)
    cv2.circle(face, (80, 52), 2, 20, -1)

    # Nose
    cv2.line(face, (64, 58), (62, 74), 100, 2)
    cv2.line(face, (62, 74), (66, 74), 100, 2)

    # Mouth smile
    cv2.ellipse(face, (64, 88), (18, 10), 0, 20, 160, 70, 2)

    # Soften
    face = cv2.GaussianBlur(face, (5, 5), 0)
    return face


def enroll_face(voter_id: str, image_input, is_demo: bool = False):
    """
    Detect face, extract feature embedding vector, and save protected template.
    
    Args:
        voter_id: Voter unique ID.
        image_input: Image path, bytes, base64, or 'DEMO'.
        is_demo: Whether demo mode enrollment is enabled.
        
    Returns:
        Tuple of (success: bool, template_hash: str, feature_file_path: str, message: str)
    """
    os.makedirs(Config.FACE_FOLDER, exist_ok=True)

    if is_demo and (image_input is None or image_input == "DEMO"):
        seed = int(generate_sha256(voter_id)[:6], 16) % 10000
        face_img = generate_synthetic_face(seed=seed)
    else:
        face_img = detect_and_align_face(image_input)

    if face_img is None:
        return False, None, None, "Face could not be detected. Please ensure good lighting and face camera directly."

    # Extract embedding
    embedding = extract_face_embedding(face_img)
    if embedding is None:
        return False, None, None, "Failed to compute facial feature embedding."

    # Save embedding vector
    feature_file_path = os.path.join(Config.FACE_FOLDER, f"{voter_id}_face_embedding.npy")
    np.save(feature_file_path, embedding)

    # Save aligned face preview
    preview_path = os.path.join(Config.FACE_FOLDER, f"{voter_id}_face_preview.png")
    cv2.imwrite(preview_path, face_img)

    # Template hash
    template_hash = hash_biometric_template(embedding.tolist())

    return True, template_hash, feature_file_path, "Facial template enrolled and secured successfully."


def match_face(voter_id: str, query_image_input, is_demo: bool = False):
    """
    Match query face against enrolled voter face embedding using Cosine Similarity.
    
    Args:
        voter_id: Voter ID to verify.
        query_image_input: Live camera frame or uploaded face image.
        is_demo: Demo mode flag.
        
    Returns:
        Tuple of (is_match: bool, similarity_score: float, message: str)
    """
    template_path = os.path.join(Config.FACE_FOLDER, f"{voter_id}_face_embedding.npy")

    # If demo mode and template doesn't exist yet, auto-enroll demo face
    if not os.path.exists(template_path):
        if is_demo:
            success, _, template_path, _ = enroll_face(voter_id, "DEMO", is_demo=True)
            if not success:
                return False, 0.0, "Enrolled face template not found."
        else:
            return False, 0.0, "Enrolled face template not found."

    # Load enrolled embedding
    try:
        enrolled_embedding = np.load(template_path)
    except Exception as e:
        return False, 0.0, f"Error loading face template: {e}"

    # Process query face
    if is_demo and (query_image_input is None or query_image_input == "DEMO"):
        seed = int(generate_sha256(voter_id)[:6], 16) % 10000
        query_face = generate_synthetic_face(seed=seed)
    else:
        query_face = detect_and_align_face(query_image_input)

    if query_face is None:
        return False, 0.0, "No face detected in submitted verification image."

    query_embedding = extract_face_embedding(query_face)
    if query_embedding is None:
        return False, 0.0, "Failed to extract query face embedding."

    # Compute Cosine Similarity
    # Both vectors are L2-normalized, so cosine similarity is simply the dot product
    similarity = float(np.dot(enrolled_embedding, query_embedding))
    similarity = round(max(0.0, min(1.0, similarity)), 3)

    is_match = similarity >= Config.FACE_SIMILARITY_THRESHOLD

    if is_match:
        msg = f"Facial Authentication Successful! (Confidence: {similarity * 100:.1f}%, Threshold: {Config.FACE_SIMILARITY_THRESHOLD * 100:.0f}%)"
    else:
        msg = f"Facial Authentication Failed! (Confidence: {similarity * 100:.1f}% below required {Config.FACE_SIMILARITY_THRESHOLD * 100:.0f}%)"

    return is_match, similarity, msg
