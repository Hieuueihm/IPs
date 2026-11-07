# Microarchitecture0.2 — hồ sơ khóa thiết kế

Ngày2026-11-05. **Bốn phần đã khóa ở mức thiết kế; chưa có RTL/PPA mới. Baseline không thay đổi.**

| Phần | Source chuẩn | Bằng chứng |
|---|---|---|
| Port | microarchitecture/ports.json, spec08 | 23 module/24 source dự kiến, width/direction cụ thể |
| Clock | microarchitecture/timing.json, spec09, cycles/*.csv | 11 bảng từng cạnh, không có lựa chọn pipeline mở |
| FSM | microarchitecture/fsm.json, spec10 | 7 FSM, priority/guard/action/default/reset cụ thể |
| Liveness | verification/model/liveness.py, spec11 | 730 trường hợp full, nguồn/gap/hash riêng |

## Các kiểm tra đã chạy

| Kiểm tra design model | Kết quả |
|---|---:|
| Schedule/memory/resource cases | 730 PASS |
| FSM guard assignments | 4398 |
| C4 vector bit-exact | 19025 |
| C0–C3 bit-slice vectors | 13500 |
| FIFO cycles / simultaneous push-pop | 20000 / 4881 |
| Active masks | 65535 |
| Abstract reset cutpoints | 686 |
| Negative controls caught | 11 |

Model kiểm fixed four-source routing, hai row/bank-half, root address chung, bank RAW/dependencies, operand/side/sum/partial identity, history/group, queue và drain. Không chỉ kiểm số packet vào bằng số packet ra.

## Storage peak

| Resource | Capacity | Peak |
|---|---:|---:|
| Side reserved | 16 | 13 |
| Side written | 16 | 12 |
| NTT outstanding (counter5) | 31 | 14 |
| Write contexts | 16 | 2 |
| FFT32 buffer | 8 | 6 |
| FFT64 buffer | 4 | 3 |
| FFT128 buffer | 2 | 2 |

## Chu kỳ: model mới so với số RTL baseline đã đo

| Workload xuôi | Baseline RTL đo | Locked model0.2 | Delta |
|---|---:|---:|---:|
| FFT32_N1024 | 454 | 456 | +2 |
| FFT64_N1024 | 1752 | 1754 | +2 |
| FFT128_N1024 | 6508 | 6510 | +2 |
| NTT12289_N1024_packed | 391 | 393 | +2 |
| NTT3329_N256_packed | 214 | 216 | +2 |
| NTT2013265921_N1024_scalar | 987 | 989 | +2 |
| NTT8380417_N256_scalar | 324 | 326 | +2 |
| NTT12289_N32_packed_batch16 | 148 | 150 | +2 |

Cột model không phải số đo trên RTL mới. q không làm đổi control shape; model q/N được nhận diện theo mode, N, hmin và batch. Chưa chạy lại1.026 kernel/C replay vì chưa có implementation mới.

## Cách sử dụng

Bắt đầu từ ft_defs và leaf/addsub/C4 units; dùng các CSV để viết latency assertions. RTL phải khớp port và từng cạnh đã khóa. Một thay đổi pipeline cần version mới và full model report mới.

PPA, X propagation, AXI/reset thật và toàn bộ numerical RTL vẫn là các gate tiếp theo; 64DSP/48BRAM/35kLUT/160MHz là target. Không chuyển MODEL_PASS thành RTL_PASS hoặc timing signoff.

