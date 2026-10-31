"""Entry point for project-local YoWASP; invoke with bundled CPython."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'study/tools/yosys'))
from yowasp_yosys import run_yosys
raise SystemExit(run_yosys(sys.argv[1:]))
