# Tuning riêng của A + CG

Giữ nguyên bản 34.062 LUT tại `experiments/a_cg_fast`, production HDL, PLAN và
spec. Top trong bản này vẫn có tên module `a_cg_fast`; đường dẫn source/build
được tách hoàn toàn sang `a_cg_tune`.

Thay đổi: FFT128 issue interval 45 chu kỳ; host map bằng một base và hai vector
cơ sở XOR. Các contract và giới hạn giao diện giữ như
[bản trước](../a_cg_fast/README.md), gồm native NTRUGen64 và cache một context.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File experiments/a_cg_tune/run.ps1 -FourState -Synthesize
python -X utf8 experiments/a_cg_tune/check_host_map.py
python -X utf8 experiments/a_cg_tune/application.py
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_tune/audit.tcl -log study/build/a_cg_tune/audit.log -journal study/build/a_cg_tune/audit.jou
python -X utf8 experiments/a_cg_tune/report.py
```

Phụ thuộc công cụ/capture C như README của bản trước. Báo cáo ở
`study/results/a_cg_tune.md`, raw reports/checkpoint ở `study/build/a_cg_tune`.
Không tự commit hoặc thay baseline sau khi kiểm thử.
