"""Fixtures for a_cg_z020_share: the a_cg_batch cases, scheduled by this directory's planner (tile latency + 1).

Loads experiments/a_cg_batch/build.py with this directory first on the import path, so its `import planner` and
`extra_cases` take the copies here, and writes to study/build/a_cg_z020_share/ (fixtures.bin, four_state.bin, .json).
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('lat1_build', ROOT / 'experiments/a_cg_batch/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
build.BUILD = ROOT / 'study/build/a_cg_z020_share'
import planner
assert Path(planner.__file__).resolve().parent == HERE and planner.TILE_EXTRA == 1

if __name__ == '__main__':
    build.fixtures()
