#!/usr/bin/env python3
"""
OpenPlex — A Perplexity Pro alternative for Termux
Uses NVIDIA NIM API free tier models with web search and source verification.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from main import main

if __name__ == "__main__":
    main()
