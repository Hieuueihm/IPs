"""Build pinned unchanged R8 C, capture kernel vectors, compare both leaf models.

Run: python -X utf8 scripts/validate_r8.py
Use --capture-only to regenerate vectors without replay, or --replay-only to
replay existing vectors. Build artifacts stay outside the reference checkout.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
import platform
from pathlib import Path
from random import Random
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'model'))
from r8_golden import Core, parse_word, wrap

COMMIT = 'ad1e5bf7714d53230ad457364db8a46a1b459c94'
URL = 'https://github.com/fixed-point-fndsa/fixed-point-c.git'
SOURCE = ROOT / 'third_party' / 'r8'
BUILD = ROOT / 'study' / 'build' / 'r8' / platform.system().lower()
VECTORS = ROOT / 'study' / 'vectors' / 'r8'
RESULTS = ROOT / 'study' / 'results'
KERNELS = ['FFT', 'iFFT', 'poly_mul_fft', 'poly_split_fft', 'poly_merge_fft']


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference():
    if not SOURCE.exists():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        run(['git', 'clone', '--no-checkout', URL, SOURCE])
        run(['git', '-C', SOURCE, 'checkout', '--detach', COMMIT])
    head = run(['git', '-C', SOURCE, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if head != COMMIT:
        raise RuntimeError(f'Expected reference {COMMIT}, found {head}; checkout left untouched.')
    # Windows checkout uses CRLF; compare canonical Git content in both hosts.
    dirty = run(['git', '-c', 'core.autocrlf=true', '-C', SOURCE, 'status', '--porcelain'],
                capture_output=True, text=True).stdout
    if dirty.strip():
        raise RuntimeError('Reference checkout is not pristine; refusing to overwrite changes.')
    files = run(['git', '-C', SOURCE, 'ls-files'], capture_output=True, text=True).stdout.splitlines()
    return {name: digest(SOURCE/name) for name in files if name.endswith(('.c', '.h'))}


def build():
    BUILD.mkdir(parents=True, exist_ok=True)
    cc = shutil.which('gcc')
    if not cc:
        raise RuntimeError('GCC with __int128 support is required.')
    macros = run([cc, '-dM', '-E', '-'], input='', capture_output=True, text=True).stdout
    if '#define __SIZEOF_LONG__ 8' not in macros:
        raise RuntimeError('Pinned R8 requires LP64 for its 64-bit __builtin_clzl use. '
                           'Run this script with Linux GCC/Python in WSL; do not patch the reference.')
    flags = ['-O2', '-std=gnu11', '-fno-strict-aliasing', '-ffunction-sections', '-fdata-sections',
             '-DFALCON_FPR_MODE=2', '-DFALCON_RAND_WIN32=0', '-I', str(SOURCE)]
    files = [SOURCE/name for name in ['codec.c','common.c','falcon.c','fft.c','fpr.c','rng.c','shake.c','sign.c','sign_ref.c','vrfy.c']]
    files += [SOURCE/'ntrugen'/'src'/name for name in
              ['ng_falcon.c','ng_fxp.c','ng_gauss.c','ng_mp31.c','ng_ntru.c','ng_poly.c','ng_zint31.c','sha3.c']]
    files += [ROOT/'sim'/'ref'/'r8_capture.c']
    commands = []
    objects = []
    for i, source in enumerate(files):
        obj = BUILD/f'{i:02d}_{source.stem}.o'
        command = [cc, *flags]
        if source == SOURCE/'fft.c':
            command += [f'-Dfalcon_inner_{k}=r8_original_{k}' for k in KERNELS]
        command += ['-c', str(source), '-o', str(obj)]
        commands.append(command)
        objects.append(obj)
    def compile_one(command):
        result = subprocess.run(command, capture_output=True, text=True, errors='replace')
        if result.returncode:
            raise RuntimeError(f'Compile failed: {command}\n{result.stderr}')
        return result.stderr
    with ThreadPoolExecutor(max_workers=4) as pool:
        logs = list(pool.map(compile_one, commands))
    exe = BUILD/('r8_capture.exe' if os.name == 'nt' else 'r8_capture')
    link = [cc, *map(str, objects), '-Wl,--gc-sections', '-lm', '-o', str(exe)]
    result = subprocess.run(link, capture_output=True, text=True, errors='replace')
    if result.returncode:
        raise RuntimeError(f'Link failed:\n{result.stderr}')
    (BUILD/'compiler.log').write_text('\n'.join(logs)+result.stderr, encoding='utf-8')
    return exe, {'compiler': run([cc, '--version'], capture_output=True, text=True).stdout.splitlines()[0],
                 'platform': platform.platform(), 'sizeof_long': 8,
                 'compile_commands': commands, 'link_command': link,
                 'harness_sha256': digest(ROOT/'sim'/'ref'/'r8_capture.c')}


def synthetic_requests():
    rng = Random(20261025)
    filename = BUILD/'requests.txt'
    mask = (1 << 128)-1
    count = 0
    with filename.open('w', encoding='ascii') as f:
        for logn in range(0, 11):
            n = 1 << logn
            for pattern in range(7):
                if pattern == 0:
                    a = [0]*n
                elif pattern == 1:
                    a = [1 << 64]+[0]*(n-1)
                elif pattern == 2:
                    a = [((-1)**i)*(1 << 64) for i in range(n)]
                elif pattern == 3:
                    values = [-(1 << 127), (1 << 127)-1, -1, 0, 1, (1 << 63)-1, 1 << 63, (1 << 63)+1]
                    a = [values[i % len(values)] for i in range(n)]
                elif pattern == 4:
                    a = [rng.randrange(-(1 << 70), 1 << 70) for _ in range(n)]
                elif pattern == 5:
                    a = [rng.getrandbits(128) for _ in range(n)]
                else:
                    a = [(-1)**i for i in range(n)]
                b = [rng.getrandbits(128) for _ in range(n)]
                for op in (['FFT','IFFT'] if logn == 0 else ['FFT','IFFT','CMUL','SPLIT','MERGE']):
                    f.write(f'{op} {logn} {count}\n')
                    f.write(' '.join(f'{x & mask:032x}' for x in a)+'\n')
                    if op == 'CMUL':
                        f.write(' '.join(f'{x & mask:032x}' for x in b)+'\n')
                    count += 1
    return filename, count


def export_rom(words):
    """Emit complete reference rows, including different 3M sums for each direction."""
    mask = (1 << 128)-1
    lines = {'forward': [], 'inverse': []}
    rows = []
    for index in range(1024):
        re, im = [parse_word(x) for x in words[2*index:2*index+2]]
        fields = {}
        for direction in lines:
            imag = im if direction == 'forward' else wrap(-im)
            values = [re, imag, wrap(re+imag)]
            fields[direction] = [f'{x & mask:032x}' for x in values]
            lines[direction].append(''.join(fields[direction]))
        rows.append({'index': index, **fields})
    files = []
    for direction, data in lines.items():
        p = VECTORS/f'twiddle_{direction}_q64_64.mem'
        p.write_text('\n'.join(data)+'\n', encoding='ascii')
        files.append({'file':p.name,'sha256':digest(p)})
    p = VECTORS/'twiddle_q64_64.json'
    p.write_text(json.dumps({'commit':COMMIT,'row_word_order':['real','imag','wrapped_real_plus_imag'],
                             'row_bits':384,'roots':rows},indent=2)+'\n',encoding='utf-8')
    files.append({'file':p.name,'sha256':digest(p)})
    return files


def capture():
    hashes = reference()
    exe, manifest = build()
    VECTORS.mkdir(parents=True, exist_ok=True)
    request, count = synthetic_requests()
    print(f'Built C oracle; capturing {count} synthetic kernel calls.', flush=True)
    inputs = [('synthetic', [], request), ('workload_512', ['--workload','9'], None),
              ('workload_1024', ['--workload','10'], None)]
    vector_files = []
    for name, args, stdin_path in inputs:
        raw = BUILD/f'{name}.jsonl'
        with raw.open('wb') as output, (stdin_path.open('rb') if stdin_path else open(os.devnull,'rb')) as inp:
            result = subprocess.run([str(exe), *args], stdin=inp, stdout=output,
                                    stderr=subprocess.PIPE, timeout=120, text=False)
        log = result.stderr.decode('utf-8', errors='replace')
        print(log.strip() or f'{name}: C oracle completed.', flush=True)
        (BUILD/f'{name}.log').write_text(log, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'{name} capture failed with exit {result.returncode}; see {BUILD}.')
        path = VECTORS/f'{name}.jsonl.gz'
        with raw.open('rb') as src, path.open('wb') as dst:
            with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as stream:
                shutil.copyfileobj(src,stream)
        vector_files.append({'file':path.name,'sha256':digest(path),'bytes':path.stat().st_size})
    assert reference() == hashes, 'Reference C source changed during capture.'
    with (BUILD/'synthetic.jsonl').open(encoding='utf-8') as f:
        rom = json.loads(f.readline())['words']
    rom_files = export_rom(rom)
    manifest.update({'source_url':URL,'commit':COMMIT,'source_pristine':True,'source_sha256':hashes,
                     'synthetic_cases':count,'files':vector_files,'seed':20261025,
                     'rom_files':rom_files,
                     'configuration':{'FALCON_FPR_MODE':2,'FALCON_AVX2':0,'FALCON_RAND_WIN32':0},
                     'scope':'Q64.64 C kernel capture; deterministic synthetic test keys; no RTL or hardware substitution.'})
    (VECTORS/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


def negative_controls(path):
    class FourM(Core):
        def cmul(self, ar, ai, br, bi):
            return (wrap(self.mul(ar,br)-self.mul(ai,bi)),
                    wrap(self.mul(ar,bi)+self.mul(ai,br)))
    class ForwardRootInInverse(Core):
        def root(self, index, inverse=False):
            return super().root(index, inverse=False)
    pending = {'4M_instead_of_3M':FourM, 'forward_root_in_IFFT':ForwardRootInInverse}
    caught = {}
    with gzip.open(path,'rt',encoding='utf-8') as f:
        rom = [parse_word(x) for x in json.loads(next(f))['words']]
        for line in f:
            rec = json.loads(line)
            if rec['type'] != 'kernel':
                continue
            for name, cls in list(pending.items()):
                if name == 'forward_root_in_IFFT' and rec['op'] != 'IFFT':
                    continue
                got, got1 = cls(rom,32).evaluate(rec)
                expected = [parse_word(x) for x in rec['out']]
                expected1 = [parse_word(x) for x in rec.get('out1',[])]
                if got != expected or (got1 is not None and got1 != expected1):
                    caught[name] = {'case':rec['case'],'op':rec['op'],'logn':rec['logn']}
                    del pending[name]
            if not pending:
                break
    assert not pending, f'Negative controls not detected: {list(pending)}'
    return caught


def replay():
    manifest = json.loads((VECTORS/'manifest.json').read_text(encoding='utf-8'))
    counts = Counter()
    words = Counter()
    leaf_mul = Counter()
    workloads = []
    kernel_total = 0
    common_rom = None
    for entry in manifest['rom_files']:
        assert digest(VECTORS/entry['file']) == entry['sha256']
    for entry in manifest['files']:
        path = VECTORS/entry['file']
        assert digest(path) == entry['sha256'], path
        cores = None
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                rec = json.loads(line)
                if rec['type'] == 'rom':
                    rom = [parse_word(x) for x in rec['words']]
                    if common_rom is None:
                        common_rom = rom
                    assert rom == common_rom
                    cores = [Core(rom,g) for g in (16,32)]
                elif rec['type'] == 'workload':
                    assert all(rec[k] == 0 for k in ('keygen','expand','sign','verify'))
                    workloads.append(rec)
                elif rec['type'] == 'kernel':
                    assert cores is not None
                    expected = [parse_word(x) for x in rec['out']]
                    expected1 = [parse_word(x) for x in rec.get('out1',[])]
                    for core in cores:
                        got, got1 = core.evaluate(rec)
                        if got != expected or (got1 is not None and got1 != expected1):
                            raise AssertionError(f'Mismatch leaf={core.leaf} file={path.name} id={rec["id"]} '
                                                 f'origin={rec["origin"]} op={rec["op"]} logn={rec["logn"]}')
                    key = f'{rec["origin"]}/{rec["op"]}/N{1 << rec["logn"]}'
                    counts[key] += 1
                    words[rec['op']] += len(expected)+len(expected1)
                    kernel_total += 1
        for core in cores:
            leaf_mul[core.leaf] += core.mul_calls
        print(f'PASS {path.name}: both F16 and R32 models.',flush=True)
    controls = negative_controls(VECTORS/'synthetic.jsonl.gz')
    result = {'commit':manifest['commit'],'kernel_calls':kernel_total,
              'golden_model_sha256':digest(ROOT/'model'/'r8_golden.py'),
              'negative_controls_detected':controls,
              'counts':dict(sorted(counts.items())),'output_words_per_model':sum(words.values()),
              'output_words_by_op':dict(words),'real_multiplications_per_leaf_model':dict(leaf_mul),
              'workloads':workloads,'mismatches':0,
              'limits':['No RTL/cycle/backpressure/PPA check.','No hardware kernel substituted in signing.',
                        'Q64.64 only; FFT32/64 not validated against R8.',
                        'R8 keygen uses NTRUGen, whose Q32.32 FFT is outside this capture.']}
    RESULTS.mkdir(parents=True,exist_ok=True)
    (RESULTS/'r8_differential.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# R8 C → FlexTransform golden model: differential check','',
           f'- Pinned commit: `{result["commit"]}`.',
           f'- C kernel calls: **{kernel_total}**; mismatches: **0**.',
           f'- Output Q64.64 words checked per model: **{sum(words.values())}** (both leaf 16 and 32).',
           '- C source remained pristine; compiler commands and SHA-256 recorded in the vector manifest.',
           '', '| Origin / kernel / N | Captured calls |','|---|---:|']
    lines += [f'| {key} | {val} |' for key,val in sorted(counts.items())]
    lines += ['', 'Workload status:']
    lines += [f'- N={1 << w["logn"]}: keygen/expand/sign_tree/verify all returned 0; signature {w["signature_bytes"]} bytes.' for w in workloads]
    lines += ['', 'Limits:']+[f'- {x}' for x in result['limits']]
    lines += ['', 'Negative controls (both detected):']+[f'- {name}: {where}' for name,where in controls.items()]
    (RESULTS/'r8_differential.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('kernel_calls','output_words_per_model','mismatches','workloads')},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--capture-only',action='store_true')
    group.add_argument('--replay-only',action='store_true')
    args=parser.parse_args()
    if not args.replay_only:
        capture()
    if not args.capture_only:
        replay()
