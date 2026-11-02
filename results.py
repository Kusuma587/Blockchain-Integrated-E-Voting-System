"""
Election Results & Analytics Module
Computes candidate vote tallies, identifies the winner, cross-validates
database counts against blockchain on-chain records, and prepares chart datasets.
"""

from typing import Dict, Any, List
from database import get_all_candidates, get_election_state, get_db_connection
from blockchain import blockchain_instance


def calculate_election_results(force_preview: bool = False) -> Dict[str, Any]:
    """
    Compute election outcome and cross-validate on-chain blockchain transactions with database records.
    
    Args:
        force_preview: If True (e.g. for admin), calculates tallies even if election is open.
        
    Returns:
        Dictionary containing winners, candidate breakdown, blockchain audit, and chart data.
    """
    election = get_election_state()
    is_closed = bool(election['is_closed']) if election else False
    is_open = bool(election['is_open']) if election else True

    # 1. Cross-validate Blockchain Integrity First
    chain_valid, chain_msg, corrupted_idx = blockchain_instance.is_chain_valid()

    # 2. Extract on-chain vote counts directly from the blockchain blocks
    on_chain_tallies = blockchain_instance.count_votes_from_chain()

    # 3. Retrieve candidates from SQLite
    candidates_rows = get_all_candidates()
    candidate_list = []
    total_votes = 0

    # Palette of professional colors for charts
    chart_colors = [
        {"bg": "rgba(59, 130, 246, 0.8)", "border": "#2563eb"},
        {"bg": "rgba(16, 185, 129, 0.8)", "border": "#059669"},
        {"bg": "rgba(245, 158, 11, 0.8)", "border": "#d97706"},
        {"bg": "rgba(139, 92, 246, 0.8)", "border": "#7c3aed"},
        {"bg": "rgba(236, 72, 153, 0.8)", "border": "#db2777"},
        {"bg": "rgba(20, 184, 166, 0.8)", "border": "#0d9488"}
    ]

    for idx, cand in enumerate(candidates_rows):
        cid = cand['candidate_id']
        db_votes = cand['vote_count']
        # On-chain tally from blockchain blocks
        chain_votes = on_chain_tallies.get(cid, 0)

        # Audit check: does database match on-chain blocks?
        is_synchronized = (db_votes == chain_votes)
        total_votes += db_votes

        candidate_list.append({
            "id": cand['id'],
            "candidate_id": cid,
            "name": cand['name'],
            "party": cand['party'],
            "symbol": cand['symbol'],
            "manifesto": cand['manifesto'],
            "db_votes": db_votes,
            "chain_votes": chain_votes,
            "is_synchronized": is_synchronized,
            "percentage": 0.0,
            "color": chart_colors[idx % len(chart_colors)]
        })

    # Calculate percentages
    for cand in candidate_list:
        if total_votes > 0:
            cand["percentage"] = round((cand["db_votes"] / total_votes) * 100, 2)
        else:
            cand["percentage"] = 0.0

    # Sort candidates by vote count descending
    sorted_candidates = sorted(candidate_list, key=lambda x: x["db_votes"], reverse=True)

    winner = None
    is_tie = False
    if total_votes > 0 and len(sorted_candidates) > 0:
        top_votes = sorted_candidates[0]["db_votes"]
        if len(sorted_candidates) > 1 and sorted_candidates[1]["db_votes"] == top_votes:
            is_tie = True
            winner = None
        else:
            winner = sorted_candidates[0]

    # Voter Turnout stats
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total_registered, SUM(has_voted) as total_voted, SUM(is_eligible) as total_eligible FROM voters')
    voter_stats = cursor.fetchone()
    conn.close()

    total_registered = voter_stats['total_registered'] or 0
    total_voted = voter_stats['total_voted'] or 0
    total_eligible = voter_stats['total_eligible'] or 0
    turnout_pct = round((total_voted / max(total_eligible, 1)) * 100, 2) if total_eligible > 0 else 0.0

    # Chart.js dataset formatting
    chart_labels = [c["name"] for c in sorted_candidates]
    chart_data = [c["db_votes"] for c in sorted_candidates]
    chart_backgrounds = [c["color"]["bg"] for c in sorted_candidates]
    chart_borders = [c["color"]["border"] for c in sorted_candidates]

    return {
        "is_closed": is_closed,
        "is_open": is_open,
        "election_title": election['title'] if election else "General Election",
        "started_at": election['started_at'] if election else None,
        "ended_at": election['ended_at'] if election else None,
        "total_votes": total_votes,
        "total_registered": total_registered,
        "total_eligible": total_eligible,
        "total_voted": total_voted,
        "turnout_percentage": turnout_pct,
        "candidates": sorted_candidates,
        "winner": winner,
        "is_tie": is_tie,
        "blockchain_status": {
            "is_valid": chain_valid,
            "message": chain_msg,
            "corrupted_block_index": corrupted_idx,
            "total_blocks": len(blockchain_instance.chain),
            "latest_hash": blockchain_instance.get_latest_block().current_hash
        },
        "chart": {
            "labels": chart_labels,
            "data": chart_data,
            "backgrounds": chart_backgrounds,
            "borders": chart_borders
        }
    }
