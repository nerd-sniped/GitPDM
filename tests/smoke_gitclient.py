import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import freecad_gitpdm.git.client as client_mod
from freecad_gitpdm.git.client import GitClient

root = os.path.join(os.environ.get('TEMP') or os.environ.get('TMP'), 'gitpdm-tests')
local = os.path.join(root, 'local')
peer = os.path.join(root, 'peer')

print('Root:', root)
print('Local:', local)

gc = GitClient()
print('client module:', client_mod.__file__)
print('GitClient dir (truncated):', [a for a in dir(GitClient) if not a.startswith('__')][:10])
print('git available:', gc.is_git_available())
print('repo root:', gc.get_repo_root(local))
print('branch:', gc.current_branch(local))
print('status:', gc.status_summary(local))
try:
    print('has remote origin:', gc.has_remote(local, 'origin'))
except Exception as e:
    print('has_remote not available or failed:', e)

upstream_before = gc.default_upstream_ref(local, 'origin')
print('upstream before fetch:', upstream_before)

fetch_res = gc.fetch(local, 'origin')
print('fetch ok:', fetch_res['ok'])
print('fetched_at:', fetch_res['fetched_at'])

upstream_after = gc.default_upstream_ref(local, 'origin')
print('upstream after fetch:', upstream_after)

if upstream_after:
    ab = gc.ahead_behind(local, upstream_after)
    print('ahead/behind:', ab)
else:
    print('No upstream to compare')
