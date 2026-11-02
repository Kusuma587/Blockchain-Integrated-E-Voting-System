"""
Multimodal Authentication & Eligibility Verification Module
Coordinates simultaneous Fingerprint & Face Biometric checks,
verifies voter registration and age eligibility, and prevents duplicate voting.
"""

import time
import secrets
from typing import Tuple, Dict, Any
from database import get_voter_by_id, get_election_state, log_audit
from fingerprint import match_fingerprint
from face_recognition_module import match_face
from config import Config


def verify_voter_eligibility(voter_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check registered voter records, age eligibility, and voting status.
    
    Args:
        voter_id: Voter unique ID.
        
    Returns:
        Tuple of (is_eligible: bool, message: str, voter_data: dict)
    """
    voter = get_voter_by_id(voter_id)
    if not voter:
        return False, f"Voter ID '{voter_id}' is not registered in the system.", {}

    voter_dict = dict(voter)

    # 1. Check Election Open Status
    election = get_election_state()
    if not election or election['is_open'] != 1 or election['is_closed'] == 1:
        return False, "Election is currently closed. Voting is not allowed at this time.", voter_dict

    # 2. Check if already voted (Duplicate voting prevention)
    if voter_dict.get('has_voted', 0) == 1:
        log_audit("DUPLICATE_VOTE_ATTEMPT", f"Voter {voter_id} attempted to vote again.", "REJECTED")
        return False, "Access Denied: You have already cast your vote in this election. Duplicate voting is strictly prohibited.", voter_dict

    # 3. Check Age Eligibility
    if voter_dict.get('age', 0) < 18:
        return False, f"Ineligible: Voter is {voter_dict.get('age')} years old. Legal voting age is 18 years or older.", voter_dict

    # 4. Check system eligibility flag
    if voter_dict.get('is_eligible', 0) != 1:
        return False, "Ineligible: Voter registration status is marked as ineligible or pending administrator clearance.", voter_dict

    # 5. Check biometric enrollment status
    if voter_dict.get('fingerprint_enrolled', 0) != 1 or voter_dict.get('face_enrolled', 0) != 1:
        return False, "Biometrics Incomplete: Both fingerprint and facial enrollment must be completed prior to authentication.", voter_dict

    return True, "Voter is eligible and authorized to proceed to biometric authentication.", voter_dict


def authenticate_multimodal_biometrics(
    voter_id: str,
    fingerprint_input=None,
    face_input=None,
    is_demo: bool = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Execute Multimodal Biometric Fusion:
    Both Fingerprint and Facial recognition must pass simultaneously.
    If either fails, authentication is rejected.
    
    Args:
        voter_id: Voter unique ID.
        fingerprint_input: Query fingerprint image data / base64 / 'DEMO'.
        face_input: Query face image data / base64 / 'DEMO'.
        is_demo: Toggle demo mode. Defaults to Config.DEMO_MODE.
        
    Returns:
        Tuple of (authenticated: bool, status_message: str, details_dict: dict)
    """
    if is_demo is None:
        is_demo = Config.DEMO_MODE

    # First verify registration and eligibility
    eligible, elig_msg, voter_data = verify_voter_eligibility(voter_id)
    if not eligible:
        return False, elig_msg, {"eligibility_passed": False, "reason": elig_msg}

    # 1. Execute Fingerprint Biometric Check
    fp_match, fp_score, fp_matches_count, fp_msg = match_fingerprint(
        voter_id=voter_id,
        query_image_input=fingerprint_input,
        is_demo=is_demo
    )

    # 2. Execute Facial Recognition Biometric Check
    face_match, face_score, face_msg = match_face(
        voter_id=voter_id,
        query_image_input=face_input,
        is_demo=is_demo
    )

    # Compile detailed multimodal diagnostics
    diagnostics = {
        "voter_id": voter_id,
        "full_name": voter_data.get("full_name"),
        "fingerprint": {
            "passed": fp_match,
            "score": fp_score,
            "minutiae_matches": fp_matches_count,
            "message": fp_msg
        },
        "face": {
            "passed": face_match,
            "confidence": face_score,
            "message": face_msg
        },
        "mode": "DEMO MODE (Sample Pattern Matching)" if is_demo else "LIVE BIOMETRIC HARDWARE MODE",
        "timestamp": time.time()
    }

    # Multimodal Fusion Rule: BOTH MUST PASS
    if fp_match and face_match:
        # Generate temporary authenticated voting session token
        session_token = secrets.token_hex(24)
        diagnostics["session_token"] = session_token
        diagnostics["authenticated"] = True

        log_audit(
            "MULTIMODAL_AUTH_SUCCESS",
            f"Voter {voter_id} authenticated (FP score: {fp_score}, Face conf: {face_score:.2f})",
            "SUCCESS"
        )
        return True, "Multimodal Biometric Authentication Successful! Both fingerprint and facial verification passed.", diagnostics
    else:
        failure_reasons = []
        if not fp_match:
            failure_reasons.append("Fingerprint verification failed")
        if not face_match:
            failure_reasons.append("Facial recognition verification failed")

        fail_summary = " & ".join(failure_reasons)
        diagnostics["authenticated"] = False
        log_audit(
            "MULTIMODAL_AUTH_FAILED",
            f"Voter {voter_id} failed: {fail_summary}",
            "REJECTED"
        )
        return False, f"Authentication Rejected: {fail_summary}. Both biometrics are strictly required to proceed.", diagnostics
