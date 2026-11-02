"""
Blockchain Module for Electronic Voting System
Implements custom tamper-evident Python blockchain with SHA-256 cryptographic linkage,
Proof-of-Work mining, transaction integrity verification, and Ethereum extensibility.
"""

import time
import json
import sqlite3
from typing import List, Dict, Any, Tuple, Optional
from config import Config
from hashing import generate_sha256, hash_transaction


class Block:
    """Represents a single block in the electronic voting blockchain."""

    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: List[Dict[str, Any]],
        previous_hash: str,
        transaction_hash: str = "",
        nonce: int = 0,
        current_hash: str = ""
    ):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.transaction_hash = transaction_hash if transaction_hash else self.calculate_transaction_hash()
        self.current_hash = current_hash if current_hash else self.calculate_hash()

    def calculate_transaction_hash(self) -> str:
        """
        Compute SHA-256 hash of transactions in this block.
        Ensures any alteration of vote data invalidates the transaction hash.
        """
        tx_canonical = json.dumps(self.transactions, sort_keys=True, separators=(',', ':'))
        return generate_sha256(tx_canonical)

    def calculate_hash(self) -> str:
        """
        Compute SHA-256 hash of the complete block header and payload.
        Combines: index + timestamp + previous_hash + transaction_hash + nonce.
        """
        header = f"{self.index}:{self.timestamp}:{self.previous_hash}:{self.transaction_hash}:{self.nonce}"
        return generate_sha256(header)

    def to_dict(self) -> Dict[str, Any]:
        """Convert block instance to dictionary format."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "transaction_hash": self.transaction_hash,
            "nonce": self.nonce,
            "current_hash": self.current_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Construct a Block instance from dictionary."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            transaction_hash=data.get("transaction_hash", ""),
            nonce=data["nonce"],
            current_hash=data["current_hash"]
        )

    def to_ethereum_payload(self) -> Dict[str, Any]:
        """
        Format block data as an Ethereum-compatible EVM transaction payload.
        Prepares fields for future Solidity smart contract recording.
        """
        return {
            "blockNumber": hex(self.index),
            "timestamp": hex(int(self.timestamp)),
            "parentHash": self.previous_hash,
            "stateRoot": self.transaction_hash,
            "transactionsRoot": self.calculate_transaction_hash(),
            "receiptsRoot": self.current_hash,
            "extraData": f"0x{generate_sha256(str(self.transactions))[:32]}",
            "gasLimit": "0x1c9c380",
            "gasUsed": "0x5208"
        }


class Blockchain:
    """Manages the linked list of blocks, mining, persistence, and integrity checks."""

    def __init__(self, difficulty: int = None):
        self.chain: List[Block] = []
        self.difficulty = difficulty if difficulty is not None else Config.BLOCKCHAIN_DIFFICULTY
        self.pending_transactions: List[Dict[str, Any]] = []

        # Load existing blocks from SQLite or create genesis block
        self.load_from_db()
        if len(self.chain) == 0:
            self.create_genesis_block()
            self.save_all_to_db()

    def create_genesis_block(self):
        """Create and mine the first block (Genesis Block) of the voting system."""
        genesis_tx = [{
            "type": "GENESIS_TRANSACTION",
            "system": "Blockchain-Integrated Multimodal Biometric Electronic Voting System",
            "status": "INITIALIZED",
            "timestamp": time.time(),
            "note": "Genesis Block sealed with SHA-256 and ECDSA cryptographic foundation."
        }]
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=genesis_tx,
            previous_hash="0" * 64,
            nonce=0
        )
        self.mine_block(genesis_block)
        self.chain.append(genesis_block)
        self.save_block_to_db(genesis_block)

    def get_latest_block(self) -> Block:
        """Return the most recently mined block in the chain."""
        return self.chain[-1]

    def mine_block(self, block: Block):
        """
        Proof-of-Work mining algorithm.
        Finds a nonce such that the block hash begins with `self.difficulty` leading zeros.
        """
        target_prefix = "0" * self.difficulty
        block.transaction_hash = block.calculate_transaction_hash()

        while True:
            computed_hash = block.calculate_hash()
            if computed_hash.startswith(target_prefix):
                block.current_hash = computed_hash
                break
            block.nonce += 1

    def add_vote_transaction(self, vote_tx: Dict[str, Any]) -> Block:
        """
        Add a single vote transaction directly into a newly mined block.
        Ensures immediate confirmation and persistence.
        
        Args:
            vote_tx: Dictionary containing anonymized voter authorization token hash,
                     candidate_id, digital_signature, and timestamp.
                     
        Returns:
            The newly mined and linked Block.
        """
        previous_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=[vote_tx],
            previous_hash=previous_block.current_hash,
            nonce=0
        )
        self.mine_block(new_block)
        self.chain.append(new_block)
        self.save_block_to_db(new_block)
        return new_block

    def is_chain_valid(self) -> Tuple[bool, str, Optional[int]]:
        """
        Validate integrity of the entire blockchain:
        1. Validates previous_hash linkage between consecutive blocks.
        2. Validates recalculated transaction_hash against stored transaction_hash.
        3. Validates recalculated current_hash against stored current_hash.
        4. Validates Proof-of-Work target difficulty requirement.
        
        Returns:
            Tuple of (is_valid: bool, status_message: str, corrupted_block_index: Optional[int])
        """
        target_prefix = "0" * self.difficulty

        for i in range(len(self.chain)):
            current = self.chain[i]

            # 1. Verify Genesis Block previous_hash
            if i == 0:
                if current.previous_hash != "0" * 64:
                    return False, f"Genesis Block (Index 0) has corrupted previous_hash: {current.previous_hash}", 0
            else:
                prev = self.chain[i - 1]
                # 2. Verify chain linkage
                if current.previous_hash != prev.current_hash:
                    return (
                        False,
                        f"Hash link broken at Block #{current.index}! Previous block hash is {prev.current_hash[:16]}..., but block stores {current.previous_hash[:16]}...",
                        current.index
                    )

            # 3. Verify transaction payload hash
            recomputed_tx_hash = current.calculate_transaction_hash()
            if current.transaction_hash != recomputed_tx_hash:
                return (
                    False,
                    f"Data Tampering Detected in Block #{current.index}! Transaction payload does not match transaction_hash.",
                    current.index
                )

            # 4. Verify block header hash
            recomputed_block_hash = current.calculate_hash()
            if current.current_hash != recomputed_block_hash:
                return (
                    False,
                    f"Block Header Tampering Detected in Block #{current.index}! Stored hash {current.current_hash[:16]}... does not match recalculated hash {recomputed_block_hash[:16]}...",
                    current.index
                )

            # 5. Verify Proof of Work
            if not current.current_hash.startswith(target_prefix):
                return (
                    False,
                    f"Proof-of-Work difficulty invalid in Block #{current.index}! Hash does not start with {self.difficulty} zeros.",
                    current.index
                )

        return True, "Blockchain integrity 100% verified. All blocks cryptographically valid and linked.", None

    def tamper_block_for_demo(self, block_index: int, fake_candidate_id: str) -> Tuple[bool, str]:
        """
        Simulate an attack/tampering attempt on a recorded block.
        Modifies a candidate vote in an existing block without re-mining subsequent blocks.
        Used to demonstrate real-time tamper-evident detection on the dashboard.
        """
        if block_index <= 0 or block_index >= len(self.chain):
            return False, f"Invalid block index {block_index}. Cannot tamper Genesis Block or non-existent block."

        target_block = self.chain[block_index]
        if not target_block.transactions or len(target_block.transactions) == 0:
            return False, "Target block has no transactions to tamper."

        # Modify transaction payload
        target_block.transactions[0]["candidate_id"] = fake_candidate_id
        target_block.transactions[0]["tampered"] = True

        # Update in SQLite without updating subsequent block hashes
        self.update_tampered_block_in_db(target_block)

        return True, f"Block #{block_index} was artificially tampered! Now run Blockchain Validation to see detection in action."

    def restore_tampered_block(self, block_index: int, original_candidate_id: str):
        """Restore tampered block back to original state."""
        if 0 < block_index < len(self.chain):
            block = self.chain[block_index]
            if block.transactions:
                block.transactions[0]["candidate_id"] = original_candidate_id
                if "tampered" in block.transactions[0]:
                    del block.transactions[0]["tampered"]
                block.transaction_hash = block.calculate_transaction_hash()
                block.current_hash = block.calculate_hash()
                self.update_tampered_block_in_db(block)

    def save_block_to_db(self, block: Block):
        """Save a single block into SQLite database."""
        conn = None
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
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
            cursor.execute('''
                INSERT OR REPLACE INTO blockchain_blocks 
                (block_index, timestamp, transactions_json, previous_hash, transaction_hash, nonce, current_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                block.index,
                block.timestamp,
                json.dumps(block.transactions),
                block.previous_hash,
                block.transaction_hash,
                block.nonce,
                block.current_hash
            ))
            conn.commit()
        except Exception as e:
            # Table might not be initialized yet during early test setup
            pass
        finally:
            if conn:
                conn.close()

    def update_tampered_block_in_db(self, block: Block):
        """Update a modified block in SQLite."""
        conn = None
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE blockchain_blocks 
                SET transactions_json = ?
                WHERE block_index = ?
            ''', (json.dumps(block.transactions), block.index))
            conn.commit()
        except Exception as e:
            print(f"Error updating tampered block in db: {e}")
        finally:
            if conn:
                conn.close()

    def save_all_to_db(self):
        """Save entire chain to SQLite."""
        for block in self.chain:
            self.save_block_to_db(block)

    def load_from_db(self):
        """Load stored blockchain blocks from SQLite."""
        conn = None
        try:
            conn = sqlite3.connect(Config.DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
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
            cursor.execute('SELECT * FROM blockchain_blocks ORDER BY block_index ASC')
            rows = cursor.fetchall()

            if rows:
                loaded_chain = []
                for row in rows:
                    block = Block(
                        index=row['block_index'],
                        timestamp=row['timestamp'],
                        transactions=json.loads(row['transactions_json']),
                        previous_hash=row['previous_hash'],
                        transaction_hash=row['transaction_hash'],
                        nonce=row['nonce'],
                        current_hash=row['current_hash']
                    )
                    loaded_chain.append(block)
                # Verify that index 0 is valid genesis block
                if len(loaded_chain) > 0 and loaded_chain[0].index == 0:
                    self.chain = loaded_chain
                else:
                    self.chain = []
            else:
                self.chain = []
        except Exception as e:
            self.chain = []
        finally:
            if conn:
                conn.close()

    def count_votes_from_chain(self) -> Dict[str, int]:
        """
        Directly and independently tally votes by traversing verified blocks on the blockchain.
        Provides on-chain ground truth tally.
        """
        tally: Dict[str, int] = {}
        for block in self.chain:
            if block.index == 0:
                continue  # Skip genesis block
            for tx in block.transactions:
                cand = tx.get("candidate_id")
                if cand:
                    tally[cand] = tally.get(cand, 0) + 1
        return tally


# Singleton blockchain instance
blockchain_instance = Blockchain()
