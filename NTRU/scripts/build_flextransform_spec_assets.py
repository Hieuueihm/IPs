"""Rebuild FT-SPEC-1.0 data/trace tables; never writes RTL.

Requires the existing pinned-R8 capture and baseline cases for provenance.
Run the checker after building. Updating a released contract needs change control.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'spec/FlexTransform/1.0'
ASSETS = DEST / 'assets'
COMMIT = 'ad1e5bf7714d53230ad457364db8a46a1b459c94'
TESTS = ('T_CFG T_NATIVE T_STABILITY T_RESET T_FLUSH T_MEMORY T_FP_PRIM '
         'T_FP_KERNEL T_NTT_PRIM T_NTT_KERNEL T_ARRAY T_CONTEXT T_JOBS '
         'T_BANK T_ROOT T_STRESS T_PROFILE T_SIGNER T_MUTATE T_PERF T_RELEASE').split()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def oracle():
    s = importlib.util.spec_from_file_location('ft_spec_oracle', ASSETS / 'reference_model.py')
    module = importlib.util.module_from_spec(s)
    s.loader.exec_module(module)
    return module


def profiles(m):
    legal = []
    for op in range(9):
        for fmt in range(4):
            for profile in range(2):
                for logn in range(11):
                    for jobs in range(1, 9):
                        c = dict(op=op, fmt=fmt, profile=profile, logn=logn, jobs=jobs, reserved=0)
                        if m.validate(c) == 0:
                            legal.append(c)
    return dict(spec='FT-SPEC-1.0', configuration='REF16',
                parameters=dict(TILE_COUNT=16, LEAF_WIDTH=16, LEAVES_PER_TILE=4,
                                CONTEXT_COUNT=2, STORE_COUNT=3, BANKS_PER_STORE=64,
                                BANK_WIDTH=16, ROWS=128, HOST_LINE_BITS=128,
                                FFT_ROOT_READ_PORTS=1, NTT_BUNDLE_BANKS=16,
                                NTT_BUNDLE_BITS=48, NTT_BUNDLE_ROWS=32, EPOCH_BITS=4,
                                MAX_ACTIVE_CYCLES=1048576, MAX_FLUSH_CYCLES=256),
                opcodes=m.OPS, formats=[dict(code=i, bits=w, fraction=w//2 if i<3 else None)
                                      for i, w in enumerate(m.WIDTHS)],
                ntt_profiles=[dict(code=i, q=q, R=65536, qprime=(-pow(q, -1, 65536))%65536,
                                   r_mod_q=65536%q, r2_mod_q=pow(65536, 2, q),
                                   root_count=1024 if i==0 else 128,
                                   logn_min=3, logn_max=10 if i==0 else 8,
                                   intt_factorbar_by_logn={str(l):65536*pow(1 << (l-(q==3329 and l==8)),-1,q)%q
                                                          for l in range(3,11 if i==0 else 9)},
                                   incomplete_logn=None if i==0 else 8)
                              for i, q in enumerate((12289, 3329))],
                legal_commands=legal)


def interface():
    groups = {
        'control': [('clk_i',1,'input'),('rst_ni',1,'input'),('pause_i',1,'input'),
                    ('flush_i',1,'input'),('flush_done_o',1,'output')],
        'command': [('cmd_valid_i',1,'input'),('cmd_ready_o',1,'output'),
                    ('cmd_op_i',4,'input'),('cmd_fmt_i',2,'input'),('cmd_profile_i',2,'input'),
                    ('cmd_logn_i',4,'input'),('cmd_jobs_m1_i',3,'input'),
                    ('cmd_tag_i',32,'input'),('cmd_reserved_i',8,'input')],
        'completion': [('cpl_valid_o',1,'output'),('cpl_ready_i',1,'input'),
                       ('cpl_tag_o',32,'output'),('cpl_status_o',8,'output'),
                       ('cpl_job_mask_o',8,'output'),('cpl_cycles_o',64,'output'),
                       ('cpl_active_cycles_o',64,'output')],
        'memory_request': [('mem_req_valid_i',1,'input'),('mem_req_ready_o',1,'output'),
                           ('mem_req_write_i',1,'input'),('mem_req_store_i',2,'input'),
                           ('mem_req_addr_i',16,'input'),('mem_req_wdata_i',128,'input'),
                           ('mem_req_strb_i',16,'input')],
        'memory_response': [('mem_rsp_valid_o',1,'output'),('mem_rsp_ready_i',1,'input'),
                            ('mem_rsp_rdata_o',128,'output'),('mem_rsp_status_o',3,'output')]
    }
    return dict(spec='FT-SPEC-1.0', clock='clk_i', reset=dict(signal='rst_ni',
                synchronous=True, active_low=True, minimum_edges=2),
                transfer='rising_edge && valid && ready',
                ports=[dict(name=n, width=w, direction=d, group=g)
                       for g, ports in groups.items() for n,w,d in ports],
                command_status=dict(OK=0,BAD_RESERVED=1,BAD_OP=2,BAD_FMT=3,
                                    BAD_PROFILE=4,BAD_LOGN=5,BAD_JOBS=6,
                                    ABORTED=16,INTERNAL_FAULT=17),
                command_error_priority=['BAD_RESERVED','BAD_OP','BAD_FMT',
                                        'BAD_PROFILE','BAD_LOGN','BAD_JOBS'],
                memory_status=dict(OK=0,BAD_STORE=1,BAD_ALIGN=2,RANGE=3,STATE=4),
                memory_error_priority=['BAD_STORE','BAD_ALIGN','RANGE','STATE'],
                stores=dict(A=0,B=1,C=2), address_unit='byte', line_bytes=16,
                address_min=0,address_max_line=0x3ff0, byte_order='little',
                max_command_outstanding=1,max_memory_outstanding=1,
                internal_array=dict(data_bits=2048,roots_bits=1024,result_bits=2048,
                                    is_ntt_bits=1,fmt_bits=2,tile_mode_bits=2,
                                    profile_bits=2,direction_bits=1,epoch_bits=4,
                                    context_bits=1,stage_bits=4,lane_mask_bits=16,
                                    product_sel_bits=2,tag_bits=32,
                                    job_map='context lookup: job index3 and destinations per active logical lane',
                                    encoding='reference private interface; alternatives require manifest mapping'))


def requirements():
    # Order within each group is the numeric ID used by the normative documents.
    groups = {
      'SCP': ('00_scope_profiles.md', [
        ('Implement opcodes 0..8 and reject reserved opcodes.', 'T_CFG T_FP_KERNEL T_NTT_KERNEL'),
        ('Enforce FFT formats 0..2 and RES16 format3 for NTT family.', 'T_CFG'),
        ('W128 is bit-exact to pinned scalar LP64 R8 numeric contract.', 'T_FP_KERNEL T_SIGNER'),
        ('Do not lower precision automatically; W32/64 have only their explicit integer contract.', 'T_CFG T_FP_PRIM'),
        ('Enforce the N/profile support table including incomplete q3329 N256.', 'T_CFG T_NTT_KERNEL'),
        ('Enforce jobs limits; FFT jobs1 and NTT N8/16/32 limits8/4/2.', 'T_CFG T_JOBS'),
        ('All jobs in a batch share op,fmt,profile,N and direction.', 'T_CFG T_JOBS'),
        ('Keep every batched polynomial and job identity independent.', 'T_JOBS T_CONTEXT'),
        ('Host owns load/read only in the states defined by protocol; no host requests in RUN.', 'T_NATIVE T_MEMORY'),
        ('Issue/address/root/control schedules are independent of coefficient values for identical control state, address footprint and flow trace.', 'T_PROFILE'),
        ('Do not depend on unwritten RAM; reset does not implicitly initialize or zeroize data.', 'T_RESET T_MEMORY')]),
      'NUM': ('01_numeric_kernels.md', [
        ('Use W32/64/128 with fractional bits W/2.', 'T_FP_PRIM'),
        ('Add/sub wrap modulo2^W without saturation.', 'T_FP_PRIM'),
        ('Multiply with full mathematical product, bias2^(F-1), shiftF, then wrapW.', 'T_FP_PRIM T_MUTATE'),
        ('div2e wraps bias addition before arithmetic shift; shift0 is identity.', 'T_FP_PRIM'),
        ('Use exact 3M with wrapped pre-add and independent per-real-product rounding.', 'T_FP_PRIM T_FP_KERNEL'),
        ('Lower limbs are unsigned; only each operand top limb is signed; preserve raw product sign.', 'T_FP_PRIM T_ARRAY'),
        ('Preserve retained W+F product bits, required carries and one final rounding; discard only exact zero-weight terms.', 'T_FP_PRIM T_ARRAY'),
        ('Use pinned exact FFT ROM bits, no sin/cos regeneration.', 'T_ROOT'),
        ('Conjugate in128 before low-width quantization; form root sum after quantization.', 'T_ROOT T_FP_KERNEL'),
        ('Require canonical NTT coefficients/roots/results; no lazy/signed residue contract.', 'T_NTT_PRIM T_NTT_KERNEL'),
        ('Montgomery implements full unsigned T, m, carry and canonical conditional subtraction.', 'T_NTT_PRIM'),
        ('Do not apply FFT product truncation to Montgomery T.', 'T_NTT_PRIM T_ARRAY'),
        ('Implement CT and GS component/domain equations exactly.', 'T_NTT_KERNEL T_ARRAY'),
        ('Root tables encode ordinary root times R; inverse ordinary roots before encoding.', 'T_ROOT T_NTT_KERNEL')]),
      'KER': ('01_numeric_kernels.md', [
        ('FFT uses exact split-real/imag indexing, roots and wrapped arithmetic of section01.4.', 'T_FP_KERNEL'),
        ('IFFT uses inverse roots and final div2e(logn-1), including N1/N2 identity.', 'T_FP_KERNEL'),
        ('CMUL is pointwise complex3M, writes A and preserves B/C.', 'T_FP_KERNEL'),
        ('SPLIT preserves input stores and writes concatenated f0/f1 to C including N2 case.', 'T_FP_KERNEL'),
        ('MERGE reads half-length A/B and writes interleaved component C including N2 case.', 'T_FP_KERNEL'),
        ('NTT uses prescribed CT loop/root/output order and q3329 incomplete stop.', 'T_NTT_KERNEL'),
        ('INTT uses prescribed inverse GS loop and final inverse2^L normalization.', 'T_NTT_KERNEL'),
        ('TOMONT returns xR modq.', 'T_NTT_KERNEL'),
        ('MODMUL returns abR^-1 modq; no implicit ordinary multiply or BASEMUL.', 'T_NTT_KERNEL'),
        ('Paired/tail/scalar NTT tile modes preserve coefficient order, roots and job schedule.', 'T_ARRAY T_NTT_KERNEL')]),
      'IF': ('02_interfaces_protocol.md', [
        ('Transfer only on sampled rising edge valid&&ready.', 'T_NATIVE T_STABILITY'),
        ('Hold valid and complete payload until handshake except reset/canceled internal epoch.', 'T_STABILITY T_FLUSH'),
        ('Avoid combinational valid/ready loops.', 'T_STABILITY T_RELEASE'),
        ('Latch every CMD field on acceptance; later input changes have no effect.', 'T_NATIVE'),
        ('Allow one outstanding CMD; host memory wins simultaneous IDLE arbitration.', 'T_NATIVE'),
        ('Return exactly one tagged completion per accepted command except reset.', 'T_NATIVE T_RESET T_FLUSH'),
        ('Publish OK only after all writes commit and command pipeline/context drain.', 'T_NATIVE T_CONTEXT'),
        ('Published completion is immutable through pause/flush until ACK; reset may cancel.', 'T_STABILITY T_FLUSH'),
        ('Internal packets retain sufficient epoch/context/lane/phase identity to retire correctly.', 'T_CONTEXT T_ARRAY'),
        ('Use defined packet packing; zero reserved/inactive bits and preserve active lane masks.', 'T_ARRAY T_CONTEXT')]),
      'RST': ('02_interfaces_protocol.md', [
        ('Synchronous active-low reset clears all control valids/state and suppresses writes/replies; hold >=2edges.', 'T_RESET'),
        ('Reset preserves data/ROM content; do not rely on initial for control reset.', 'T_RESET T_MEMORY')]),
      'ERR': ('02_interfaces_protocol.md', [
        ('Validate command fields in specified error priority, without evaluating dependent invalid fields.', 'T_CFG'),
        ('Invalid CMD returns error/tag/mask0 without arithmetic/data/root issue or RAM change.', 'T_CFG'),
        ('Detected internal invariant failure stops command side effects, drains and returns INTERNAL_FAULT unless reset/flush takes priority.', 'T_CONTEXT T_FLUSH')]),
      'MEM': ('03_microarchitecture_memory.md', [
        ('Validate host store/alignment/range/state using specified priority.', 'T_MEMORY'),
        ('Implement byte-enable writes and little-endian raw128 lines; zero-strobe write is ACKed no-op.', 'T_MEMORY'),
        ('One outstanding host request, exactly one stable ordered response.', 'T_MEMORY T_STABILITY'),
        ('ACK host write OK only after enabled bytes have committed.', 'T_MEMORY'),
        ('Enforce IDLE/RUN/DONE/FLUSH memory ownership and DONE write STATE behavior.', 'T_MEMORY T_NATIVE'),
        ('Block new command until completion ACK and any earlier memory response drains.', 'T_NATIVE'),
        ('Apply fixed bijective bank/row mapping and <=1R+1W per bank per edge.', 'T_BANK'),
        ('Bank read adapter latency is >=1 edge and held response cannot be overwritten.', 'T_BANK T_STABILITY'),
        ('Serialize overlapping read/write; never depend on macro read-during-write behavior.', 'T_BANK'),
        ('Map FFT components to consecutive little-endian limbs16 and preserve split-real/imag layout.', 'T_MEMORY T_FP_KERNEL'),
        ('Map NTT job j coefficient i at word j*N+i, same map in B for MODMUL.', 'T_JOBS T_MEMORY'),
        ('Only bytes in output footprint may change; preserve all other bytes/stores.', 'T_JOBS T_MEMORY T_FP_KERNEL')]),
      'CTL': ('02_interfaces_protocol.md', [
        ('Pause holds datapath/issue/context/command writes while published external responses may ACK.', 'T_STABILITY T_CONTEXT T_PERF'),
        ('Reset/flush override pause and can drain/cancel without pause deadlock.', 'T_RESET T_FLUSH')]),
      'FLS': ('02_interfaces_protocol.md', [
        ('Implement four-phase level flush handshake and block new requests through release.', 'T_FLUSH'),
        ('Suppress command writes from first sampled flush edge, drain/invalidate all canceled packets.', 'T_FLUSH T_CONTEXT'),
        ('Unpublished command gets exactly one ABORTED mask0; no rollback, all batch outputs invalid.', 'T_FLUSH'),
        ('Preserve published completion unchanged and do not wait for cpl_ready to ACK flush.', 'T_FLUSH'),
        ('IDLE flush produces no completion; reset cancels flush/control without reply.', 'T_FLUSH T_RESET'),
        ('Flush completes <=256 clocks after accepted host responses drain regardless of pause/completion backpressure.', 'T_FLUSH')]),
      'ARC': ('03_microarchitecture_memory.md', [
        ('Shared array sustains legal input frame II1 with ready consumer and no pause/flush.', 'T_ARRAY T_PERF'),
        ('Publish per-mode latency; hold output and identity through backpressure.', 'T_ARRAY T_STABILITY'),
        ('Align bypass/tail data, roots, valid and metadata.', 'T_ARRAY'),
        ('Service bank conflicts in legal rounds and gather every word into its correct operand slot.', 'T_BANK T_FP_KERNEL'),
        ('Budget FFT root1/cycle, prefetch complete lane roots, clear cache valid at each CMD/flush.', 'T_ROOT T_PROFILE'),
        ('Pack small independent NTT jobs with per-job index/root schedule and active masks.', 'T_JOBS T_ARRAY'),
        ('Use specified NTT bundle order/bank mapping, broadcast or serialize conflicts, no padded-row request.', 'T_ROOT T_BANK'),
        ('Preserve limb fusion grouping/sign/shift and retained-width exact product.', 'T_ARRAY T_FP_PRIM'),
        ('Keep FFT half-operands/cross products and NTT A/sum/root/tail side paths until consumed.', 'T_ARRAY T_CONTEXT'),
        ('Provide implementation manifest covering all items in03.9 and interface mapping.', 'T_RELEASE')]),
      'CTX': ('03_microarchitecture_memory.md', [
        ('Use two independently owned microbatch contexts; no reuse until all effects commit.', 'T_CONTEXT'),
        ('Collect p0/p1/p2 by logical lane; never combine incomplete or mismatched triplets.', 'T_CONTEXT'),
        ('Maintain command tag, job, stage, lane, destination and epoch ownership through retire.', 'T_CONTEXT'),
        ('Detect duplicate/unknown current-epoch phase errors; discard canceled-epoch packets without new-command writes.', 'T_CONTEXT'),
        ('READY requires all coefficients/roots and output capacity for active lanes.', 'T_CONTEXT T_ROOT'),
        ('Inactive lanes are explicitly masked/zero and have no side effect.', 'T_CONTEXT T_ARRAY'),
        ('Memory-pass barrier waits for committed writes; paired NTT layers fuse inside one pass; resolve in-place RAW/WAW hazards.', 'T_CONTEXT T_BANK'),
        ('Epoch increments on CMD/cancel; modulo wrap never replaces drain; reset clears every pipeline valid.', 'T_CONTEXT T_RESET T_FLUSH')]),
      'DV': ('04_verification_acceptance.md', [
        ('Map every mandatory requirement to recorded test results or explicitly reviewed waiver; NOT_RUN is not PASS.', 'T_RELEASE'),
        ('Check coefficient-independent schedule with identical config/initial state/flow trace.', 'T_PROFILE'),
        ('Publish completion <=1048576 active clocks for a valid unflushed/unreset command.', 'T_STRESS T_PERF'),
        ('Release source/tool/seed/hash/coverage/assertion/provenance/performance/deviation manifest.', 'T_RELEASE')])
    }
    records=[]
    for group,(section,items) in groups.items():
        for i,(text,tests) in enumerate(items,1):
            source=section
            if group=='MEM' and i<=6:
                source='02_interfaces_protocol.md'
            if group=='IF' and i>=9:
                source='03_microarchitecture_memory.md'
            records.append(dict(id=f'FT-{group}-{i:03}',shall=text,section=source,test_ids=tests.split()))
    return dict(spec='FT-SPEC-1.0',test_ids=TESTS,requirements=records)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    m=oracle()
    src_fft=ROOT/'study/vectors/r8/twiddle_q64_64.json'
    src_trace=ROOT/'study/build/pqc_application/N512/capture/trace.jsonl'
    src_cases=ROOT/'study/build/kernel_engine/cases.json'
    fft=json.loads(src_fft.read_text(encoding='utf-8'))
    assert fft['commit']==COMMIT and len(fft['roots'])==1024
    (ASSETS/'fft_q64_64.mem').write_text(''.join(''.join(r['forward'][:2])+'\n' for r in fft['roots']),encoding='ascii')
    ntt=None
    with src_trace.open(encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            if r['type']=='ntt_rom':
                ntt=r
                break
    assert ntt is not None
    for q in (12289,3329):
        for inv in (False,True):
            suffix='inverse' if inv else 'forward'
            if q==12289:
                words=ntt[suffix]
                assert len(words)==1024
            else:
                ordinary=[pow(17,int(f'{k:07b}'[::-1],2),q) for k in range(128)]
                words=[65536*(pow(x,-1,q) if inv else x)%q for x in ordinary]
            (ASSETS/f'ntt_q{q}_{suffix}.mem').write_text(''.join(f'{x:04x}\n' for x in words),encoding='ascii')
    roots=m.read_roots(ASSETS)
    p=profiles(m)
    dump(DEST/'profiles.json',p)
    dump(DEST/'interface.json',interface())
    req=requirements()
    dump(DEST/'requirements.json',req)
    (DEST/'05_requirements.md').write_text(
        '# 05 — Requirements and verification traceability\n\n'
        'Generated from [requirements.json](requirements.json). SHALL/MUST are mandatory.\n'
        'Test definitions: [04](04_verification_acceptance.md). No RTL test is marked PASS by this table.\n\n'
        '| Requirement | Mandatory behavior | Source | Tests |\n|---|---|---|---|\n'+''.join(
          f"| {r['id']} | {r['shall']} | [{r['section'][:2]}]({r['section']}) | {', '.join(r['test_ids'])} |\n"
          for r in req['requirements']),encoding='utf-8')
    cases=json.loads(src_cases.read_text(encoding='utf-8'))
    candidates={}
    for r in cases:
        fmt=r['width'] if m.OPS[r['op']]<5 else 3
        candidates[m.OPS[r['op']],fmt,r['profile'],r['logn']]=r
    fixtures=[]
    for i,c in enumerate(p['legal_commands']):
        op=next(k for k,v in m.OPS.items() if v==c['op'])
        width=m.WIDTHS[c['fmt']]
        mask=(1<<width)-1
        r=candidates.get((c['op'],c['fmt'],c['profile'],c['logn']))
        if c['jobs']==1 and r is not None:
            cvt=lambda x: (int(x,16) if isinstance(x,str) else x)&mask
            a=[[cvt(x) for x in r['a']]]
            b=[[cvt(x) for x in r.get('b',[])]]
            expected=[[cvt(x) for x in r['out']+r.get('out1',[])]]
            origin=dict(kind='baseline_expected',origin=r.get('origin'),case_id=r.get('id'),
                        original_format=r['width'],native_format=c['fmt'])
        else:
            n=1<<c['logn']
            q=(12289,3329)[c['profile']]
            a=[[(29*j+17*k*k+3*k+1)%q if c['fmt']==3 else (k+1)&mask for k in range(n)] for j in range(c['jobs'])]
            b=[[(q-1-11*k-7*j)%q for k in range(n)] for j in range(c['jobs'])] if op=='MODMUL' else [[] for _ in a]
            expected=m.evaluate(c,a,b,roots)
            origin=dict(kind='spec_integer_oracle',reason='multi-job or missing baseline identity')
        # Never silently regenerate an inconsistent existing expected record.
        assert m.evaluate(c,a,b,roots)==expected,(i,c,origin)
        encode=lambda jobs:[[f'{x:0{width//4}x}' for x in job] for job in jobs]
        fixtures.append(dict(id=f'K{i:04}',command=c,a=encode(a),b=encode(b),
                             expected=encode(expected),word_bits=width,
                             output_store=2 if op in ('SPLIT','MERGE') else 0,provenance=origin))
    (ASSETS/'kernel_fixtures.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in fixtures),encoding='utf-8')
    prim=[]
    for w in (32,64,128):
        vals=[0,1,-1,1<<(w//2-1),-(1<<(w//2-1)),(1<<(w-1))-1,-(1<<(w-1)),(1<<(w//2))+1]
        for a in vals:
            for b in vals:
                prim.append(dict(kind='fixed_mul',width=w,a=f'{a% (1<<w):0{w//4}x}',b=f'{b% (1<<w):0{w//4}x}',
                                 expected=f'{m.mul(a,b,w)%(1<<w):0{w//4}x}'))
        for a in vals:
            for s in (0,1,2,9):
                prim.append(dict(kind='div2e',width=w,a=f'{a%(1<<w):0{w//4}x}',shift=s,
                                 expected=f'{m.div2e(a,s,w)%(1<<w):0{w//4}x}'))
    for q in (12289,3329):
        for a in (0,1,2,q//2,q-2,q-1):
            for b in (0,1,2,q//2,q-2,q-1):
                prim.append(dict(kind='mont',q=q,a=a,b=b,expected=m.mont(a,b,q)))
    dump(ASSETS/'primitive_fixtures.json',prim)
    bad=[]
    # One test for every single field plus multiple simultaneous errors.
    base=dict(op=0,fmt=2,profile=0,logn=10,jobs=1,reserved=0)
    changes=[{},dict(reserved=1),dict(op=15),dict(fmt=3),dict(profile=1),
             dict(logn=11),dict(jobs=2),dict(reserved=1,op=15,fmt=3,profile=3,logn=15,jobs=8),
             dict(op=15,fmt=3,profile=3,logn=15,jobs=8),dict(fmt=3,profile=3,logn=15,jobs=8),
             dict(profile=3,logn=15,jobs=8),dict(logn=15,jobs=8),
             dict(op=5,fmt=3,profile=1,logn=9),dict(op=5,fmt=3,profile=1,logn=3,jobs=8)]
    for change in changes:
        c={**base,**change};bad.append(dict(command=c,expected_status=m.validate(c)))
    dump(ASSETS/'command_fixtures.json',bad)
    dump(ASSETS/'provenance.json',dict(spec='FT-SPEC-1.0',r8_commit=COMMIT,
        c_contract=dict(abi='LP64',FPR_MODE=2,AVX2=0),
        source_files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in (src_fft,src_trace,src_cases)],
        generated_by='scripts/build_flextransform_spec_assets.py',
        note='Only baseline_expected fixtures inherit captured expected bits; multi-job/custom widths have integer-contract evidence, not signer-precision approval.'))
    # Hash every release file, not caches or the manifest itself.
    files={p.relative_to(DEST).as_posix():sha(p) for p in sorted(DEST.rglob('*'))
           if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
    dump(DEST/'manifest.json',dict(spec='FT-SPEC-1.0',status='candidate',files=files,
         tools={name:sha(ROOT/name) for name in ('scripts/build_flextransform_spec_assets.py',
                                                'scripts/check_flextransform_spec.py') if (ROOT/name).exists()}))
    print(json.dumps(dict(requirements=len(req['requirements']),tests=len(TESTS),kernel_fixtures=len(fixtures),primitive_fixtures=len(prim),release_files=len(files))))


if __name__=='__main__':
    main()
