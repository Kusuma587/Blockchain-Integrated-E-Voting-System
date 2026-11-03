"""
Unit and Integration Tests for Vercel Deployment Configuration
Verifies that api/index.py loads the Flask application, executes under serverless conditions,
and all key endpoints render properly in simulated Vercel environments.
"""

import unittest
import sys
import os

# Ensure repo root is on sys.path so 'api.index' can be imported
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class TestVercelDeployment(unittest.TestCase):

    def test_01_api_entrypoint_import(self):
        """Test that api/index.py successfully exposes the Flask app object."""
        from api.index import app as vercel_app
        self.assertIsNotNone(vercel_app)
        self.assertEqual(vercel_app.name, 'app')

    def test_02_serverless_config_resolution(self):
        """Test that serverless detection correctly configures /tmp storage."""
        from config import Config
        self.assertTrue(hasattr(Config, 'IS_SERVERLESS'))
        self.assertTrue(hasattr(Config, 'DATABASE_PATH'))
        self.assertTrue(hasattr(Config, 'UPLOAD_FOLDER'))

    def test_03_vercel_client_routes(self):
        """Test that all key endpoints render successfully through the Vercel WSGI entry point."""
        from api.index import app as vercel_app
        vercel_app.config['TESTING'] = True
        client = vercel_app.test_client()

        # Home
        res_home = client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"BioChain", res_home.data)

        # About
        res_about = client.get('/about')
        self.assertEqual(res_about.status_code, 200)
        self.assertIn(b"Cloud Deployment", res_about.data)

        # Blockchain Explorer
        res_chain = client.get('/blockchain')
        self.assertEqual(res_chain.status_code, 200)

        # Election Results
        res_results = client.get('/results')
        self.assertEqual(res_results.status_code, 200)


if __name__ == '__main__':
    unittest.main()
