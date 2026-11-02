import os

# Base directory of the Blockchain Voting System project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application Configuration Settings."""
    
    # Flask Secret Key for secure sessions
    SECRET_KEY = os.environ.get('SECRET_KEY', 'btech_data_science_blockchain_voting_secret_key_2026')
    
    # SQLite Database Configuration
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'voting.db')
    
    # Upload Directories
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    FINGERPRINT_FOLDER = os.path.join(UPLOAD_FOLDER, 'fingerprints')
    FACE_FOLDER = os.path.join(UPLOAD_FOLDER, 'faces')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tif', 'tiff'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    
    # Biometric Engine Settings
    # In Demo Mode, users can authenticate using bundled sample biometrics or live upload/webcam
    DEMO_MODE = True
    
    # Fingerprint matching threshold (minimum number of good matched minutiae/ORB descriptors)
    FINGERPRINT_MATCH_THRESHOLD = 12
    FINGERPRINT_SCORE_THRESHOLD = 0.55
    
    # Face recognition cosine similarity threshold (0.0 to 1.0)
    FACE_SIMILARITY_THRESHOLD = 0.65
    
    # Blockchain Settings
    BLOCKCHAIN_DIFFICULTY = 2  # Number of leading zeros for Proof-of-Work
    BLOCKCHAIN_SALT = "sec_voting_anon_salt_2026_ds_project"
    
    # Default Admin Credentials
    DEFAULT_ADMIN_USER = "admin"
    DEFAULT_ADMIN_PASS = "Admin@2026!"
