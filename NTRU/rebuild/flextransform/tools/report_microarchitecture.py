"""Summarize the completed model run, with numerical/PPA scope labels."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
def main():
    cfg=json.loads((HERE/'design.json').read_text())
    r=json.loads((ROOT/cfg['microarchitecture_contract']['full_report']).read_text())
    assert r['full'] and r['status']=='MODEL_PASS' and r['cases']==730
    lines=['# Microarchitecture0.2 — hồ sơ khóa thiết kế','','Ngày2026-11-05. **Bốn phần đã khóa ở mức thiết kế; chưa có RTL/PPA mới. Baseline không thay đổi.**','',
        '| Phần | Source chuẩn | Bằng chứng |','|---|---|---|',
        '| Port | microarchitecture/ports.json, spec08 | 23 module/24 source dự kiến, width/direction cụ thể |',
        '| Clock | microarchitecture/timing.json, spec09, cycles/*.csv | 11 bảng từng cạnh, không có lựa chọn pipeline mở |',
        '| FSM | microarchitecture/fsm.json, spec10 | 7 FSM, priority/guard/action/default/reset cụ thể |',
        '| Liveness | verification/model/liveness.py, spec11 | 730 trường hợp full, nguồn/gap/hash riêng |','',
        '## Các kiểm tra đã chạy','','| Kiểm tra design model | Kết quả |','|---|---:|',
        f'| Schedule/memory/resource cases | {r["cases"]} PASS |',
        f'| FSM guard assignments | {r["extra"]["fsm"]["total_guard_assignments"]} |',
        f'| C4 vector bit-exact | {r["extra"]["guard_math"]["c4_vectors"]} |',
        f'| C0–C3 bit-slice vectors | {r["extra"]["guard_math"]["c2_c3_vectors"]} |',
        f'| FIFO cycles / simultaneous push-pop | {r["extra"]["fifo_reset"]["fifo_cycles"]} / {r["extra"]["fifo_reset"]["fifo_simultaneous_cases"]} |',
        f'| Active masks | {r["extra"]["fifo_reset"]["active_masks"]} |',
        f'| Abstract reset cutpoints | {r["extra"]["fifo_reset"]["abort_cutpoints"]} |',
        f'| Negative controls caught | {len(r["extra"]["negative_controls"])} |','',
        'Model kiểm fixed four-source routing, hai row/bank-half, root address chung, bank RAW/dependencies, operand/side/sum/partial identity, history/group, queue và drain. Không chỉ kiểm số packet vào bằng số packet ra.','',
        '## Storage peak','','| Resource | Capacity | Peak |','|---|---:|---:|']
    for name,cap,key in [('Side reserved',16,'side_reserved'),('Side written',16,'side_written'),('NTT outstanding (counter5)',31,'outstanding'),('Write contexts',16,'contexts')]:
        lines.append(f'| {name} | {cap} | {r["peaks"][key]} |')
    for fmt,cap in [(0,8),(1,4),(2,2)]:
        peak=max(x['peaks'].get('fft_buffers',0) for x in r['results'] if x['fft'] and x['fmt']==fmt)
        lines.append(f'| FFT{32*(1<<fmt)} buffer | {cap} | {peak} |')
    lines+=['','## Chu kỳ: model mới so với số RTL baseline đã đo','','| Workload xuôi | Baseline RTL đo | Locked model0.2 | Delta |','|---|---:|---:|---:|']
    for target in cfg['reference_cycles_forward']:
        vals=[x['cycles'] for x in r['results'] if not x['inverse'] and all(x[k]==target[k] for k in ['fft','fmt','logn','hmin','packed','jobs_log','native'])]
        assert len(vals)==1;cy=vals[0]
        assert cy<=target['cycles']+cfg['rewrite_cycle_checkpoint']['max_additional_core_cycles']
        lines.append(f'| {target["name"]} | {target["cycles"]} | {cy} | {cy-target["cycles"]:+} |')
    lines+=['','Cột model không phải số đo trên RTL mới. q không làm đổi control shape; model q/N được nhận diện theo mode, N, hmin và batch. Chưa chạy lại1.026 kernel/C replay vì chưa có implementation mới.','',
        '## Cách sử dụng','','Bắt đầu từ ft_defs và leaf/addsub/C4 units; dùng các CSV để viết latency assertions. RTL phải khớp port và từng cạnh đã khóa. Một thay đổi pipeline cần version mới và full model report mới.','',
        'PPA, X propagation, AXI/reset thật và toàn bộ numerical RTL vẫn là các gate tiếp theo; 64DSP/48BRAM/35kLUT/160MHz là target. Không chuyển MODEL_PASS thành RTL_PASS hoặc timing signoff.','']
    (HERE/'docs/MICROARCH_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('MICROARCH_REVIEW_EMITTED')
if __name__=='__main__':main()
