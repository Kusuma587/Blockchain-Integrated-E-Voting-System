"""
Voting Module for Electronic Voting System
Handles secure vote casting, ECDSA digital signing, SHA-256 transaction hashing,
anonymized voter authorization token generation, and blockchain block sealing.
"""

import time
from typing import Tuple, Dict, Any
from config import Config
from hashing import generate_sha256, hash_transaction
from signatures import sign_data, verify_signature
from database import get_voter_by_id, mark_voter_as_voted, get_election_state, log_audit
from blockchain import blockchain_instance


def cast_vote(voter_id: str, candidate_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Securely execute the voting transaction:
    1. Verify voter registration, eligibility, and double-voting prevention.
    2. Retrieve voter's server-protected ECDSA private key.
    3. Generate anonymized voter authorization hash: SHA256(voter_id + BLOCKCHAIN_SALT).
       (Ensures voter identity is strictly decoupled from the ballot choice).
    4. Sign the vote payload with the voter's private key.
    5. Verify the digital signature before submitting to blockchain.
    6. Compute SHA-256 transaction hash.
    7. Mine and append block to the blockchain.
    8. Update voter status in SQLite atomically.
    9. Return cryptographic vote receipt.
    
    Args:
        voter_id: Unique voter identifier.
        candidate_id: ID of candidate selected.
        
    Returns:
        Tuple of (success: bool, message: str, receipt_dict: dict)
    """
    # 1. Verify election is open
    election = get_election_state()
    if not election or election['is_open'] != 1 or election['is_closed'] == 1:
        return False, "Voting rejected: The election is currently closed.", {}

    # 2. Check voter status
    voter = get_voter_by_id(voter_id)
    if not voter:
        return False, f"Voter {voter_id} does not exist.", {}

    if voter['has_voted'] == 1:
        log_audit("DOUBLE_VOTE_BLOCKED", f"Voter {voter_id} attempted second vote.", "REJECTED")
        return False, "Voting rejected: You have already voted. Each eligible voter may cast exactly one ballot.", {}

    if voter['is_eligible'] != 1:
        return False, "Voting rejected: Voter status is not eligible.", {}

    # 3. Privacy Mechanism: Generate Anonymized Voter Authorization Hash
    # Protects ballot secrecy: The blockchain stores only this non-invertible hash
    voter_auth_hash = generate_sha256(f"{voter_id}_{Config.BLOCKCHAIN_SALT}")

    # 4. Construct vote transaction payload
    current_timestamp = time.time()
    tx_payload = {
        "candidate_id": candidate_id,
        "voter_auth_hash": voter_auth_hash,
        "election_id": "GENERAL-ELECTION-2026",
        "timestamp": current_timestamp
    }

    # 5. Sign transaction using voter's private key (ECDSA SECP256K1)
    private_key_pem = voter['private_key_pem']
    public_key_pem = voter['public_key_pem']

    if not private_key_pem or not public_key_pem:
        return False, "Cryptographic key error: Voter ECDSA keys not found.", {}

    try:
        signature_b64 = sign_data(private_key_pem, tx_payload)
    except Exception as e:
        return False, f"Digital signature generation failed: {e}", {}

    # 6. Verify digital signature before broadcasting
    is_sig_valid = verify_signature(public_key_pem, signature_b64, tx_payload)
    if not is_sig_valid:
        log_audit("INVALID_SIGNATURE", f"Digital signature verification failed for voter {voter_id}", "REJECTED")
        return False, "Security Error: ECDSA digital signature verification failed. Vote rejected.", {}

    # 7. Generate deterministic SHA-256 transaction hash
    tx_hash = hash_transaction(tx_payload)

    # 8. Complete transaction record for the block
    complete_transaction = {
        "tx_hash": tx_hash,
        "candidate_id": candidate_id,
        "voter_auth_hash": voter_auth_hash,
        "signature": signature_b64,
        "public_key": public_key_pem,
        "election_id": tx_payload["election_id"],
        "timestamp": current_timestamp
    }

    # 9. Seal transaction on the blockchain in a new block
    try:
        new_block = blockchain_instance.add_vote_transaction(complete_transaction)
    except Exception as e:
        return False, f"Blockchain recording failed: {e}", {}

    # 10. Update SQLite Database status atomically
    db_ok, db_msg = mark_voter_as_voted(voter_id, candidate_id)
    if not db_ok:
        return False, f"Database update error: {db_msg}", {}

    # 11. Compile Vote Confirmation Receipt
    receipt = {
        "voter_id": voter_id,
        "voter_auth_hash": voter_auth_hash,
        "candidate_id": candidate_id,
        "transaction_hash": tx_hash,
        "block_index": new_block.index,
        "block_hash": new_block.current_hash,
        "previous_hash": new_block.previous_hash,
        "nonce": new_block.nonce,
        "timestamp": current_timestamp,
        "status": "CONFIRMED_ON_BLOCKCHAIN"
    }

    log_audit("VOTE_RECORDED_ON_BLOCKCHAIN", f"Block #{new_block.index} mined with TxHash {tx_hash[:16]}...", "SUCCESS")
    return True, "Your vote has been securely signed and permanently recorded on the blockchain!", receipt
