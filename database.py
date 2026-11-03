"""
Database Module for Blockchain Voting System
Manages SQLite database initialization, schema creation, voter registration,
candidate management, election state, and persistent blockchain storage.
"""

import sqlite3
import os
import json
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from signatures import generate_ecdsa_keypair
from hashing import generate_sha256


def ensure_db_ready():
    """Ensure database file directory exists and seed template is copied if on serverless runtime."""
    try:
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    except (OSError, PermissionError):
        pass

    # If running in serverless mode (e.g. Vercel) and /tmp database does not exist,
    # copy the pre-seeded SQLite database from the deployment package if available.
    if Config.IS_SERVERLESS and not os.path.exists(Config.DATABASE_PATH):
        bundled_db = os.path.join(Config.BASE_DIR, 'database', 'voting.db')
        if os.path.exists(bundled_db):
            try:
                shutil.copy2(bundled_db, Config.DATABASE_PATH)
            except Exception as e:
                print(f"Serverless DB copy notice: {e}")


def get_db_connection():
    """Create and return a database connection with row factory enabled."""
    ensure_db_ready()
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables and seed initial admin, candidates, and sample voters."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Voters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            voter_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT NOT NULL,
            is_eligible INTEGER DEFAULT 1,
            has_voted INTEGER DEFAULT 0,
            fingerprint_enrolled INTEGER DEFAULT 0,
            face_enrolled INTEGER DEFAULT 0,
            fingerprint_template_hash TEXT,
            face_template_hash TEXT,
            fingerprint_feature_path TEXT,
            face_feature_path TEXT,
            public_key_pem TEXT,
            private_key_pem TEXT,
            voted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            party TEXT NOT NULL,
            symbol TEXT NOT NULL,
            manifesto TEXT,
            vote_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Election state table (single-row configuration)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS election_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            title TEXT NOT NULL,
            is_open INTEGER DEFAULT 1,
            is_closed INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP
        )
    ''')

    # Blockchain blocks persistence table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blockchain_blocks (
            block_index INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            transactions_json TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            transaction_hash TEXT NOT NULL,
            nonce INTEGER NOT NULL,
            current_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Audit log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            details TEXT,
            status TEXT
        )
    ''')

    # # 1. Seed Default Admin if not exists
    # cursor.execute('SELECT * FROM admin WHERE username = ?', (Config.DEFAULT_ADMIN_USER,))
    # if not cursor.fetchone():
    #     hashed_pw = generate_password_hash(Config.DEFAULT_ADMIN_PASS)
    #     cursor.execute(
    #         'INSERT INTO admin (username, password_hash) VALUES (?, ?)',
    #         (Config.DEFAULT_ADMIN_USER, hashed_pw)
    #     )
    # 1. Seed Default Admin if credentials are configured
    admin_username = Config.DEFAULT_ADMIN_USER
    admin_password = Config.DEFAULT_ADMIN_PASS
    if admin_username and admin_password:
        cursor.execute(
            'SELECT * FROM admin WHERE username = ?',
            (admin_username,)
        )

        if not cursor.fetchone():
            hashed_pw = generate_password_hash(admin_password)

            cursor.execute(
                'INSERT INTO admin (username, password_hash) VALUES (?, ?)',
                (admin_username, hashed_pw)
            )
    elif Config.IS_PRODUCTION:
        print("Admin account creation skipped: credentials are not configured.")


    # 2. Seed Default Election State if not exists
    cursor.execute('SELECT * FROM election_state WHERE id = 1')
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO election_state (id, title, is_open, is_closed)
            VALUES (1, 'General Election 2026: Digital Governance & Civic Tech', 1, 0)
        ''')

    # 3. Seed Candidates if empty
    cursor.execute('SELECT COUNT(*) as count FROM candidates')
    if cursor.fetchone()['count'] == 0:
        sample_candidates = [
            (
                'CAND-01',
                'Dr. Aisha Sharma',
                'Progressive Digital Alliance',
                '🚀 Rocket',
                'Advancing ethical AI research, open civic data, and technological sustainability.'
            ),
            (
                'CAND-02',
                'Rajesh V. Menon',
                'National Data Frontiers',
                '🌐 Globe',
                'Decentralized broadband infrastructure, digital literacy, and cyber defense.'
            ),
            (
                'CAND-03',
                'Priya K. Nair',
                'Green Horizon Coalition',
                '🌿 Leaf',
                'Clean renewable energy transition for data centers and green innovation grants.'
            ),
            (
                'CAND-04',
                'Kabir Sen',
                'Independent Cyber Union',
                '🛡️ Shield',
                'Voter privacy protection, transparent open algorithms, and citizen rights.'
            )
        ]
        cursor.executemany('''
            INSERT INTO candidates (candidate_id, name, party, symbol, manifesto, vote_count)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', sample_candidates)

    # 4. Seed Sample Voters if empty
    cursor.execute('SELECT COUNT(*) as count FROM voters')
    if cursor.fetchone()['count'] == 0:
        sample_voters = [
            ('VOTER-1001', 'Aarav Patel', 24, 'aarav@example.com', '9876543210', 1),
            ('VOTER-1002', 'Diya Roy', 28, 'diya@example.com', '9876543211', 1),
            ('VOTER-1003', 'Rohan Gupta', 22, 'rohan@example.com', '9876543212', 1),
            ('VOTER-1004', 'Ananya Verma', 17, 'ananya@example.com', '9876543213', 0),  # Underage test
        ]
        for vid, name, age, email, mob, eligible in sample_voters:
            priv_key, pub_key = generate_ecdsa_keypair()
            # Generate deterministic initial mock biometric template hashes for sample test voters
            fp_hash = generate_sha256(f"SAMPLE_FP_{vid}")
            face_hash = generate_sha256(f"SAMPLE_FACE_{vid}")
            cursor.execute('''
                INSERT INTO voters (
                    voter_id, full_name, age, email, mobile,
                    is_eligible, has_voted, fingerprint_enrolled, face_enrolled,
                    fingerprint_template_hash, face_template_hash,
                    public_key_pem, private_key_pem
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 1, 1, ?, ?, ?, ?)
            ''', (vid, name, age, email, mob, eligible, fp_hash, face_hash, pub_key, priv_key))

    conn.commit()
    conn.close()


def log_audit(action: str, details: str = "", status: str = "SUCCESS"):
    """Insert an audit log record into SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO audit_logs (action, details, status) VALUES (?, ?, ?)',
            (action, details, status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging audit: {e}")


def get_election_state():
    """Retrieve current election state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM election_state WHERE id = 1')
    state = cursor.fetchone()
    conn.close()
    return state


def update_election_state(is_open: int, is_closed: int):
    """Update election open/close state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    ended_at = datetime.now().isoformat() if is_closed else None
    cursor.execute('''
        UPDATE election_state 
        SET is_open = ?, is_closed = ?, ended_at = ?
        WHERE id = 1
    ''', (is_open, is_closed, ended_at))
    conn.commit()
    conn.close()
    log_audit("ELECTION_STATE_CHANGE", f"isOpen={is_open}, isClosed={is_closed}")


def get_all_voters():
    """Return list of all registered voters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT voter_id, full_name, age, email, mobile, is_eligible, has_voted, fingerprint_enrolled, face_enrolled, created_at FROM voters ORDER BY created_at DESC')
    voters = cursor.fetchall()
    conn.close()
    return voters


def get_voter_by_id(voter_id: str):
    """Return single voter record by Voter ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voters WHERE voter_id = ?', (voter_id,))
    voter = cursor.fetchone()
    conn.close()
    return voter


def get_all_candidates():
    """Return list of all candidates."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates ORDER BY id ASC')
    candidates = cursor.fetchall()
    conn.close()
    return candidates


def add_candidate(candidate_id: str, name: str, party: str, symbol: str, manifesto: str):
    """Add a new candidate."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO candidates (candidate_id, name, party, symbol, manifesto, vote_count)
        VALUES (?, ?, ?, ?, ?, 0)
    ''', (candidate_id, name, party, symbol, manifesto))
    conn.commit()
    conn.close()
    log_audit("ADD_CANDIDATE", f"Added candidate {name} ({candidate_id})")


def mark_voter_as_voted(voter_id: str, candidate_id: str):
    """
    Atomically update voter status to voted and increment candidate vote count.
    Ensures single vote per voter.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check current status
        cursor.execute('SELECT has_voted, is_eligible FROM voters WHERE voter_id = ?', (voter_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Voter ID not found."
        if row['has_voted'] == 1:
            conn.close()
            return False, "Voter has already cast their vote."
        if row['is_eligible'] == 0:
            conn.close()
            return False, "Voter is not eligible to vote."

        # Update voter record
        now = datetime.now().isoformat()
        cursor.execute('UPDATE voters SET has_voted = 1, voted_at = ? WHERE voter_id = ?', (now, voter_id))

        # Update candidate tally
        cursor.execute('UPDATE candidates SET vote_count = vote_count + 1 WHERE candidate_id = ?', (candidate_id,))

        conn.commit()
        conn.close()
        log_audit("VOTE_CAST", f"Voter {voter_id} successfully cast ballot.")
        return True, "Vote registered in database successfully."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)
