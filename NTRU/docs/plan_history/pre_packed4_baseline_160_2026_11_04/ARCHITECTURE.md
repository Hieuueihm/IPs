# FlexTransform — kiến trúc baseline 160 MHz

**Hiện hành từ 2026-11-04:** `a_cg_z020_system160`, được người dùng chấp nhận sau sign-off STA toàn hệ thống trên XC7Z020-CLG400-2.

- [Mô tả kiến trúc hiện hành](docs/architecture_v1.md): PS7–AXI, 16 tile, 32 bank, root và constant-geometry.
- [Nguồn và kết quả chuẩn](experiments/BASELINE.md), [manifest](experiments/BASELINE.json).
- [Contract 3.0](spec/FlexTransform/3.0/README.md): FFT32/64/128, native NTRUGen64, NTT đa modulus/packed16/batch và giao tiếp thực tế.
- [Kết quả sign-off](study/results/a_cg_z020_system160.md): **31.242 LUT, 64 DSP, 48 RAMB18; 160 MHz; setup +0,038 ns, hold +0,011 ns**.

Cốt lõi là chia sẻ phép nhân và các chuỗi cộng/trừ giữa FFT/NTT, tăng độ rộng bằng lượt tính limb trong tile. Baseline không ghép nhiều tile để tạo một phép nhân rộng. Bộ nhớ dữ liệu 32 bank `256×32`, root 16 bank `512×32`, host AXI-Lite, scale IFFT ở đường đọc host.

Phạm vi STA gồm PS7, AXI, MMCM/reset và toàn core/data/root. DDR/ngoại vi tắt, chưa đo board; phần ngoài transform vẫn ở C. Không suy nghiệm thu toàn spec 2.0 hoặc full signer từ kết quả này.

Các mục v0.4 và thử nghiệm F16/R32, radix-4, số bank hoặc ZCU106 trước đây được giữ nguyên trong [bản lưu](docs/plan_history/pre_baseline_160_2026_11_04/ARCHITECTURE.md). Chúng không còn mô tả baseline hiện hành. [PLAN hiện hành](PLAN.md).
