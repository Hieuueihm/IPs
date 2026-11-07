"""Replay C on Linux-local storage, then copy evidence to the private build.

Avoid DrvFS write latency on the large per-kernel C trace. C math and the
accepted input/output matching and independent signature checks stay intact.
"""
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
names=sys.argv[1:]
assert names
for name in names:
    source=ROOT/'experiments/paper_ablation31/variants'/name/'application.py'
    spec=importlib.util.spec_from_file_location('private_application_'+name,source)
    app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
    target=app.APP
    tmp=Path(tempfile.mkdtemp(prefix='ntru-ablation-'+name+'-'))
    for n in (512,1024):
        (tmp/f'N{n}').mkdir()
        shutil.copy2(target/f'N{n}/replacement.txt',tmp/f'N{n}/replacement.txt')
    app.APP=tmp
    print('APPLICATION_REPLAY_START',name,str(tmp),flush=True)
    app.linux()
    for n in (512,1024):
        previous=target/f'N{n}/trace.jsonl'
        if previous.exists() and not (target/f'N{n}/initial_trace.jsonl').exists():
            shutil.copy2(previous,target/f'N{n}/initial_trace.jsonl')
    shutil.copytree(tmp,target,dirs_exist_ok=True)
    print('APPLICATION_REPLAY_PASS',name,flush=True)
