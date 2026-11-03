"""
Main Flask Web Application for
"Blockchain-Integrated Multimodal Biometric Electronic Voting System"
Final-Year BTech Data Science Project
"""

import os
import json
import time
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from database import (
    init_db, get_db_connection, log_audit,
    get_election_state, update_election_state,
    get_all_voters, get_voter_by_id, get_all_candidates,
    add_candidate
)
from signatures import generate_ecdsa_keypair
from hashing import generate_sha256
from fingerprint import enroll_fingerprint, match_fingerprint
from face_recognition_module import enroll_face, match_face
from authentication import verify_voter_eligibility, authenticate_multimodal_biometrics
from voting import cast_vote
from results import calculate_election_results
from blockchain import blockchain_instance

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config.from_object(Config)

# Ensure upload directories exist safely without crashing on read-only serverless filesystems
try:
    os.makedirs(Config.FINGERPRINT_FOLDER, exist_ok=True)
    os.makedirs(Config.FACE_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
except (OSError, PermissionError):
    pass

# Initialize database tables and sample seeds
with app.app_context():
    init_db()


# -------------------------------------------------------------
# Decorators & Context Processors
# -------------------------------------------------------------
def admin_required(f):
    """Ensure user is logged in as administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Administrator login required to access this resource.", "warning")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def voter_auth_required(f):
    """Ensure voter has successfully passed multimodal biometric authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        voter_id = session.get('authenticated_voter_id')
        session_token = session.get('voter_session_token')
        if not voter_id or not session_token:
            flash("Multimodal biometric authentication is required before accessing the voting ballot.", "danger")
            return redirect(url_for('authenticate_voter'))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_global_state():
    """Inject election state, demo mode status, and runtime environment into all templates."""
    election = get_election_state()
    return {
        'election_state': election,
        'demo_mode': Config.DEMO_MODE,
        'is_serverless': Config.IS_SERVERLESS,
        'app_title': 'Blockchain-Integrated Multimodal Biometric E-Voting'
    }


# -------------------------------------------------------------
# Module 1: Admin Routes
# -------------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin WHERE username = ?', (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            log_audit("ADMIN_LOGIN", f"Admin user '{username}' logged in successfully.")
            flash(f"Welcome back, Administrator ({username})!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            log_audit("ADMIN_LOGIN_FAILED", f"Failed login attempt for username '{username}'.", "FAILED")
            flash("Invalid administrator credentials. Please try again.", "danger")

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    username = session.pop('admin_username', 'Admin')
    session.pop('admin_logged_in', None)
    log_audit("ADMIN_LOGOUT", f"Admin '{username}' logged out.")
    flash("You have been securely logged out.", "info")
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard overview."""
    voters = get_all_voters()
    candidates = get_all_candidates()
    election = get_election_state()
    chain_valid, chain_msg, corrupted_idx = blockchain_instance.is_chain_valid()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 15')
    logs = cursor.fetchall()
    conn.close()

    total_registered = len(voters)
    total_voted = sum(1 for v in voters if v['has_voted'] == 1)
    total_eligible = sum(1 for v in voters if v['is_eligible'] == 1)

    return render_template(
        'dashboard.html',
        voters=voters,
        candidates=candidates,
        election=election,
        total_registered=total_registered,
        total_voted=total_voted,
        total_eligible=total_eligible,
        total_blocks=len(blockchain_instance.chain),
        chain_valid=chain_valid,
        chain_msg=chain_msg,
        corrupted_idx=corrupted_idx,
        logs=logs
    )


@app.route('/admin/election/toggle', methods=['POST'])
@admin_required
def toggle_election():
    """Open or close the election."""
    action = request.form.get('action')
    if action == 'open':
        update_election_state(is_open=1, is_closed=0)
        flash("Election has been opened! Eligible voters can now authenticate and vote.", "success")
    elif action == 'close':
        update_election_state(is_open=0, is_closed=1)
        flash("Election has been officially closed! Vote counting and official tally are now finalized.", "warning")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/candidate/add', methods=['POST'])
@admin_required
def add_candidate_route():
    """Add a new election candidate."""
    candidate_id = request.form.get('candidate_id', '').strip()
    name = request.form.get('name', '').strip()
    party = request.form.get('party', '').strip()
    symbol = request.form.get('symbol', '').strip()
    manifesto = request.form.get('manifesto', '').strip()

    if not candidate_id or not name or not party:
        flash("Candidate ID, Name, and Party are required fields.", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        add_candidate(candidate_id, name, party, symbol, manifesto)
        flash(f"Candidate '{name}' ({candidate_id}) added successfully.", "success")
    except Exception as e:
        flash(f"Error adding candidate: {e}", "danger")

    return redirect(url_for('admin_dashboard'))


# -------------------------------------------------------------
# Module 2: Voter Registration
# -------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new voter."""
    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        full_name = request.form.get('full_name', '').strip()
        age_str = request.form.get('age', '').strip()
        email = request.form.get('email', '').strip().lower()
        mobile = request.form.get('mobile', '').strip()

        # Validation
        if not voter_id or not full_name or not age_str or not email or not mobile:
            flash("All registration fields are required.", "danger")
            return render_template('register.html')

        try:
            age = int(age_str)
        except ValueError:
            flash("Age must be a valid integer number.", "danger")
            return render_template('register.html')

        # Eligibility determination (Legal voting age >= 18)
        is_eligible = 1 if age >= 18 else 0

        # Check duplicates
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT voter_id FROM voters WHERE voter_id = ? OR email = ?', (voter_id, email))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            flash(f"Registration rejected: Voter ID or Email already exists in the system.", "danger")
            return render_template('register.html')

        # Generate cryptographic ECDSA SECP256k1 keypair for this voter
        priv_key, pub_key = generate_ecdsa_keypair()

        cursor.execute('''
            INSERT INTO voters (
                voter_id, full_name, age, email, mobile,
                is_eligible, has_voted, fingerprint_enrolled, face_enrolled,
                public_key_pem, private_key_pem
            ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
        ''', (voter_id, full_name, age, email, mobile, is_eligible, pub_key, priv_key))
        conn.commit()
        conn.close()

        log_audit("VOTER_REGISTERED", f"Voter {voter_id} ({full_name}), Age: {age}, Eligible: {is_eligible}")

        if not is_eligible:
            flash(f"Voter {voter_id} registered. Note: Under legal voting age (<18), voter is marked as INELIGIBLE.", "warning")
        else:
            flash(f"Voter {voter_id} successfully registered! Next, complete fingerprint and face enrollment.", "success")

        # Redirect to fingerprint enrollment
        return redirect(url_for('enroll_fingerprint_route', voter_id=voter_id))

    return render_template('register.html')


# -------------------------------------------------------------
# Module 3 & 4: Biometric Enrollment
# -------------------------------------------------------------
@app.route('/enroll/fingerprint', methods=['GET', 'POST'])
def enroll_fingerprint_route():
    """Fingerprint biometric enrollment."""
    prefill_voter_id = request.args.get('voter_id', '')

    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        mode = request.form.get('mode', 'live')  # 'live' or 'demo'
        is_demo = (mode == 'demo') or Config.DEMO_MODE

        voter = get_voter_by_id(voter_id)
        if not voter:
            flash(f"Voter ID '{voter_id}' not found. Please register first.", "danger")
            return render_template('fingerprint.html', prefill_voter_id=voter_id)

        # Image capture: uploaded file, webcam data URL, or demo trigger
        image_input = None
        if 'fingerprint_file' in request.files and request.files['fingerprint_file'].filename != '':
            image_input = request.files['fingerprint_file'].read()
        elif request.form.get('webcam_image'):
            image_input = request.form.get('webcam_image')
        elif is_demo:
            image_input = "DEMO"

        success, template_hash, file_path, msg = enroll_fingerprint(voter_id, image_input, is_demo=is_demo)

        if success:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE voters 
                SET fingerprint_enrolled = 1,
                    fingerprint_template_hash = ?,
                    fingerprint_feature_path = ?
                WHERE voter_id = ?
            ''', (template_hash, file_path, voter_id))
            conn.commit()
            conn.close()

            log_audit("FINGERPRINT_ENROLLED", f"Fingerprint enrolled for {voter_id}. TemplateHash: {template_hash[:16]}...")
            flash(f"Fingerprint enrolled successfully for {voter_id}!", "success")
            return redirect(url_for('enroll_face_route', voter_id=voter_id))
        else:
            flash(f"Fingerprint enrollment failed: {msg}", "danger")

    return render_template('fingerprint.html', prefill_voter_id=prefill_voter_id)


@app.route('/enroll/face', methods=['GET', 'POST'])
def enroll_face_route():
    """Facial biometric enrollment."""
    prefill_voter_id = request.args.get('voter_id', '')

    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        mode = request.form.get('mode', 'live')
        is_demo = (mode == 'demo') or Config.DEMO_MODE

        voter = get_voter_by_id(voter_id)
        if not voter:
            flash(f"Voter ID '{voter_id}' not found. Please register first.", "danger")
            return render_template('face.html', prefill_voter_id=voter_id)

        image_input = None
        if 'face_file' in request.files and request.files['face_file'].filename != '':
            image_input = request.files['face_file'].read()
        elif request.form.get('webcam_image'):
            image_input = request.form.get('webcam_image')
        elif is_demo:
            image_input = "DEMO"

        success, template_hash, file_path, msg = enroll_face(voter_id, image_input, is_demo=is_demo)

        if success:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE voters 
                SET face_enrolled = 1,
                    face_template_hash = ?,
                    face_feature_path = ?
                WHERE voter_id = ?
            ''', (template_hash, file_path, voter_id))
            conn.commit()
            conn.close()

            log_audit("FACE_ENROLLED", f"Face enrolled for {voter_id}. TemplateHash: {template_hash[:16]}...")
            flash(f"Facial biometrics enrolled successfully for {voter_id}! Both biometric profiles are now active.", "success")
            return redirect(url_for('authenticate_voter', voter_id=voter_id))
        else:
            flash(f"Facial enrollment failed: {msg}", "danger")

    return render_template('face.html', prefill_voter_id=prefill_voter_id)


# -------------------------------------------------------------
# Module 5 & 6: Multimodal Biometric Authentication & Eligibility
# -------------------------------------------------------------
@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate_voter():
    """
    Multimodal Authentication Page:
    Voter provides Voter ID, Fingerprint, and Face.
    Both biometrics must pass to grant access to the voting ballot.
    """
    prefill_voter_id = request.args.get('voter_id', '')
    diagnostics = None

    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        mode = request.form.get('mode', 'live')
        is_demo = (mode == 'demo') or Config.DEMO_MODE

        # Fingerprint input
        fp_input = None
        if 'fingerprint_file' in request.files and request.files['fingerprint_file'].filename != '':
            fp_input = request.files['fingerprint_file'].read()
        elif request.form.get('fingerprint_webcam'):
            fp_input = request.form.get('fingerprint_webcam')
        elif is_demo:
            fp_input = "DEMO"

        # Face input
        face_input = None
        if 'face_file' in request.files and request.files['face_file'].filename != '':
            face_input = request.files['face_file'].read()
        elif request.form.get('face_webcam'):
            face_input = request.form.get('face_webcam')
        elif is_demo:
            face_input = "DEMO"

        authenticated, msg, details = authenticate_multimodal_biometrics(
            voter_id=voter_id,
            fingerprint_input=fp_input,
            face_input=face_input,
            is_demo=is_demo
        )
        diagnostics = details

        if authenticated:
            # Set secure authenticated session
            session['authenticated_voter_id'] = voter_id
            session['voter_session_token'] = details.get('session_token')
            session['voter_name'] = details.get('full_name')
            session['auth_timestamp'] = time.time()

            flash(f"Biometric Verification Passed! Welcome, {details.get('full_name')}.", "success")
            return redirect(url_for('voting_panel'))
        else:
            flash(msg, "danger")

    return render_template('authenticate.html', prefill_voter_id=prefill_voter_id, diagnostics=diagnostics)


@app.route('/eligibility', methods=['GET', 'POST'])
def check_eligibility():
    """Voter eligibility check page."""
    result = None
    voter_id = ""

    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        eligible, msg, voter_data = verify_voter_eligibility(voter_id)
        result = {
            "voter_id": voter_id,
            "eligible": eligible,
            "message": msg,
            "voter": voter_data
        }

    return render_template('eligibility.html', result=result, prefill_voter_id=voter_id)


# -------------------------------------------------------------
# Module 7 & 8 & 10: Voting Panel, Confirmation, and Blockchain Submission
# -------------------------------------------------------------
@app.route('/voting')
@voter_auth_required
def voting_panel():
    """Ballot page displaying all official candidates."""
    voter_id = session.get('authenticated_voter_id')
    voter = get_voter_by_id(voter_id)

    if not voter or voter['has_voted'] == 1:
        session.pop('authenticated_voter_id', None)
        session.pop('voter_session_token', None)
        flash("You have already cast your vote or session is invalid.", "warning")
        return redirect(url_for('index'))

    candidates = get_all_candidates()
    return render_template('voting.html', voter=voter, candidates=candidates)


@app.route('/vote/confirm', methods=['POST'])
@voter_auth_required
def confirm_vote_route():
    """Review candidate choice before final blockchain submission."""
    candidate_id = request.form.get('candidate_id', '').strip()
    voter_id = session.get('authenticated_voter_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates WHERE candidate_id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    conn.close()

    if not candidate:
        flash("Selected candidate not found.", "danger")
        return redirect(url_for('voting_panel'))

    return render_template('confirmation.html', candidate=candidate, voter_id=voter_id)


@app.route('/vote/submit', methods=['POST'])
@voter_auth_required
def submit_vote_route():
    """
    Final vote submission:
    Digitally signs transaction with ECDSA, computes SHA-256 hash,
    and mines the vote block on the blockchain.
    """
    candidate_id = request.form.get('candidate_id', '').strip()
    voter_id = session.get('authenticated_voter_id')

    success, msg, receipt = cast_vote(voter_id=voter_id, candidate_id=candidate_id)

    # Invalidate session immediately after casting ballot
    session.pop('authenticated_voter_id', None)
    session.pop('voter_session_token', None)
    session.pop('voter_name', None)

    if success:
        flash("Vote successfully signed and recorded on the blockchain!", "success")
        return render_template('confirmation.html', receipt=receipt, vote_success=True)
    else:
        flash(f"Vote submission failed: {msg}", "danger")
        return redirect(url_for('index'))


# -------------------------------------------------------------
# Module 9: Blockchain Explorer & Tamper Test
# -------------------------------------------------------------
@app.route('/blockchain')
def blockchain_explorer():
    """Public Blockchain Explorer displaying all mined blocks and transaction hashes."""
    chain = blockchain_instance.chain
    chain_valid, chain_msg, corrupted_idx = blockchain_instance.is_chain_valid()
    candidates = get_all_candidates()

    return render_template(
        'blockchain.html',
        chain=chain,
        chain_valid=chain_valid,
        chain_msg=chain_msg,
        corrupted_idx=corrupted_idx,
        candidates=candidates
    )


@app.route('/blockchain/validate')
def validate_blockchain_route():
    """Trigger blockchain integrity validation."""
    chain_valid, chain_msg, corrupted_idx = blockchain_instance.is_chain_valid()
    if chain_valid:
        flash("Blockchain Integrity Check PASSED! All block hashes, transaction roots, and links are 100% valid.", "success")
    else:
        flash(f"SECURITY ALERT: {chain_msg}", "danger")
    return redirect(url_for('blockchain_explorer'))


@app.route('/admin/blockchain/tamper', methods=['POST'])
@admin_required
def tamper_blockchain_route():
    """Simulate malicious tampering on a recorded block to demonstrate tamper-evidence."""
    block_index = int(request.form.get('block_index', 1))
    fake_candidate = request.form.get('fake_candidate', 'CAND-04')

    success, msg = blockchain_instance.tamper_block_for_demo(block_index, fake_candidate)
    if success:
        flash(f"Block #{block_index} has been altered! Run Validation to witness real-time tamper detection.", "warning")
    else:
        flash(f"Tamper simulation failed: {msg}", "danger")
    return redirect(url_for('blockchain_explorer'))


@app.route('/admin/blockchain/restore', methods=['POST'])
@admin_required
def restore_blockchain_route():
    """Restore block state after demonstration."""
    block_index = int(request.form.get('block_index', 1))
    original_candidate = request.form.get('original_candidate', 'CAND-01')

    blockchain_instance.restore_tampered_block(block_index, original_candidate)
    flash(f"Block #{block_index} restored to original verified state.", "info")
    return redirect(url_for('blockchain_explorer'))


# -------------------------------------------------------------
# Module 11: Election Results
# -------------------------------------------------------------
@app.route('/results')
def election_results():
    """Display final election results, winner declaration, and charts."""
    force_preview = bool(session.get('admin_logged_in'))
    results_data = calculate_election_results(force_preview=force_preview)
    return render_template('results.html', results=results_data)


# -------------------------------------------------------------
# General Pages: Home, About, API
# -------------------------------------------------------------
@app.route('/')
def index():
    """Home landing page."""
    candidates = get_all_candidates()
    election = get_election_state()
    chain_valid, _, _ = blockchain_instance.is_chain_valid()
    return render_template(
        'index.html',
        candidates=candidates,
        election=election,
        chain_valid=chain_valid,
        total_blocks=len(blockchain_instance.chain)
    )


@app.route('/about')
def about():
    """About project architecture, workflow, and technology stack."""
    return render_template('about.html')


@app.route('/api/toggle-demo-mode', methods=['POST'])
def toggle_demo_mode():
    """Toggle demo biometric mode on or off."""
    Config.DEMO_MODE = not Config.DEMO_MODE
    state_str = "ENABLED (Synthetic Biometric Simulators Active)" if Config.DEMO_MODE else "DISABLED (Hardware / Camera Mode Active)"
    flash(f"Biometric Demo Mode is now {state_str}.", "info")
    return redirect(request.referrer or url_for('index'))


@app.route('/api/voter/<voter_id>/status')
def voter_status_api(voter_id):
    """JSON API to fetch voter status."""
    voter = get_voter_by_id(voter_id.upper())
    if not voter:
        return jsonify({"found": False, "message": "Voter ID not registered."}), 404

    return jsonify({
        "found": True,
        "voter_id": voter['voter_id'],
        "full_name": voter['full_name'],
        "age": voter['age'],
        "is_eligible": bool(voter['is_eligible']),
        "has_voted": bool(voter['has_voted']),
        "fingerprint_enrolled": bool(voter['fingerprint_enrolled']),
        "face_enrolled": bool(voter['face_enrolled'])
    })


if __name__ == '__main__':
    print("=" * 70)
    print(" Blockchain-Integrated Multimodal Biometric Electronic Voting System ")
    print(" Final-Year BTech Data Science Capstone Project ")
    print(" Server launching on http://127.0.0.1:5000 ")
    # print(f" Default Admin: {Config.DEFAULT_ADMIN_USER} | Password: {Config.DEFAULT_ADMIN_PASS}")
    print("=" * 70)
    app.run(host='127.0.0.1', port=5000, debug=True)
