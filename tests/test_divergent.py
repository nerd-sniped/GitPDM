import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freecad_gitpdm.git.client import GitClient

root = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP'), 'gitpdm-tests')
local = os.path.join(root, 'local')

gc = GitClient()
upstream = gc.default_upstream_ref(local, 'origin')
print(f'Upstream: {upstream}')

ab = gc.ahead_behind(local, upstream)
print(f'Ahead/Behind: {ab}')
