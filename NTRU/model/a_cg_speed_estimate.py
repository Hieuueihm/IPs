"""Cycle estimates for the measured A/CG prototype; no RTL changes.

Models shared FFT program phase, noninterleaved stage input streams, physical
1R1W bank hazards and numerical RAM replay. Estimates are not RTL timings.
"""
import hashlib
import gzip
import importlib.util
import json
import struct
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('speed_cg',ROOT/'model/cg_bank4_model.py')
cg=importlib.util.module_from_spec(s);s.loader.exec_module(cg)


def plan(m,planes,inv,fl,overlap):
    n=m.bit_length()-1; period=cg.FFT[fl][0] if fl else 3
    book=cg.Book();layers=[];starts=[];labels=list(range(m));previous_last_read=-1
    previous_last_write=-1
    for stage in range(n):
        events=cg.template(m,planes,inv,fl,stage,0,True)
        # Prototype has one common NTT phase, unlike the older t//6 model.
        for e in events:
            delta=0 if fl else 2-(e['A']-period*(e['k']*planes+e['part']))
            e['A']+=delta
            for kind in ('reads','writes'):
                e[kind]=[(a,c+delta-(1 if fl and kind=='writes' else 0),p,pl,port)
                         for a,c,p,pl,port in e[kind]]
        first_read=min(c for e in events for a,c,*_ in e['reads'])
        lower=(previous_last_read if overlap else previous_last_write)+1-first_read
        # Shared microprogram: every FFT start has the same phase modulo II.
        st=book.earliest(events,max(0,lower),period if overlap or not fl else 1,0)
        book.take(events,st)
        starts.append(st)
        previous_last_read=max(c for e in events for a,c,*_ in e['reads'])
        first_write=min(c for e in events for a,c,*_ in e['writes'])
        assert first_write>previous_last_write,'Proposed single write-stage context would be insufficient'
        previous_last_write=max(c for e in events for a,c,*_ in e['writes'])
        h=1<<stage if inv else m>>(stage+1)
        out=[None]*m
        for e in events:
            x,y=(labels[p] for p in e['rp'])
            assert y==x+h and (x//h)%2==0
            e['root']=(m//h if fl else m//(2*h))+x//(2*h)
            for p,label in zip(e['wp'],(x,y)):out[p]=label
        assert None not in out
        labels=out;layers.append(events)
    assert labels==list(range(m))
    body=previous_last_write+1 if n else 0
    return dict(m=m,planes=planes,inverse=inv,fft_l=fl,interleaved=True,layers=layers,
                starts=starts,rows_per_buffer=max(1,m//32)*planes,
                cycles=body+(3 if fl else 4) if n else 0)


def fixtures():
    raw=(ROOT/'study/build/a_cg_prototype/fixtures.bin').read_bytes()
    w=struct.unpack('<'+'I'*(len(raw)//4),raw);pos=2
    assert w[0]==0x43474131
    for _ in range(w[1]):
        fft,fmt,ln,hm,inv,q,qi,ns,nr,nw=w[pos:pos+10];pos+=10
        desc=w[pos:pos+3*ns];pos+=3*ns
        roots=[w[pos+t*nr:pos+(t+1)*nr] for t in range(16)];pos+=16*nr
        aa,zz=w[pos:pos+nw],w[pos+nw:pos+2*nw];pos+=2*nw
        fl=1<<fmt if fft else 0
        def values(a):
            if not fft:return list(a)
            return [cg.fp.wrap(sum(a[i+j]<<(32*j) for j in range(fl)),32*fl) for i in range(0,len(a),fl)]
        yield dict(fft=fft,fmt=fmt,logn=ln,hmin=hm,inverse=inv,q=q,desc=desc,
                   roots=roots,a=values(aa),z=values(zz),words=nw,root_rows=nr)
    assert pos==len(w)


def c_reference_checks(cache,checks):
    for filename in ('synthetic.jsonl.gz','workload_512.jsonl.gz','workload_1024.jsonl.gz'):
        gm=igm=None
        with gzip.open(ROOT/'study/vectors/r8'/filename,'rt') as f:
            for line in f:
                d=json.loads(line)
                if d['type']=='rom':
                    w=[cg.fp.wrap(int(x,16),128) for x in d['words']]
                    gm=list(zip(w[::2],w[1::2]));igm=[(a,cg.fp.wrap(-b,128)) for a,b in gm]
                    assert gm==cg.fp.roots(128),'R8 C root bits differ from current FFT128 table'
                if d['type']!='kernel' or d['op'] not in ('FFT','IFFT'):continue
                ln=d['logn'];a=[cg.fp.wrap(int(x,16),128) for x in d['a']]
                z=[cg.fp.wrap(int(x,16),128) for x in d['out']]
                key=(1<<max(0,ln-1),8,d['op']=='IFFT',4)
                pn=cache.setdefault(key,(None,plan(*key,True)))[1]
                got=a if ln==0 else cg.replay(pn,a,gm=gm,igm=igm)
                assert got==z,(filename,d['id'],d['op'],ln)
                checks['R8_C_'+('synthetic' if filename.startswith('synthetic') else 'workload')]+=1
    # Sample five real C NTRUGen primes over every supported N, both directions.
    for pi,q,ln,gm,igm,a,z,b,iz in cg.pc.ntrugen():
        if pi not in (0,1,161,321,322):continue
        for inv,inp,expected in ((False,a,z),(True,b,iz)):
            key=(1<<ln,1,inv,0)
            pn=cache.setdefault(key,(None,plan(*key,True)))[1]
            assert cg.replay(pn,inp,q,gm,igm)==expected,(pi,ln,inv)
            checks['NTRUGen_C_NTT']+=1
    # Intentional compatibility audit, not a pass criterion for native keygen:
    # current generic rounded FFT64 is a different contract from NTRUGen fmt5.
    for line in (ROOT/'spec/FlexTransform/2.0/assets/kernel/fft_ntrugen.jsonl').read_text().splitlines():
        d=json.loads(line);ln=d['logn'];inv=d['op']=='IFFT'
        a=[cg.fp.wrap(int(x,16),64) for x in d['input'][0]]
        z=[cg.fp.wrap(int(x,16),64) for x in d['expected'][0]]
        pn=cache[(1<<max(0,ln-1),4,inv,2)][1]
        got=cg.replay(pn,a,gm=cg.fp.roots(64),igm=cg.fp.roots_inv(64))
        checks['NTRUGen_FFT64_native_'+('matches' if got==z else 'different_contract')]+=1


def write_report(result):
    rows=[]
    for fft,fmt,q,ln,hm,label in [(0,0,12289,10,0,'NTT q12289 N1024'),
            (0,0,3329,8,1,'NTT q3329 N256 hmin1'),(0,0,8380417,8,0,'NTT q8380417 N256'),
            (1,0,0,10,0,'FFT32 N1024'),(1,1,0,10,0,'FFT64 N1024 (generic)'),(1,2,0,10,0,'FFT128 N1024 (R8)')]:
        c=next(c for c in result['cases'] if (c['fft'],c['fmt'],c['q'],c['logn'],c['hmin'],c['inverse'])==(fft,fmt,q,ln,hm,0))
        rows.append((label,c))
    ck=result['checks']
    text=['# Ước tính tăng tốc A + CG, giữ contract số học PQC','',
        'Ngày 02/11/2026. Đây là **model chu kỳ và replay số học**, chưa phải RTL đã tăng tốc.',
        'Không thay nguyên mẫu 28.466 LUT hoặc RTL chính. Mọi speedup dưới đây giả định cùng clock; chưa có LUT hoặc post-route Fmax cho bản tối ưu.','',
        '## 1. Tăng tốc kernel bằng chồng lấp tầng','',
        '| Kernel | RTL nguyên mẫu | Model chồng lấp | Speedup | Giảm chu kỳ |',
        '|---|---:|---:|---:|---:|']
    for label,c in rows:
        text.append(f'| {label} | {c["kernel_measured"]:,} | {c["kernel_overlap_model"]:,} | {c["kernel_speedup"]:.2f}× | {100*(1-c["kernel_overlap_model"]/c["kernel_measured"]):.1f}% |')
    text += ['',
        'NTT N1024 đạt khoảng 985 chu kỳ, gần baseline cũ 984. FFT128 chỉ còn khoảng 2,5% chu kỳ lấy lại từ overlap; không nên kỳ vọng tăng vài lần chỉ từ bỏ rào tầng.',
        'N1024 FFT ở đây là 1.024 thành phần scalar = 512 điểm phức, đúng reference của repo.',
        'Với 16 engine và lịch 45 tích32×32/BF, FFT128 N1024 cần 103.680 tích, cận dưới số học là 6.480 chu kỳ. Model 6.937 đã gần cận này; đây là cận có điều kiện giữ thuật toán/lịch tích hiện tại, không phải cận mọi kiến trúc.','',
        'Model giữ từng stream input của một tầng liền nhau, nhưng cho đọc tầng kế trong khi kết quả tầng trước còn ghi về. Có kiểm cổng 1R/1W, RAW/WAR/WAW, pha chung FFT theo II 3/12/48 và tài nguyên engine.',
        'RTL tương lai cần tách context tầng đọc và tầng ghi; pipeline nhãn, active mask, root và cờ scale cuối tầng. Không được chỉ bỏ điều kiện chờ trong FSM hiện tại.',
        '**N nhỏ:** ép FFT64/128 về pha liên tục có thể chậm hơn rào hiện tại. Lịch này chỉ chọn khi có lợi; các cấu hình nhỏ nên giữ rào, hoặc khảo sát ghép batch độc lập sau. Không tự giảm precision theo N.','',
        '## 2. Host và root mới là khoản lớn của toàn giao dịch','',
        'Bảng sau là **cận thời gian phục vụ bank có điều kiện**, không phải latency RTL đã đo của host mới. Giả định host có burst/buffer, nhận line chồng với phục vụ bank và pipeline read response; giữ nguyên bố cục, một cổng đọc/ghi mỗi bank.',
        'Giữ chi phí cố định đã đo, chưa tính stall phía host/DDR. Cột root multicast thêm giao thức gửi một giá trị32 bit tới mask các lane cùng địa chỉ, chỉ gom các bit-pattern giống hệt.','',
        '| N1024 | Toàn ca hiện tại | Chỉ overlap | + host burst, root nối tiếp | + multicast root |',
        '|---|---:|---:|---:|---:|']
    for label,c in rows:
        if c['logn']!=10:continue
        text.append(f'| {label} | {c["cold_measured"]:,} | {c["cold_overlap_only"]:,} | {c["cold_burst_bank_service_bound"]:,} | {c["cold_burst_multicast_bound"]:,} |')
    text += ['',
        'Các cột toàn ca đều nạp root mới, nạp input và đọc output; không trộn với trường hợp cache đã có root. Đây chưa phải thời gian ký/sinh khóa/encapsulate.',
        'Với line tự nhiên 128 bit: NTT hmin0/FFT32 cần ít nhất một nhịp bank; FFT64 hai nhịp; FFT128 bốn nhịp. Ở FFT128, bốn limb của một phần tử nằm cùng bank, khác row. Không thể mặc định cả ba precision đạt một line/nhịp nếu giữ layout.',
        'Ví dụ FFT128: overlap chỉ 23.894 → 23.718 toàn ca; cải thiện host mới mở ra cận 19.622, thêm multicast root còn 17.394, khoảng 1,37× so với hiện tại. Đây là khả năng từ mô hình, không phải cam kết.',
        'Root multicast FFT128 N1024 giảm 4.480 lượt ghi xuống 2.252; NTT N1024 chỉ 1.072 xuống 1.023. Vì vậy không nên ưu tiên multicast nếu workload chủ yếu là NTT.',
        'Nếu root còn đúng context thì bỏ được cold-load, nhưng không gọi phần lợi do tái dùng cache là speedup số học. Đổi q/chiều/precision/root contract phải vô hiệu hoặc thay đúng context.','',
        '## 3. Correctness PQC: những gì đã và chưa được kiểm','',
        f'- Model rào khớp **{ck["measured_cycle_calibrations"]}/138** số chu kỳ RTL đã đo, bao gồm N, hmin và ba precision.',
        f'- Model overlap replay đúng dữ liệu RAM theo chu kỳ: **{ck["numeric_overlap_replay"]} ca transform + {ck["identity"]} ca identity**, dùng đúng root bit-pattern từ fixture, không tự thay primitive root.',
        f'- Kiểm thêm trực tiếp với capture C R8 Q64.64: **{ck["R8_C_synthetic"]} synthetic + {ck["R8_C_workload"]} FFT/IFFT thật từ workload N512/N1024**, khớp từng bit; root so nguyên bit với C.',
        f'- NTT/INTT theo C NTRUGen: **{ck["NTRUGen_C_NTT"]} ca**, năm prime31 bit, N2..1024, hai chiều. Đây là model, không phải kết quả RTL mới.',
        f'- Multicast tái tạo đúng toàn bộ root đã nạp ở {ck["exact_root_multicast_replays"]} ca. Thử cho đọc trước khi dữ liệu tồn tại đã bị checker bắt.',
        '- Các thay đổi đề xuất giữ precision, phép wrap/carry, 3M, vị trí rounding, root, Montgomery domain và normalization. Chỉ thay thời điểm truyền/tính những phép độc lập.','',
        '**Khoảng trống quan trọng: FFT64 generic không phải FFT64 NTRUGen.**',
        f'Model contract hiện tại không khớp **{ck["NTRUGen_FFT64_native_different_contract"]}/40 vector C FFT64 NTRUGen**; {ck["NTRUGen_FFT64_native_matches"]} ca còn lại trùng ngẫu nhiên hoặc là đồng nhất.',
        'NTRUGen yêu cầu nhân cắt bớt, bảng GM_TAB riêng, signed rounded-half ở mọi tầng inverse trước phép nhân. Nguyên mẫu dùng round-nearest, root thu hẹp từ R8 và scale ở tầng cuối. Cờ floor hiện cũng không điều khiển tích64 bit trong tile.',
        'Vì vậy **không gán hàng FFT64 1.752 chu kỳ cho keygen NTRUGen**, không tuyên bố core hiện hỗ trợ đầy đủ keygen FN-DSA. Phải bổ sung một contract số học riêng, chạy đúng vector C, rồi đo lại cadence/cycle/LUT. Không được sửa expected vector để hợp với RTL.',
        'FFT32/64 vẫn là chế độ số học hợp lệ của accelerator, nhưng chưa phải quyền thay FFT128 trong signer R8. Muốn dùng precision thấp cho một ứng dụng khác cần reference và phân tích sai số của chính ứng dụng đó.',
        'NTT q3329/q8380417 khớp kernel không tự xác nhận toàn ML-KEM/ML-DSA. Cần adapter đúng residue/domain/order/root/scaling và các phép ngoài transform, đặc biệt incomplete NTT/base multiplication ở q3329.',
        'Co-simulation ký/verify đã có trong repo dùng một RTL cũ; **không chuyển kết luận đó sang A + CG hoặc model overlap**. Sau khi có RTL tối ưu, phải replay các lời gọi C bằng output của chính RTL đó, rồi ký/verify (hoặc encapsulate/decapsulate) bằng reference độc lập trước khi chốt ứng dụng.','',
        '## 4. Hướng thực hiện đề nghị','',
        '1. Khóa contract ứng dụng trước: giữ FFT128 R8 cho signing; bổ sung profile FFT64 NTRUGen nếu keygen nằm trong mục tiêu. Không đổi độ chính xác để đạt latency.',
        '2. Tối ưu burst host vì lợi toàn giao dịch lớn nhất; kiểm lưu/đọc đủ word, thứ tự và backpressure, kể cả N nhỏ.',
        '3. Thêm read/write stage context để chồng lấp, ưu tiên NTT; giữ lựa chọn rào ở N nhỏ.',
        '4. Thêm multicast/reuse root nếu trace cho thấy đáng làm; context phải gắn đúng contract và tham số.',
        '5. Mỗi bản chỉ được ghi nhận speedup sau simulation RTL với vector C; sau đó synth đủ host/root và xác nhận vẫn dưới 35k. Chưa dự toán số LUT tăng bằng dư địa 6.534 LUT.','',
        'Muốn tính tăng tốc toàn ứng dụng cần trace số lời gọi từng N/format/chiều, cache miss và thời gian phần C còn lại. Không suy từ speedup một kernel ra speedup toàn PQC.','',
        '## Dữ liệu và chạy lại','',
        '- [Model](../../model/a_cg_speed_estimate.py), chạy `python -X utf8 model/a_cg_speed_estimate.py`.',
        '- [JSON mọi cấu hình, giả định và SHA256](a_cg_speed_estimate.json).',
        '- [RTL và số đo hiện tại](a_cg_prototype.md).',
        '- [Contract R8](../../docs/numeric_contract.md), [contract NTRUGen](../../spec/FlexTransform/2.0/01_so_hoc_kernel.md).','']
    (ROOT/'study/results/a_cg_speed_estimate.md').write_text('\n'.join(text),encoding='utf-8')


def main():
    measured=json.loads((ROOT/'study/results/a_cg_prototype.json').read_text(encoding='utf-8'))
    cases=[];checks=Counter();cache={};roots_cache={}
    for idx,d in enumerate(fixtures()):
        fft,fmt,ln,hm,inv,q=(d[k] for k in ('fft','fmt','logn','hmin','inverse','q'))
        m=1<<max(0,ln-1 if fft else ln-hm);fl=1<<fmt if fft else 0;planes=2*fl if fft else 1<<hm
        key=(m,planes,inv,fl)
        if key not in cache:cache[key]=plan(*key,False),plan(*key,True)
        barrier,overlap=cache[key]
        actual=measured['cases'][idx]['kernel_cycles']
        assert barrier['cycles']==actual,(idx,barrier['cycles'],actual)
        checks['measured_cycle_calibrations']+=1
        # Execute chronological physical RAM transactions with exact arithmetic.
        if ln==0 or (fft and ln==1):
            assert d['a']==d['z'];checks['identity']+=1
        else:
            # Use exact fixture constants. A valid alternative primitive root
            # would permute/alter the application's transform representation.
            gm=[None]*(max(e['root'] for layer in overlap['layers'] for e in layer)+1)
            for stage,layer in enumerate(overlap['layers']):
                mask,base,period_mask=d['desc'][3*stage:3*stage+3]
                for e in layer:
                    addr=base+(e['k']&period_mask)*(planes if fft else 1)
                    row=d['roots'][e['t']]
                    value=(tuple(cg.fp.wrap(sum(row[addr+part*fl+j]<<(32*j) for j in range(fl)),32*fl)
                                 for part in (0,1)) if fft else row[addr])
                    assert gm[e['root']] in (None,value)
                    gm[e['root']]=value
            assert cg.replay(overlap,d['a'],q,gm,gm)==d['z'],idx
            checks['numeric_overlap_replay']+=1
        # Multicast estimate only: one 32-bit value to all selected root lanes
        # at a common row. Verify every lane receives its exact fixture bits.
        reconstructed=[[None]*d['root_rows'] for _ in range(16)];groups=0
        for row in range(d['root_rows']):
            by_value={}
            for t in range(16):by_value.setdefault(d['roots'][t][row],[]).append(t)
            for value,lanes in by_value.items():
                groups+=1
                for t in lanes:reconstructed[t][row]=value
        assert all(list(a)==b for a,b in zip(d['roots'],reconstructed))
        checks['exact_root_multicast_replays']+=1
        host=cg.host_cost(overlap)
        # N=1 FFT stores one scalar, whereas the complex-plane model reserves
        # two. Only active words are relevant to real host traffic.
        if fft and ln==0:
            host={k:dict(cycles_128bit_lines_serialized=d['words'],max_subcycles_per_line=d['words']) for k in ('load','readback')}
        lines=(d['words']+3)//4
        io=host['load']['cycles_128bit_lines_serialized']+host['readback']['cycles_128bit_lines_serialized']
        # Remaining command/pipeline overhead is measured, not hidden in the
        # bank service bound. Keep it even after the proposed host improvements.
        root_serial=16*d['root_rows']
        fixed=measured['cases'][idx]['all_host_cycles']-actual-root_serial-12*lines
        assert fixed>=0,(idx,fixed)
        # Burst proposal requires overlapped line accept/service and a pipelined
        # read response. Counts bank service cycles plus retained fixed overhead.
        kernel=overlap['cycles']
        full_old=measured['cases'][idx]['all_host_cycles']
        full_kernel_only=full_old-actual+kernel
        full_host_bound=fixed+kernel+root_serial+io
        full_multicast_bound=fixed+kernel+groups+io
        cases.append(dict(case=idx,name=measured['cases'][idx]['name'],fft=fft,fmt=fmt,logn=ln,hmin=hm,inverse=inv,q=q,
            kernel_measured=actual,kernel_overlap_model=kernel,kernel_speedup=actual/kernel if kernel else 1,
            starts=overlap['starts'],host_bank_service=host,
            host_fixed_overhead=fixed,cold_measured=full_old,cold_overlap_only=full_kernel_only,
            cold_burst_bank_service_bound=full_host_bound,cold_burst_multicast_bound=full_multicast_bound,
            root_serial_writes=root_serial,root_multicast_writes=groups,
            warm_burst_bank_service_bound=fixed+kernel+io))
    # Mutation: a required first-layer value has not yet been written.
    import copy
    bad=copy.deepcopy(cache[(1024,1,False,0)][1])
    for e in bad['layers'][1]:
        e['reads']=[(a,c-10000,p,pl,port) for a,c,p,pl,port in e['reads']]
    tabs=cg.sc.Tables()
    try:cg.replay(bad,[0]*1024,12289,tabs.gm[12289],tabs.igm[12289])
    except (AssertionError,KeyError):checks['early_read_mutation_detected']+=1
    else:raise AssertionError('Early read mutation not detected')
    c_reference_checks(cache,checks)
    result=dict(date='2026-11-02',kind='cycle estimate with physical RAM numeric replay, not optimized RTL',
        assumptions=['16 engines and unchanged bit-accurate arithmetic.',
            'Shared FFT program requires all BF starts aligned modulo II=3/12/48.',
            'Each stage input stream is contiguous; stages overlap only input versus pending outputs.',
            'Separate read/write stage contexts, pipelined mask/root/scale metadata are required in future RTL.',
            'Host estimates are bank-service bounds; burst line buffering and read-response pipelining are not implemented.',
            'Root multicast needs a runtime destination mask; host software and external memory bandwidth are excluded.',
            'Same clock assumed; new LUT count and post-route Fmax are unknown.'],
        checks=dict(checks),cases=cases,
        compatibility_gaps=['Current generic FFT64 is not native NTRUGen FFT64; 35/40 C native vectors differ.',
                            'Optimized RTL and full-application C/RTL co-simulation have not been run.'],
        sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [Path(__file__),ROOT/'model/cg_bank4_model.py',ROOT/'study/results/a_cg_prototype.json',
                 ROOT/'study/build/a_cg_prototype/fixtures.bin',ROOT/'experiments/a_cg/rtl/a_cg_core.sv',ROOT/'experiments/a_cg/rtl/tile_a.sv',
                 ROOT/'study/vectors/r8/synthetic.jsonl.gz',ROOT/'study/vectors/r8/workload_512.jsonl.gz',
                 ROOT/'study/vectors/r8/workload_1024.jsonl.gz',ROOT/'study/build/ntrugen_mp31/dump.bin',
                 ROOT/'spec/FlexTransform/2.0/assets/kernel/fft_ntrugen.jsonl']})
    out=ROOT/'study/results';(out/'a_cg_speed_estimate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_report(result)
    print('CHECKS',dict(checks))
    for c in cases:
        if c['logn']==10 and not c['inverse'] and ((c['fft']) or c['q']==12289):
            print(json.dumps(c,ensure_ascii=False))


if __name__=='__main__':main()
