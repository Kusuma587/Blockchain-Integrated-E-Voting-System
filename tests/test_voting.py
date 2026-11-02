"""
Unit Tests for Voting & Authentication Module
Verifies voter eligibility, duplicate voting prevention, and ECDSA digital signatures.
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, get_voter_by_id, mark_voter_as_voted, update_election_state
from authentication import verify_voter_eligibility
from signatures import generate_ecdsa_keypair, sign_data, verify_signature
from voting import cast_vote


class TestVoting(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize database before running tests."""
        init_db()
        update_election_state(is_open=1, is_closed=0)

    def test_ecdsa_signature_verification(self):
        """Test ECDSA key generation, signing, and verification."""
        priv_key, pub_key = generate_ecdsa_keypair()
        payload = {
            "candidate_id": "CAND-01",
            "voter_auth_hash": "test_auth_hash",
            "timestamp": time.time()
        }
        sig = sign_data(priv_key, payload)
        self.assertTrue(verify_signature(pub_key, sig, payload))

        # Tampered payload should fail verification
        tampered = payload.copy()
        tampered["candidate_id"] = "CAND-02"
        self.assertFalse(verify_signature(pub_key, sig, tampered))

    def test_underage_voter_ineligibility(self):
        """Test that voter under 18 (VOTER-1004) is marked ineligible."""
        is_eligible, msg, voter_data = verify_voter_eligibility("VOTER-1004")
        self.assertFalse(is_eligible)
        self.assertIn("17", msg)

    def test_unregistered_voter_rejection(self):
        """Test that non-existent voter ID is rejected."""
        is_eligible, msg, _ = verify_voter_eligibility("NON_EXISTENT_VOTER_9999")
        self.assertFalse(is_eligible)
        self.assertIn("not registered", msg)

    def test_duplicate_vote_prevention(self):
        """Test that a voter can only vote once."""
        voter_id = "VOTER-1001"
        voter = get_voter_by_id(voter_id)

        # Cast first vote
        if voter['has_voted'] == 0:
            success, msg, receipt = cast_vote(voter_id, "CAND-01")
            self.assertTrue(success, msg)
            self.assertIn("transaction_hash", receipt)

        # Attempt to cast duplicate second vote
        dup_success, dup_msg, _ = cast_vote(voter_id, "CAND-02")
        self.assertFalse(dup_success)
        self.assertIn("already voted", dup_msg.lower())


if __name__ == '__main__':
    unittest.main()
