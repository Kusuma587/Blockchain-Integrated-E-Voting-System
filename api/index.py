"""
Vercel Serverless Function Entry Point
for Blockchain-Integrated Multimodal Biometric Electronic Voting System.
"""

import os
import sys

API_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(API_DIR, '..'))

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault('VERCEL', '1')

from app import app

__all__ = ['app']
