# Ablation riêng cho baseline 3.1

Mọi RTL đối chứng nằm trong `variants/`; báo cáo, mô phỏng và checkpoint chỉ ghi
vào `study/build/paper_ablation31/`. Không cập nhật manifest hay RTL baseline.

## Các biến thí nghiệm

| Bản | Thay đổi so với reference | Câu hỏi |
|---|---|---|
| reference | Không đổi RTL | Mốc đo cùng flow synthesis |
| single_stream | Chỉ nhận một nhóm packed16, lịch cấp 1/3 chu kỳ | Chi phí/lợi ích của nhóm packed thứ hai |
| separate_history | Giữ hai nhóm, tách lịch sử T_hi theo nhóm và scalar | Dùng chung trạng thái tiết kiệm được bao nhiêu? |
| sparse_feed | Giữ tile reference; cấp packed 1/3 thay vì 2/3 chu kỳ | Tile mạnh có ích không nếu bộ nhớ không cấp đủ? |
| split_domains | Một tile FFT chuyên biệt và một tile NTT chuyên biệt, vẫn chung host/data/root | Lợi ích số học hợp nhất khi không nhân đôi bộ nhớ |
| dedicated_mont32 | Hai bộ nhân phụ cho m và mq của scalar NTT32; tăng lịch và side RAM để II=1 | Cái giá diện tích để bỏ ba lượt reduction |

Mọi bản giữ FFT32/64/128, hợp đồng làm tròn/wrap R8 và NTRUGen64, scalar
NTT đa modulus, packed16, CT/GS, batch, AXI và root RAM. Không buộc bỏ một chế độ
để làm nhỏ mạch. Bản single_stream cố ý giảm throughput packed, không giảm phép tính.
Bản split_domains chỉ tách số học, không phải hai IP hoàn chỉnh riêng biệt.

## Phương pháp đo

- Vivado 2018.1, `xc7z020clg400-2`, 6.250 ns, jitter 0.300 ns,
  uncertainty setup/hold 0.100/0.050 ns.
- Synthesis OOC top `a_cg_axil`, toàn bộ host AXI-lite, 32 data BRAM và 16 root
  BRAM đều hoạt động; cùng flatten_hierarchy rebuilt, không directive riêng cho từng bản.
- So sánh các hàng synthesis với nhau. Kết quả hệ thống PS7 sau routing của
  baseline được ghi riêng; không cộng ước lượng shell vào số OOC rồi gọi là P&R.
- 1.026 ca AXI bit-exact; four-state tập trung 12 ca cho single/split, 4 ca
  packed cho history/sparse, 2 ca scalar cho dedicated; reset AXI và các vector từ
  74 lời gọi C ứng dụng. Golden không lấy từ RTL đối chứng. Đổi lịch không đổi input/output/root.
- Phân rã routed baseline từ checkpoint signoff theo hierarchy. LUT hợp nhất qua
  biên module có thể khiến tổng module con lệch nhẹ khỏi cha; phải ghi residual,
  không ép mọi LUT chọn dữ liệu thành số học hoặc điều khiển.
- Đây là ablation nội bộ, không phải phép so PPA với tác giả khác và không tự
  chứng minh novelty hay tính an toàn mật mã của toàn bộ scheme.

## Chạy lại

`prepare.py` tạo snapshot một lần và từ chối ghi đè snapshot hiện có. Các file
generator ghi rõ cách biến đổi; `input_manifest.json` là dấu vết ban đầu, báo cáo
cuối ghi hash nguồn thực dùng. `provision_auxiliary.py` tạo các bản copy riêng của
orchestrator C. `application_linux.py` chạy C trên Linux-local storage rồi chép
evidence về build riêng để tránh chi phí ghi trace qua DrvFS. Không dùng script
từ baseline để ghi đè kết quả cũ.

```powershell
& experiments/paper_ablation31/run_one.ps1 -Variant single_stream -Stage sim
& experiments/paper_ablation31/run_one.ps1 -Variant single_stream -Stage synth
python -X utf8 experiments/paper_ablation31/verify_extra.py single_stream
python -X utf8 experiments/paper_ablation31/variants/single_stream/application.py
```

`synth.tcl` từ chối ghi đè checkpoint đã hoàn tất. P&R có entry point riêng trong
`run_one.ps1`; không được gọi kết quả synth là signoff 160 MHz. Baseline routed
được đọc bởi `decompose.tcl`, không được ghi lại.
