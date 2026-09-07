import sys
import os

# Add root directory to sys.path so api.py and other modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app
