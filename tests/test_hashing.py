"""
Unit Tests for SHA-256 Hashing Module
Verifies deterministic hashing, avalanche effect, and transaction hashing.
"""

import unittest
import sys
import os

# Include parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hashing import generate_sha256, hash_transaction, hash_biometric_template, verify_hash


class TestHashing(unittest.TestCase):

    def test_sha256_reproducibility(self):
        """Test that identical input always produces identical SHA-256 hash."""
        data = "Electronic_Voting_2026"
        hash1 = generate_sha256(data)
        hash2 = generate_sha256(data)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_avalanche_effect(self):
        """Test that a single character modification drastically alters the output hash."""
        input_a = "Voter_1001_CAND_01"
        input_b = "Voter_1001_CAND_02"
        hash_a = generate_sha256(input_a)
        hash_b = generate_sha256(input_b)
        self.assertNotEqual(hash_a, hash_b)
        # Check that more than 30 characters differ (avalanche criterion)
        diff_count = sum(1 for a, b in zip(hash_a, hash_b) if a != b)
        self.assertGreater(diff_count, 30)

    def test_transaction_hash_deterministic(self):
        """Test that key ordering in dictionary does not change transaction hash."""
        dict1 = {"candidate_id": "CAND-01", "timestamp": 1700000000.0, "voter_auth_hash": "abc"}
        dict2 = {"voter_auth_hash": "abc", "candidate_id": "CAND-01", "timestamp": 1700000000.0}
        self.assertEqual(hash_transaction(dict1), hash_transaction(dict2))

    def test_biometric_template_hashing(self):
        """Test numeric list biometric vector hashing."""
        vector = [0.1234567, 0.9876543, -0.4567891]
        hash_val = hash_biometric_template(vector)
        self.assertIsInstance(hash_val, str)
        self.assertEqual(len(hash_val), 64)

    def test_verify_hash(self):
        """Test verify_hash function."""
        text = "Tamper_Evident_Ledger"
        expected = generate_sha256(text)
        self.assertTrue(verify_hash(text, expected))
        self.assertFalse(verify_hash("Tamper_Evident_Ledger_Modified", expected))


if __name__ == '__main__':
    unittest.main()
