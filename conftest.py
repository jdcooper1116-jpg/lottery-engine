"""
Root conftest.py — adds the lottery_engine directory to sys.path
so all modules can be imported without installing the package.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
