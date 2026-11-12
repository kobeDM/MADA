import os
import sys
import tempfile

HOME = tempfile.mkdtemp(prefix='mada_test_')
os.environ['MADAHOME'] = HOME
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
