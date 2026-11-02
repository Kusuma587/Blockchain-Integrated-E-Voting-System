"""
Unit Tests for Blockchain Module
Verifies genesis block, block addition, proof-of-work, chain validation, and tamper detection.
"""

import unittest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockchain import Block, Blockchain


class TestBlockchain(unittest.TestCase):

    def setUp(self):
        """Set up a fresh test blockchain instance with difficulty 2 in memory."""
        self.blockchain = Blockchain(difficulty=2)
        # Prevent in-memory test tampering from persisting to disk
        self.blockchain.save_block_to_db = lambda block: None
        self.blockchain.update_tampered_block_in_db = lambda block: None
        self.blockchain.chain = []
        self.blockchain.create_genesis_block()

    def test_genesis_block(self):
        """Test genesis block properties."""
        genesis = self.blockchain.chain[0]
        self.assertEqual(genesis.index, 0)
        self.assertEqual(genesis.previous_hash, "0" * 64)
        self.assertTrue(genesis.current_hash.startswith("00"))

    def test_add_block_and_mining(self):
        """Test adding a block with proof-of-work mining."""
        tx = {
            "tx_hash": "testhash123",
            "candidate_id": "CAND-01",
            "voter_auth_hash": "voterhash456",
            "timestamp": time.time()
        }
        initial_len = len(self.blockchain.chain)
        new_block = self.blockchain.add_vote_transaction(tx)

        self.assertEqual(len(self.blockchain.chain), initial_len + 1)
        self.assertEqual(new_block.index, initial_len)
        self.assertEqual(new_block.previous_hash, self.blockchain.chain[initial_len - 1].current_hash)
        self.assertTrue(new_block.current_hash.startswith("00"))

    def test_valid_chain(self):
        """Test that unmodified chain passes validation."""
        tx1 = {"candidate_id": "CAND-01", "voter_auth_hash": "vh1", "timestamp": time.time()}
        tx2 = {"candidate_id": "CAND-02", "voter_auth_hash": "vh2", "timestamp": time.time()}
        self.blockchain.add_vote_transaction(tx1)
        self.blockchain.add_vote_transaction(tx2)

        is_valid, msg, _ = self.blockchain.is_chain_valid()
        self.assertTrue(is_valid, msg)

    def test_tamper_detection_transaction_payload(self):
        """Test that modifying a transaction payload is immediately detected."""
        tx = {"candidate_id": "CAND-01", "voter_auth_hash": "voter1", "timestamp": time.time()}
        self.blockchain.add_vote_transaction(tx)

        # Maliciously tamper with candidate in Block #1
        self.blockchain.chain[1].transactions[0]["candidate_id"] = "CAND-02"

        is_valid, msg, corrupted_index = self.blockchain.is_chain_valid()
        self.assertFalse(is_valid)
        self.assertEqual(corrupted_index, 1)
        self.assertIn("Data Tampering Detected", msg)

    def test_tamper_detection_broken_link(self):
        """Test that altering previous_hash breaks chain linkage."""
        tx1 = {"candidate_id": "CAND-01", "voter_auth_hash": "v1", "timestamp": time.time()}
        tx2 = {"candidate_id": "CAND-02", "voter_auth_hash": "v2", "timestamp": time.time()}
        self.blockchain.add_vote_transaction(tx1)
        self.blockchain.add_vote_transaction(tx2)

        # Alter previous_hash in Block #2
        self.blockchain.chain[2].previous_hash = "f" * 64

        is_valid, msg, corrupted_index = self.blockchain.is_chain_valid()
        self.assertFalse(is_valid)
        self.assertEqual(corrupted_index, 2)
        self.assertIn("Hash link broken", msg)


if __name__ == '__main__':
    unittest.main()
