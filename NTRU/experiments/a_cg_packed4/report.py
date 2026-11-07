"""Read-only validation/report of the private candidate; never refresh baseline hashes."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'study/build/a_cg_packed4'
BASE=ROOT/'study/build/a_cg_z020_system160'

def read(path):return path.read_text(encoding='utf-8-sig',errors='replace')
def cases(path):
    return [dict(re.findall(r'(\w+)=(\S+)',line)) for line in read(path).splitlines() if line.startswith('CASE ')]
def synth(which):
    folder=BUILD/('synth_'+which)
    util=read(folder/'util.rpt')
    def number(label):
        m=re.search(r'^\|\s*'+re.escape(label)+r'\s*\|\s*([\d,]+)',util,re.M)
        assert m,label
        return int(m[1].replace(',',''))
    metrics=dict(line.split('=',1) for line in read(folder/'metrics.txt').splitlines())
    assert metrics['DSP48']=='64' and metrics['RAMB18']=='48' and metrics['BLACKBOX']=='0',metrics
    return dict(lut=number('Slice LUTs*'),ff=number('Slice Registers'),dsp=int(metrics['DSP48']),
                ramb18=int(metrics['RAMB18']),internal_setup_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),
                internal_hold_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS']))

def main():
    manifest=json.loads(read(BUILD/'final_source_manifest.json'))
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
    assert all(p.read_bytes()==(BUILD/'rtl_final'/p.name).read_bytes() for p in (HERE/'rtl').iterdir())
    new,old=cases(BUILD/'sim.log'),cases(BASE/'sim.log')
    assert len(new)==len(old)==1026
    packed=[]
    for n,o in zip(new,old):
        for key in ['fft','fmt','logn','hmin','inverse','packed','jobs','native','words','q']:
            assert n[key]==o[key],(key,n,o)
        assert n['errors']=='0'
        if n['packed']=='1':
            assert int(n['cycles'])<=int(o['cycles']),(n,o)
            packed.append(dict(**{k:int(n[k]) for k in ['logn','hmin','inverse','jobs','q']},
                               old_cycles=int(o['cycles']),new_cycles=int(n['cycles']),
                               speedup=int(o['cycles'])/int(n['cycles'])))
        else:assert n['cycles']==o['cycles'],(n,o)
    assert 'TOTAL cases=1026 errors=0 PASS' in read(BUILD/'sim.log')
    assert 'AXI_PROTOCOL' in read(BUILD/'sim.log')
    assert 'PACKED4_TILE packets=16800 butterflies=33600 PASS' in read(BUILD/'tile_shared.log')
    assert 'PACKED4_RESET both_streams_inflight=1 PASS' in read(BUILD/'tile_shared.log')
    spans=[int(x) for x in re.findall(r'first_to_last_clocks=(\d+)',read(BUILD/'tile_shared.log'))]
    assert len(spans)==28 and max(spans)<=449
    assert 'AXI_RESET aw_split=1 w_split=1 b_pending=1 r_pending=1 PASS' in read(BUILD/'axil_reset.log')
    four=re.search(r'FOUR_STATE TOTAL cases=(\d+) PASS',read(BUILD/'four_state.log'))
    assert four
    app=json.loads(read(BUILD/'application/application_results.json'))
    oldapp=json.loads(read(BASE/'application/application_results.json'))
    assert app['artifacts_sha256']==oldapp['artifacts_sha256'] and len(app['artifacts_sha256'])==14
    assert len(app['independent_verification'])==4
    assert all(v['valid']==0 and v['wrong_message']!=0 for v in app['independent_verification'])
    assert json.loads(read(BUILD/'application/rtl_records.json'))['calls']==74
    synths={which:synth(which) for which in ['baseline','candidate','candidate_shared_t']}
    result=dict(cases=1026,packed_cases=len(packed),tile_butterflies=33600,four_state_cases=int(four[1]),
                c_transform_calls=74,identical_application_artifacts=14,independently_verified_signatures=4,
                unchanged_nonpacked_cycles=True,synthesis=synths,packed=packed,
                source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'rtl').iterdir()},
                scope='OOC AXI host/core including data/root; synthesis only; no P&R or new board timing sign-off')
    (BUILD/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    rows=['# Packed16 dùng cả bốn leaf — kết quả nguyên mẫu',
          '', 'Nguồn riêng: `experiments/a_cg_packed4/rtl/`. Baseline 160 MHz không đổi. Chưa commit.',
          '', '## Tài nguyên: cùng top AXI host + core + data/root, chỉ synth',
          '', '| Bản | LUT | FF | DSP | RAMB18 | Setup nội bộ (ns) | Hold nội bộ (ns) |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for key,label in [('baseline','Baseline, synth lại cùng flow'),('candidate','Hai luồng, T-high riêng'),('candidate_shared_t','Hai luồng, T-high dùng chung (RTL hiện tại)')]:
        m=synths[key]
        rows.append(f"| {label} | {m['lut']:,} | {m['ff']:,} | {m['dsp']} | {m['ramb18']} | {m['internal_setup_ns']:+.3f} | {m['internal_hold_ns']:+.3f} |")
    rows+=['','Part `xc7z020clg400-2`, Vivado 2018.1, chu kỳ 6,25 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns, input jitter 0,300 ns.',
           'Các con số OOC này không bao gồm PS7/interconnect/MMCM/reset của top board. Không thay số P&R toàn hệ thống 31.242 LUT của baseline.',
           'Setup synth âm là chưa đạt ràng buộc trong mô hình ước tính này. Chưa P&R hoặc sign-off 160 MHz cho ứng viên; không thừa kế sign-off baseline.',
           '', '## Chu kỳ kernel đo qua AXI', '', '| q | N | hmin | Jobs | Hướng | Baseline packed16 | Bốn leaf | Tăng tốc |',
           '|---:|---:|---:|---:|---|---:|---:|---:|']
    for q,ln,hm,jobs in [(3329,8,1,1),(3329,8,1,4),(12289,9,0,1),(12289,10,0,1),(12289,10,0,2)]:
        for inv in [0,1]:
            matching=[r for r in packed if (r['q'],r['logn'],r['hmin'],r['jobs'],r['inverse'])==(q,ln,hm,jobs,inv)]
            if not matching:continue
            r=matching[0]
            rows.append(f"| {q} | {1<<ln} | {hm} | {jobs} | {'INTT' if inv else 'NTT'} | {r['old_cycles']} | {r['new_cycles']} | {r['speedup']:.3f}× |")
    rows+=['',f"{len(packed)} ca packed16 qua kiểm; mọi ca không tăng chu kỳ. {1026-len(packed)} ca nonpacked giữ nguyên chu kỳ và kết quả.",
           'Đây là chu kỳ kernel; không quy đổi thành tốc độ toàn bộ signer hay thông lượng AXI end-to-end.',
           '', '## Correctness và mức sử dụng leaf',
           '', '- 1.026 ca FFT32/64/128, scalar/packed NTT, nhiều modulus và batch qua AXI: không sai số.',
           '- Oracle tile độc lập: 16.800 gói / 33.600 butterfly, hai slot, CT/GS, halving, pairing, bubbles, enable stall, dữ liệu biên.',
           '- 300 gói bão hòa trong 448–449 khoảng chu kỳ. Có chu kỳ cả bốn leaf chứa phép toán hợp lệ; thông lượng ổn định 4 butterfly/3 chu kỳ/tile.',
           '- Reset khi cả hai luồng đang xử lý: không có response cũ sau reset.',
           f'- {four[1]} ca four-state tập trung packed16 ở cấp lõi: PASS, có N=2/N1024, incomplete NTT và batch.',
           '- C replay: 74 transform; 14 artifact trùng từng byte; 4 chữ ký xác minh độc lập; altered-live-input bị từ chối.',
           '- AXI split AW/W, B/R stalls, WSTRB, lỗi địa chỉ/lệnh và reset giao dịch: PASS.',
           '', '## Phần thay đổi',
           '', 'Chia leaf0/1 và leaf2/3 thành hai luồng lệch một chu kỳ. Tích thô được căn độ trễ năm chu kỳ và phản hồi riêng từng nhóm. Hai luồng dùng chung T-high/NZ history, reducer cuối, add/sub và side/tag RAM. Không thêm DSP hoặc cổng BRAM.',
           'Core đọc ở hai pha mỗi ba chu kỳ; planner đổi thời điểm phát và gap giữa tầng, kiểm bank/RAW và phiên bản dữ liệu. Transform ngắn vẫn chịu fill/drain; batch giúp tăng lượng công việc độc lập.',
           '', 'Nguồn và constraints đã đóng băng trong `study/build/a_cg_packed4/rtl_final/` và `final_source_manifest.json`. Kết quả máy đọc: `study/build/a_cg_packed4/results.json`.',
           'Bản đầu T-high riêng giữ ở `variants/separate_history/tile_a.sv`, `synth_candidate`, `sim_v0.log`, `application_v0`. Four-state v0 dừng khi đổi bản, không tính là PASS.',
           'Kiểm lại bằng `python -X utf8 experiments/a_cg_packed4/report.py` và `python -X utf8 scripts/check_baseline.py`.']
    (ROOT/'study/results/a_cg_packed4.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print('PACKED4_VALIDATED',json.dumps({k:v for k,v in result.items() if k not in ['packed','source_sha256']}))

if __name__=='__main__':main()
