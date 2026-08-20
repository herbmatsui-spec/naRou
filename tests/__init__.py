import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

stubs_dir = os.path.join(ROOT, "stubs")
if stubs_dir not in sys.path:
    sys.path.insert(0, stubs_dir)
