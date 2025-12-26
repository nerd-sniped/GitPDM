import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freecad_gitpdm.git.client import GitClient

root = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP'), 'gitpdm-tests')
localM = os.path.join(root, 'local-master')

gc = GitClient()
print('Has remote:', gc.has_remote(localM, 'origin'))

upstream = gc.default_upstream_ref(localM, 'origin')
print(f'Upstream (master-only fallback): {upstream}')

ab = gc.ahead_behind(localM, upstream)
print(f'Ahead/Behind: {ab}')
