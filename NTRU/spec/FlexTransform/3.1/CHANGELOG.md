# 3.1 — packed16 dùng cả bốn leaf, 2026-11-04

Implementation được người dùng nhận: **a_cg_packed4_system160**. Thay baseline 3.0; [registry hiện hành](../../../experiments/BASELINE.md). Bản 3.0 giữ lịch sử trong thư mục riêng.

- FFT/NTT numerical semantics, precision, q/qinv, wrap/round, pairing, halving, AXI register map và bộ nhớ giữ nguyên.
- Packed16 dùng hai nhóm leaf0/1 và leaf2/3, nhận ở pha0/1: hai gói mỗi ba clock, mỗi gói hai butterfly. NTT32 vẫn một gói mỗi ba clock; FFT vẫn ghép 32×32 và tính theo limb.
- Packed lấy raw products trước fusion, căn độ trễ 5 clock; phản hồi riêng mỗi nhóm, dùng chung T-high/NZ history, reducer cuối, add/sub và side/tag. Không thêm DSP/cổng BRAM.
- Lõi đọc ở pha1/2, planner phát seq tại 3*(seq//2)+seq%2 và sinh lại gap/descriptor; không sao chép lịch 3.0. Header port và AXI ABI giữ nguyên nhưng scheduling contract đổi nên tăng minor version.
- Toàn hệ thống xc7z020clg400-2 sau P&R: 160 MHz, 34.277 LUT, 33.397 FF, 64 DSP, 48 RAMB18, setup +0,178 ns, hold +0,032 ns. Không suy số P&R từ synth.
- Coverage mới: 1.026 ca AXI, 33.600 butterfly tile, 10 ca four-state packed, 74 transform C/14 artifact/4 chữ ký. Coverage arithmetic 38 ca/12 mode của 3.0 giữ làm lịch sử; IP reset kế thừa cấu hình không đổi.

Nâng baseline cập nhật registry, spec và điểm vào build/kiểm; không sửa bốn file RTL hoặc DCP đã đo. Nguồn chức năng a_cg_packed4 và bản tích hợp a_cg_packed4_system160 được kiểm byte-equivalence. Chưa full signer RTL/chạy board; các yêu cầu ngoài phạm vi của 2.0 vẫn giữ làm lịch sử.
