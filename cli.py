#!/usr/bin/env python
"""
Calico CLI - Root-level entry point.

This wrapper allows running the CLI from the project root directory:
    uv run cli.py play
    uv run cli.py mcts --record
    uv run cli.py benchmark

The actual CLI implementation is in source/cli.py.
"""
import sys
from pathlib import Path

# Add source directory to Python path for imports
source_dir = Path(__file__).parent / "source"
if str(source_dir) not in sys.path:
    sys.path.insert(0, str(source_dir))

# Import and run the CLI app
from cli_app import app

if __name__ == "__main__":
    app()
