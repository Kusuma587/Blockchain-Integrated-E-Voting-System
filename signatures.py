"""
ECDSA Digital Signature Module
Implements Elliptic Curve Digital Signature Algorithm (ECDSA) using SECP256K1 curve
for transaction authentication, voter authorization, and non-repudiation.
"""

import base64
import json
from typing import Tuple, Union
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature


def generate_ecdsa_keypair() -> Tuple[str, str]:
    """
    Generate an ECDSA key pair using SECP256K1 elliptic curve.
    
    Returns:
        Tuple of (private_key_pem_string, public_key_pem_string)
    """
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem


def load_private_key(private_key_pem: str) -> ec.EllipticCurvePrivateKey:
    """Load an ECDSA private key from a PEM string."""
    return serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None
    )


def load_public_key(public_key_pem: str) -> ec.EllipticCurvePublicKey:
    """Load an ECDSA public key from a PEM string."""
    return serialization.load_pem_public_key(
        public_key_pem.encode('utf-8')
    )


def sign_data(private_key_pem: str, data: Union[str, bytes, dict]) -> str:
    """
    Sign input data using ECDSA SECP256K1 with SHA-256.
    
    Args:
        private_key_pem: Sender's ECDSA private key in PEM format.
        data: Data to sign (string, bytes, or dictionary).
        
    Returns:
        Base64-encoded digital signature string.
    """
    if isinstance(data, dict):
        # Canonical JSON string for deterministic signing
        data_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    elif isinstance(data, str):
        data_bytes = data.encode('utf-8')
    else:
        data_bytes = data

    private_key = load_private_key(private_key_pem)
    signature = private_key.sign(
        data_bytes,
        ec.ECDSA(hashes.SHA256())
    )
    return base64.b64encode(signature).decode('utf-8')


def verify_signature(public_key_pem: str, signature_b64: str, data: Union[str, bytes, dict]) -> bool:
    """
    Verify an ECDSA SECP256K1 digital signature against the signed data.
    
    Args:
        public_key_pem: Signer's ECDSA public key in PEM format.
        signature_b64: Base64-encoded signature string.
        data: The original data that was signed.
        
    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        if isinstance(data, dict):
            data_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        signature = base64.b64decode(signature_b64.encode('utf-8'))
        public_key = load_public_key(public_key_pem)

        public_key.verify(
            signature,
            data_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except (InvalidSignature, ValueError, Exception):
        return False
