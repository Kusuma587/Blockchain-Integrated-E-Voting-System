"""
End-to-End Integration Test for
Blockchain-Integrated Multimodal Biometric Electronic Voting System
Tests complete 17-step workflow via Flask TestClient.
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import init_db, get_voter_by_id, get_all_candidates
from blockchain import blockchain_instance
from config import Config


class TestEndToEndWorkflow(unittest.TestCase):

    def setUp(self):
        """Set up Flask test client and ensure test database is ready."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            init_db()

    def test_01_home_and_about_pages(self):
        """Test public informational pages."""
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"Blockchain-Integrated Multimodal Biometric", res_home.data)

        res_about = self.client.get('/about')
        self.assertEqual(res_about.status_code, 200)
        self.assertIn(b"Technology Stack", res_about.data)

    def test_02_admin_authentication_and_dashboard(self):
        """Test admin login and access to admin dashboard."""
        # Bad login
        res_bad = self.client.post('/admin/login', data={'username': 'admin', 'password': 'WrongPassword'})
        self.assertEqual(res_bad.status_code, 200)
        self.assertIn(b"Invalid administrator credentials", res_bad.data)

        # Good login
        res_good = self.client.post('/admin/login', data={'username': 'admin', 'password': Config.DEFAULT_ADMIN_PASS}, follow_redirects=True)
        self.assertEqual(res_good.status_code, 200)
        self.assertIn(b"Election Authority Dashboard", res_good.data)

    def test_03_voter_registration_workflow(self):
        """Test new voter registration."""
        unique_suffix = str(int(time.time() * 1000))[-5:]
        self.test_voter_id = f"VOTER-T{unique_suffix}"
        voter_payload = {
            'voter_id': self.test_voter_id,
            'full_name': 'Vikramaditya Rao',
            'age': '25',
            'email': f'vikram.{unique_suffix}@example.com',
            'mobile': '9811223344'
        }
        res = self.client.post('/register', data=voter_payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Fingerprint Biometric Enrollment", res.data)

        # Verify voter exists in database
        voter = get_voter_by_id(self.test_voter_id)
        self.assertIsNotNone(voter)
        self.assertEqual(voter['full_name'], 'Vikramaditya Rao')
        self.assertEqual(voter['is_eligible'], 1)
        self.assertIsNotNone(voter['public_key_pem'])

    def test_04_biometric_enrollment(self):
        """Test enrolling fingerprint and face for newly registered voter in Demo mode."""
        unique_suffix = str(int(time.time() * 1000))[-5:]
        voter_id = f"VOTER-E{unique_suffix}"
        
        # Register voter first
        self.client.post('/register', data={
            'voter_id': voter_id,
            'full_name': 'Biometric Test Voter',
            'age': '29',
            'email': f'bio.{unique_suffix}@example.com',
            'mobile': '9822334455'
        })

        # 1. Fingerprint Enrollment
        fp_res = self.client.post('/enroll/fingerprint', data={
            'voter_id': voter_id,
            'mode': 'demo'
        }, follow_redirects=True)
        self.assertEqual(fp_res.status_code, 200)
        self.assertIn(b"Facial Biometric Enrollment", fp_res.data)

        # 2. Face Enrollment
        face_res = self.client.post('/enroll/face', data={
            'voter_id': voter_id,
            'mode': 'demo'
        }, follow_redirects=True)
        self.assertEqual(face_res.status_code, 200)
        self.assertIn(b"Multimodal Biometric Voter Authentication", face_res.data)

        # Check voter biometrics in DB
        voter = get_voter_by_id(voter_id)
        self.assertEqual(voter['fingerprint_enrolled'], 1)
        self.assertEqual(voter['face_enrolled'], 1)

    def test_05_multimodal_authentication_and_voting(self):
        """Test voter authentication, ballot display, vote confirmation, and blockchain recording."""
        unique_suffix = str(int(time.time() * 1000))[-5:]
        voter_id = f"VOTER-V{unique_suffix}"

        # Register and enroll voter
        self.client.post('/register', data={
            'voter_id': voter_id,
            'full_name': 'Voting Test Voter',
            'age': '30',
            'email': f'voter.{unique_suffix}@example.com',
            'mobile': '9833445566'
        })
        self.client.post('/enroll/fingerprint', data={'voter_id': voter_id, 'mode': 'demo'})
        self.client.post('/enroll/face', data={'voter_id': voter_id, 'mode': 'demo'})

        # 1. Authenticate via multimodal biometrics
        auth_res = self.client.post('/authenticate', data={
            'voter_id': voter_id,
            'mode': 'demo'
        }, follow_redirects=True)
        self.assertEqual(auth_res.status_code, 200)
        self.assertIn(b"Official Electronic Ballot", auth_res.data)

        # 2. Review vote confirmation
        cand_id = 'CAND-02'
        confirm_res = self.client.post('/vote/confirm', data={'candidate_id': cand_id})
        self.assertEqual(confirm_res.status_code, 200)
        self.assertIn(b"Confirm Your Ballot Choice", confirm_res.data)

        # 3. Final vote submission onto blockchain
        submit_res = self.client.post('/vote/submit', data={'candidate_id': cand_id})
        self.assertEqual(submit_res.status_code, 200)
        self.assertIn(b"Vote Cast & Recorded Successfully!", submit_res.data)
        self.assertIn(b"Immutable Blockchain Receipt", submit_res.data)

        # 4. Attempt duplicate voting with same voter -> MUST FAIL
        dup_auth = self.client.post('/authenticate', data={
            'voter_id': voter_id,
            'mode': 'demo'
        }, follow_redirects=True)
        self.assertEqual(dup_auth.status_code, 200)
        self.assertIn(b"already cast your vote", dup_auth.data.lower())

    def test_06_blockchain_explorer_and_integrity(self):
        """Test blockchain explorer page and validation route."""
        res = self.client.get('/blockchain')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Decentralized Blockchain Explorer", res.data)

        val_res = self.client.get('/blockchain/validate', follow_redirects=True)
        self.assertEqual(val_res.status_code, 200)
        self.assertIn(b"Blockchain Integrity Check PASSED", val_res.data)

    def test_07_election_results_page(self):
        """Test election results calculations and charts rendering."""
        res = self.client.get('/results')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Official Election Results", res.data)
        self.assertIn(b"Dual-Layer Verification Audit Table", res.data)


if __name__ == '__main__':
    unittest.main()
