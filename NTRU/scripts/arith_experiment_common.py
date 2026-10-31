"""Small common runner for controlled arithmetic RTL synthesis experiments."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parent.parent
WEIGHTS={'$_BUF_':.67,'$_NOT_':.67,'$_NAND_':1.,'$_NOR_':1.,'$_AND_':1.33,'$_OR_':1.33,
         '$_ANDNOT_':1.33,'$_ORNOT_':1.33,'$_XOR_':2.33,'$_XNOR_':2.33,'$_MUX_':2.33}

def run(cmd,**kwargs):
    return subprocess.run([str(c) for c in cmd],check=True,**kwargs)

def hashes(paths):
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}

def check_hashes(expected):
    assert hashes(expected)==expected,'source changed since validation'

def synthesize(build,sources,tops,yosys):
    yosys=yosys or shutil.which('yosys')
    if not yosys:raise RuntimeError('Provide native Yosys with --yosys')
    version=run([yosys,'-V'],capture_output=True,text=True).stdout.strip()
    def one(top):
        stat=build/f'{top}_stat.json';depth=build/f'{top}_ltp.txt'
        ys=build/f'{top}.ys'
        ys.write_text('\n'.join([
            'read_verilog -sv -I'+(ROOT/'hdl/proto').as_posix()+' '+' '.join((ROOT/s).as_posix() for s in sources),
            f'hierarchy -check -top {top}',f'synth -flatten -noabc -top {top}',
            'abc -fast -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX','opt_clean -purge',
            f'tee -q -o {stat.as_posix()} stat -json',f'tee -q -o {depth.as_posix()} ltp -noff']))
        start=time.monotonic();print('Synthesizing '+top+' ...',flush=True)
        r=run([yosys,'-Q','-s',ys.as_posix()],capture_output=True,text=True)
        (build/f'{top}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        cells=next(iter(json.loads(stat.read_text())['modules'].values()))['num_cells_by_type']
        ff=sum(n for c,n in cells.items() if 'DFF' in c)
        unknown={c:n for c,n in cells.items() if c not in WEIGHTS and 'DFF' not in c}
        assert not unknown,unknown
        comb=sum(WEIGHTS.get(c,0)*n for c,n in cells.items())
        row={'top':top,'comb_ge':round(comb,1),'ff':ff,'total_ge':round(comb+4.67*ff,1),
             'depth_cells':int(re.search(r'length=(\d+)',depth.read_text()).group(1)),
             'tool':version,'unknown':unknown,'seconds':round(time.monotonic()-start,1)}
        print(json.dumps(row),flush=True);return row
    with ThreadPoolExecutor(max_workers=3) as pool:return list(pool.map(one,tops))
