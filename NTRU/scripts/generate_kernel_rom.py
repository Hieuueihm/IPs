"""Export bit-exact R8 FFT constants and banked Montgomery root bundles."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hdl/core/rom'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fft = json.loads((ROOT/'study/vectors/r8/twiddle_q64_64.json').read_text())
    for component in range(2):
        (OUT/f'fft_{component}.mem').write_text(''.join(r['forward'][component]+'\n' for r in fft['roots']), encoding='ascii')
    capture = ROOT/'study/build/pqc_application/N512/capture/trace.jsonl'
    with capture.open() as f:
        nt = next(json.loads(line) for line in f if '"type":"ntt_rom"' in line)
    tables = [nt, {}]
    q=3329; R=65536%q
    tables[1]['forward']=[R*pow(17, int(f'{i:07b}'[::-1],2), q)%q for i in range(128)]
    tables[1]['inverse']=[R*pow(pow(17,int(f'{i:07b}'[::-1],2),q),-1,q)%q for i in range(128)]
    for profile, table in enumerate(tables):
        for inv, direction in enumerate(('forward','inverse')):
            values=table[direction]
            for bank in range(16):
                rows=[]
                for row in range(32):
                    g=row*16+bank
                    words=[values[k] if k<len(values) else 0 for k in (g,2*g,2*g+1)]
                    rows.append(sum(v<<(16*i) for i,v in enumerate(words)))
                (OUT/f'ntt_{profile}_{inv}_{bank}.mem').write_text(''.join(f'{v:012x}\n' for v in rows),encoding='ascii')
    files=sorted(OUT.glob('*.mem'))
    init=['// Generated literal file names for Vivado 2018.1 (no $sformatf support).','case(b)']
    for bank in range(16):
        init.append(f'{bank}:begin')
        for profile in range(2):
            for inv in range(2):
                init.append(f'    $readmemh({{`FLEX_ROM_DIR,"ntt_{profile}_{inv}_{bank}.mem"}},{"i" if inv else "f"}{profile});')
        init.append('end')
    init.append('endcase')
    (OUT/'ntt_init.vh').write_text('\n'.join(init)+'\n',encoding='ascii')
    (OUT/'manifest.json').write_text(json.dumps({'r8_commit':fft['commit'], 'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}},indent=2)+'\n')
    print(f'Exported {len(files)} ROM files')


if __name__=='__main__':main()
