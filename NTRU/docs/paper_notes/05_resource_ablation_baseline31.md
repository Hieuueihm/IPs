# Phân rã tài nguyên và ablation baseline 3.1

Các số dưới đây là phép đo trên các bản riêng, giữ `xc7z020clg400-2` và contract số học. Không đổi baseline đã nhận.

## 1. Kết quả chính

- Hợp nhất đường FFT/NTT tiết kiệm **4,860 LUT (12.45%) và 64 DSP (50%)** so với hai đường số học chuyên biệt vẫn dùng chung host/data/root.
- Dùng chung lịch sử `T_hi` tiết kiệm **1,208 LUT, 1,056 FF**, không đổi chu kỳ.
- Hai nhóm packed16 tốn thêm **1,124 LUT** so với một nhóm. Lợi ích phụ thuộc kích thước và batch; không gọi mọi workload là nhanh gấp đôi.
- Toàn bộ đối chứng giữ đủ các mode. Không có hàng nào được làm nhỏ bằng cách bỏ FFT rộng, giảm precision hay giới hạn lại tập modulus.

## 2. Điều kiện đo và phạm vi

Vivado 2018.1; synthesis OOC `a_cg_axil`, flatten_hierarchy rebuilt. Clock 6.250 ns, jitter 0.300 ns, setup/hold uncertainty 0.100/0.050 ns. Tất cả hàng synthesis tính đủ host AXI-lite, command, executor, tile, data RAM và root RAM. PS7/interconnect/MMCM/reset ngoài accelerator không nằm trong hàng OOC.

Phân rã riêng dùng checkpoint **đã route** của hệ thống baseline: 34.277 LUT, 33.397 FF, 64 DSP, 48 RAMB18; setup +0,178 ns, hold +0,032 ns tại 160 MHz. Không cộng một shell ước lượng vào OOC rồi gọi thành kết quả toàn hệ thống. Không P&R lại các ablation trong bộ đo này.

WNS synthesis dùng mô hình routing ước lượng. Nó không phải signoff hoặc Fmax đo được. Cả sáu bản cùng worst path host `wstrb_reg[0]/C → cmd_cfg_reg/R`, 11 tầng logic (5 CARRY4), nên cùng WNS −0,531 ns không có nghĩa các datapath có timing bằng nhau. Chỉ baseline có bằng chứng signoff hệ thống 160 MHz.

## 3. Bảng tài nguyên cùng flow synthesis

| Bản | LUT | FF | LUTRAM | SRL | DSP48 | RAMB18 | WNS reg→reg synth (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| reference | 34,185 | 32,855 | 2,496 | 897 | 64 | 48 | -0.531 |
| single_stream | 33,061 | 31,719 | 2,496 | 817 | 64 | 48 | -0.531 |
| separate_history | 35,393 | 33,911 | 2,496 | 1,953 | 64 | 48 | -0.531 |
| sparse_feed | 34,280 | 32,935 | 2,496 | 897 | 64 | 48 | -0.531 |
| split_domains | 39,045 | 41,444 | 2,948 | 897 | 128 | 48 | -0.531 |
| dedicated_mont32 | 35,008 | 33,959 | 2,496 | 897 | 176 | 48 | -0.531 |

Mọi netlist có 0 black box. LUTRAM/SRL là các thành phần đã tính trong tổng LUT, không cộng thêm lần nữa. `single_stream` là ablation trên tổ chức tile hiện tại, không phải một thiết kế một luồng được tối ưu độc lập đến cùng. Mức +1.124 LUT chỉ là chênh lệch hai snapshot matched này, không thay thế phép so với baseline 3.0 hoặc kiến trúc một luồng tốt nhất.

## 4. Chu kỳ kernel đo qua RTL

| Workload xuôi | reference | single_stream | separate_history | sparse_feed | split_domains | dedicated_mont32 |
|---|---:|---:|---:|---:|---:|---:|
| Packed q=12289 N1024 | 391 | 531 | 391 | 531 | 391 | 391 |
| Packed ML-KEM q=3329 N256 hmin=1 | 214 | 237 | 214 | 237 | 214 | 214 |
| Packed q=12289 N32 ×16 job | 148 | 159 | 148 | 159 | 148 | 148 |
| Scalar q=2013265921 N1024 | 987 | 987 | 987 | 987 | 987 | 438 |
| Scalar ML-DSA q=8380417 N256 | 324 | 324 | 324 | 324 | 324 | 246 |
| FFT32 N1024 | 454 | 454 | 454 | 454 | 454 | 454 |
| FFT64 N1024 | 1752 | 1752 | 1752 | 1752 | 1752 | 1752 |
| FFT128 N1024 | 6508 | 6508 | 6508 | 6508 | 6508 | 6508 |

Packed FN-DSA-size N1024: 531/391 = **1.358×**. ML-KEM-size N256: **1.107×**. Lịch cấp thưa giữ nguyên tile mạnh nhưng mất đúng lợi ích này. Vì vậy phải tối ưu cả cấp dữ liệu và số học.

Batch 16 job N32: chạy tuần tự cần 16×138 = 2208 chu kỳ kernel; batch cần 148, tương đương **14.92× throughput**. Đây là throughput khi đủ job độc lập; latency của cả batch là 148, không phải latency một job độc lập.

`cycles` chỉ đo kernel sau start; không phải tăng tốc toàn bộ keygen/sign. `all_host_cycles` trong JSON giữ số đo driver AXI mô phỏng có nạp root/dữ liệu/đọc về; không đại diện driver CPU trên board.

Mức dùng product slot hữu ích của packed16 tính từ số phép nhân và chu kỳ đo, không phải power/activity hay bộ đếm stall: mỗi butterfly cần ba nhân 16×16, mảng có 64 lá. N1024 đạt khoảng 61,4%; ML-KEM N256 khoảng 19,6%; N32 một job khoảng 2,7%, batch 16 job khoảng 40,5%. Các số này tính cả khoảng trống giữa tầng và drain của kernel. Như vậy overhead của transform nhỏ vẫn hiện rõ, dù đã có hai nhóm.

## 5. Phân rã baseline đã route

| Nhóm theo hierarchy | LUT | FF | DSP | RAMB18 |
|---|---:|---:|---:|---:|
| PS_AXI_clock_reset_shell | 436 | 542 | 0 | 0 |
| AXI_host | 367 | 744 | 0 | 0 |
| core_frontend | 227 | 815 | 0 | 0 |
| executor_direct_memory_and_route | 7,302 | 3,272 | 0 | 48 |
| tiles_after_parent_accounting | 25,945 | 28,024 | 64 | 0 |

Chi tiết các tile (cộng báo cáo module con):

| Nhóm | LUT | FF | DSP |
|---|---:|---:|---:|
| leaf_array_and_fusion | 4,425 | 4,192 | 64 |
| shared_addsub | 7,152 | 1,616 | 0 |
| FFT_control_delay | 1,264 | 48 | 0 |
| Montgomery_delay_alignment | 2,352 | 2,368 | 0 |
| tile_mixed_direct | 10,768 | 19,800 | 0 |
| tile_internal_combining_residual | -10 | 0 | 0 |
| tile_cross_hierarchy_residual | -6 | 0 | 0 |

48 RAMB18 gồm 32 data bank và 16 root bank. `tile_mixed_direct` chứa trạng thái, LUTRAM, chọn toán hạng, tích lũy FFT và reduction; không đủ căn cứ gán toàn bộ nhóm này là bộ nhân hoặc điều khiển. Các residual âm là LUT kết hợp qua biên hierarchy được Vivado ghi rõ, không phải tài nguyên âm vật lý.

Bộ cộng/trừ dùng chung chiếm một phần lớn LUT, còn lá DSP và fusion chỉ là một phần datapath. Vì vậy giảm số phép nhân không tự động giảm tổng LUT; phải tính cả lịch sử, mux, routing và metadata.

Kiểm đếm FF vật lý theo tên còn cho thấy ba pipeline `nhp0`, `nhp1`, `nlo_delay` chiếm **5.088 FF** trên 16 tile. Chúng giữ toán hạng/kết quả để thực hiện chính xác phép wrap64(v+1) rồi dịch phải của native NTRUGen IFFT. Đây là ví dụ chi phí do contract và căn chỉnh pipeline, không thể ghi chung thành chi phí bộ nhân. Danh sách họ thanh ghi lớn nằm trong JSON để truy ngược.

## 6. Kiểm chứng contract và ứng dụng

| Bản | AXI bit-exact | Four-state mới | Reset AXI mới | Vector từ C | Chữ ký kiểm độc lập |
|---|---:|---|---|---:|---:|
| reference | 1026 PASS | Kế thừa baseline giống byte | PASS | 74 | 4 |
| single_stream | 1026 PASS | FOUR_STATE TOTAL cases=12 PASS | PASS | 74 | 4 |
| separate_history | 1026 PASS | FOUR_STATE TOTAL cases=4 PASS | PASS | 74 | 4 |
| sparse_feed | 1026 PASS | FOUR_STATE TOTAL cases=4 PASS | PASS | 74 | 4 |
| split_domains | 1026 PASS | FOUR_STATE TOTAL cases=12 PASS | PASS | 74 | 4 |
| dedicated_mont32 | 1026 PASS | FOUR_STATE TOTAL cases=2 PASS | PASS | 74 | 4 |

Bộ 1.026 ca bao gồm CT/GS, FFT32/64/128, NTRUGen64, nhiều modulus scalar/packed và job bank/row. Input, expected output, root và mọi trường descriptor trừ gap được hash từng ca và khớp reference cho cả sáu bản. `dedicated_mont32` còn được planner replay lại và kiểm xung đột bank/phụ thuộc trước khi chạy RTL.

74 lời gọi FFT/IFFT/NTT/INTT lấy từ C R8 sống tại N512/N1024 được thay bằng output RTL, so 14 artifact từng byte, kiểm 4 chữ ký bằng verifier riêng và thử đầu vào sai để chặn C fallback. Các phần ngoài transform vẫn ở C. Đây không phải chứng nhận toàn bộ ML-KEM/ML-DSA hoặc chứng minh an toàn mật mã tổng quát.

Four-state tập trung phần thay đổi: single_stream và split_domains kiểm FFT ba precision hai chiều cùng scalar/packed; history và sparse kiểm packed; dedicated kiểm scalar. Reference giữ RTL giống byte baseline và chạy lại suite AXI/reset/C. Không chạy lại các test ngoài phạm vi mà không có lý do.

## 7. Những kết luận dùng được cho paper

1. Có bằng chứng định lượng cho dùng chung số học: cùng chức năng, cùng chu kỳ, tiết kiệm LUT và một nửa DSP so với đối chứng tách đường. Đối chứng vẫn chia sẻ memory/host, nên không phóng đại bằng hai hệ thống đầy đủ.
2. Có bằng chứng cho tối ưu trạng thái: cùng hai nhóm và cùng lịch, dùng chung T_hi giảm LUT/FF mà không giảm precision hay tập modulus.
3. Có bằng chứng lịch cấp dữ liệu là điều kiện để khai thác packed16: phần cứng đủ nhưng cấp thưa vẫn chậm như một nhóm. NTT nhỏ một job vẫn chịu overhead; batch làm tăng throughput khi có đủ việc độc lập.
4. Bộ nhân riêng cho reduction là một điểm đánh đổi thực: NTT32 nhanh hơn nhưng phải trả DSP, LUT và side RAM. Không suy diễn đây là thiết kế tối ưu tuyệt đối hoặc rằng mọi reduction chuyên dụng đều đắt như đối chứng này.
5. Chưa có P&R cho các bản đối chứng, đối chiếu cùng chip với RTL tác giả khác, chứng minh formal toàn thiết kế, đo board/power hay kiểm side channel. Không dùng ablation nội bộ để claim first/best toàn literature.

Một kết quả cần giữ nguyên dù không có lợi cho luận điểm dùng chung tối đa: `dedicated_mont32` chỉ tăng **823 LUT (2,41%)** nhưng tăng **112 DSP (64 → 176)**; scalar N1024 q=2013265921 nhanh **987 → 438 chu kỳ (2,253×)**. Nếu ưu tiên latency và chấp nhận 176 DSP, đây là ứng viên đáng xét tiếp. Nếu giữ mục tiêu 64 DSP, bản dùng chung phù hợp hơn. Chưa có P&R để xác nhận bản 176 DSP đạt 160 MHz hoặc vừa ngân sách toàn hệ thống.

## 8. Dấu vết và tái lập

`study/build/paper_ablation31/results.json` có số đo, chu kỳ từng ca, hash nguồn/planner và báo cáo kiểm chứng. `experiments/paper_ablation31/` chứa toàn bộ RTL và script riêng. `input_manifest.json` giữ snapshot khởi tạo; hash cuối trong results.json mới là nguồn thực đã đo. Các sửa đường dẫn planner/harness không đổi RTL và đều nằm trong bản riêng.

Hai lượt replay C đầu dùng DrvFS bị timeout do ghi trace lớn; log lỗi ban đầu được giữ. Replay hoàn tất trên Linux-local storage dùng cùng C/harness và cùng dữ liệu, sau đó chép evidence về build riêng. Timeout không được tính là PASS.

Baseline phải qua `python -X utf8 scripts/check_baseline.py` sau khi hoàn tất; không cập nhật registry, spec hay RTL chính.
