"""
Hashing Module for Blockchain Voting System
Implements SHA-256 cryptographic hashing for vote transactions,
biometric template protection, and block data integrity verification.
"""

import hashlib
import json
from typing import Any, Union


def generate_sha256(data: Union[str, bytes]) -> str:
    """
    Generate SHA-256 hexadecimal hash string for input data.
    
    Args:
        data: String or bytes to hash.
        
    Returns:
        64-character hexadecimal SHA-256 string.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    elif not isinstance(data, bytes):
        data = str(data).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def hash_transaction(tx_data: dict[str, Any]) -> str:
    """
    Deterministically hash a vote transaction dictionary using SHA-256.
    Keys are sorted to guarantee repeatable canonical representation.
    
    Args:
        tx_data: Transaction dictionary containing candidate_id, timestamp, voter_token_hash, etc.
        
    Returns:
        64-character SHA-256 hash.
    """
    # Sort keys to ensure deterministic canonical JSON encoding
    canonical_json = json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def hash_biometric_template(features: Union[list, str, bytes]) -> str:
    """
    Generate a cryptographic SHA-256 hash of extracted biometric feature templates.
    Protects voter biometrics by ensuring raw biometric descriptors cannot be reconstructed.
    
    Args:
        features: Biometric feature vector, descriptor string, or bytes.
        
    Returns:
        SHA-256 hash representing the enrolled template.
    """
    if isinstance(features, (list, tuple)):
        # Normalize numeric list representation
        features_str = json.dumps([round(float(x), 6) for x in features], separators=(',', ':'))
        return generate_sha256(features_str)
    return generate_sha256(features)


def hash_file(file_path: str) -> str:
    """
    Compute SHA-256 hash of a file on disk (read in 64KB chunks).
    
    Args:
        file_path: Absolute path to the file.
        
    Returns:
        SHA-256 hexadecimal string.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_hash(data: Union[str, bytes], expected_hash: str) -> bool:
    """
    Verify whether the SHA-256 hash of data matches the expected hash.
    
    Args:
        data: Input string or bytes.
        expected_hash: Hexadecimal hash string to compare against.
        
    Returns:
        True if hashes match exactly, False otherwise.
    """
    computed = generate_sha256(data)
    return computed.lower() == expected_hash.lower()
