"""
Application Configuration Module for
Blockchain-Integrated Multimodal Biometric Electronic Voting System
Academic Research Capstone Project
"""

import os
import sys
import tempfile

# Base directory of the Blockchain Voting System project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Detect serverless environment (e.g. Vercel, AWS Lambda) or production flag
IS_SERVERLESS = bool(
    os.environ.get('VERCEL') == '1' or
    os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or
    os.environ.get('SERVERLESS') == '1'
)

IS_PRODUCTION = bool(
    IS_SERVERLESS or
    os.environ.get('FLASK_ENV') == 'production' or
    os.environ.get('ENVIRONMENT') == 'production'
)

# Helper to check if currently executing inside a test runner
IS_TESTING = bool(
    os.environ.get('TESTING') == 'True' or
    'unittest' in sys.modules
)


class Config:
    """Application Configuration Settings."""

    # Serverless & Environment Flags
    IS_SERVERLESS = IS_SERVERLESS
    IS_PRODUCTION = IS_PRODUCTION

    # --------------------------------------------------------------------------
    # 1. Flask Secret Key (Session Protection & Cookie Cryptography)
    # --------------------------------------------------------------------------
    # In production and Vercel deployments, a strong, secret random key MUST be
    # supplied via the SECRET_KEY environment variable. Hardcoded production
    # fallbacks are strictly prohibited.
    # For local development and testing only, a clearly labeled local key is used.
    _env_secret = os.environ.get('SECRET_KEY')
    if _env_secret:
        SECRET_KEY = _env_secret
    elif IS_PRODUCTION and not IS_TESTING:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: 'SECRET_KEY' environment variable is required for production/Vercel deployment. "
            "Please configure a strong SECRET_KEY in your Vercel Project Settings -> Environment Variables. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        # Documented local-only development fallback (never used in production/Vercel)
        SECRET_KEY = os.environ.get(
            'DEV_SECRET_KEY',
            'local-development-only-secret-key-do-not-use-in-production'
        )

    # --------------------------------------------------------------------------
    # 2. SQLite Database Configuration & Serverless Storage Path
    # --------------------------------------------------------------------------
    # In local development: Stored at Blockchain_Voting_System/database/voting.db
    # In Vercel / serverless: Root filesystem is read-only. Database is routed to
    # /tmp/voting.db.
    # NOTE: /tmp is ephemeral on serverless containers and resets on cold starts.
    if IS_SERVERLESS or os.environ.get('DATABASE_PATH'):
        DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(tempfile.gettempdir(), 'voting.db'))
    else:
        DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'voting.db')

    # --------------------------------------------------------------------------
    # 3. Biometric Image Upload & Storage Security
    # --------------------------------------------------------------------------
    if IS_SERVERLESS or os.environ.get('UPLOAD_FOLDER'):
        UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(tempfile.gettempdir(), 'uploads'))
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    FINGERPRINT_FOLDER = os.path.join(UPLOAD_FOLDER, 'fingerprints')
    FACE_FOLDER = os.path.join(UPLOAD_FOLDER, 'faces')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tif', 'tiff'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload limit

    # --------------------------------------------------------------------------
    # 4. Biometric Engine Settings (Academic Prototype)
    # --------------------------------------------------------------------------
    # DEMO_MODE is kept ENABLED by default for this academic prototype.
    # This allows evaluators and cloud users on Vercel to test the complete 17-step
    # workflow using synthetic mathematical fingerprint patterns and facial embeddings
    # without requiring physical USB fingerprint scanner hardware.
    DEMO_MODE = os.environ.get('DEMO_MODE', 'True').lower() in ('true', '1', 't', 'yes')

    # Dual-Biometric Matching Thresholds (Fingerprint & Face only)
    FINGERPRINT_MATCH_THRESHOLD = int(os.environ.get('FINGERPRINT_MATCH_THRESHOLD', '12'))
    FINGERPRINT_SCORE_THRESHOLD = float(os.environ.get('FINGERPRINT_SCORE_THRESHOLD', '0.55'))
    FACE_SIMILARITY_THRESHOLD = float(os.environ.get('FACE_SIMILARITY_THRESHOLD', '0.65'))

    # --------------------------------------------------------------------------
    # 5. Blockchain Settings
    # --------------------------------------------------------------------------
    BLOCKCHAIN_DIFFICULTY = int(os.environ.get('BLOCKCHAIN_DIFFICULTY', '2'))
    # BLOCKCHAIN_SALT = os.environ.get('BLOCKCHAIN_SALT', 'sec_voting_anon_salt_2026_ds_project')

    # Blockchain anonymization salt
    _env_blockchain_salt = os.environ.get('BLOCKCHAIN_SALT')

    if _env_blockchain_salt:
        BLOCKCHAIN_SALT = _env_blockchain_salt
    elif IS_PRODUCTION and not IS_TESTING:
        raise RuntimeError(
            "BLOCKCHAIN_SALT environment variable is required in production."
        )
    else:
        BLOCKCHAIN_SALT = 'local-development-only-blockchain-salt'

    # --------------------------------------------------------------------------
    # 6. Administrator Account Configuration
    # --------------------------------------------------------------------------
    # In Vercel / production: Default admin credentials MUST NOT be hardcoded.
    # They must be explicitly set via DEFAULT_ADMIN_USER and DEFAULT_ADMIN_PASS
    # in the Vercel dashboard. If unset in production, default admin creation is
    # safely disabled to prevent unauthorized access.
    # In local development: Defaults to 'admin' / 'Admin@2026!' for local usability.
    if IS_PRODUCTION and not IS_TESTING:
        DEFAULT_ADMIN_USER = os.environ.get('DEFAULT_ADMIN_USER')
        DEFAULT_ADMIN_PASS = os.environ.get('DEFAULT_ADMIN_PASS')
    else:
        DEFAULT_ADMIN_USER = os.environ.get('DEFAULT_ADMIN_USER', 'admin')
        DEFAULT_ADMIN_PASS = os.environ.get('DEFAULT_ADMIN_PASS', 'Admin@2026!')
