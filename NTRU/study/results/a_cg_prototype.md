# Nguyên mẫu A + CG bốn nguồn: kết quả RTL và synthesis

**Kết quả: 28.466 LUT, dưới 35.000 LUT với dư địa 6.534 LUT.**
Đo toàn top `a_cg_core`, bao gồm adapter host, root RAM, descriptor, bộ nhớ dữ liệu, mạng và 16 engine.
Không sửa RTL chính, PLAN hoặc spec; không commit. Đây là nguyên mẫu riêng, chưa phải bản thay thế tương đương mọi tính năng của core cũ.

## 1. Số đo toàn core

Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, out-of-context synthesis, flatten rebuilt. Clock báo cáo 5 ns được đặt **sau synthesis**, giống baseline.
Chưa place/route; chưa có timing vật lý hoặc Fmax đã xác nhận. I/O chưa ràng buộc input/output delay.

| Tài nguyên | Baseline lưu sẵn | A + CG đo mới |
|---|---:|---:|
| LUT tổng, gồm LUTRAM/SRL | 51,573 | 28,466 |
| FF | 29,891 | 20,415 |
| DSP48E2 | 64 | 64 |
| RAMB36E2 | 44 | 0 |
| RAMB18E2 | 64 | 48 |
| BRAM36 quy đổi | 76 | 24 |

LUT giảm **23,107 (44.8%)**. So sánh này có thay đổi cách giữ root và giao thức host, không phải phép đo tác động riêng của A hoặc CG.
WNS sau synth: **+2.090 ns** ở báo cáo 5 ns. Không dùng số này để khẳng định chạy 200 MHz sau routing.

| Phân cấp LUT | Baseline | A + CG |
|---|---:|---:|
| Tổng 16 tile/engine | 32,256 | 26,052 |
| Phần còn lại của top | 19,317 | 2,414 |

Phân cấp sau flatten/rebuild có thể phân bổ lại logic chung. Không gọi toàn bộ phần ngoài tile là điều khiển: nó gồm cả mạng, host, root và điều khiển RAM.
Phần giảm lớn nhất nằm ở tổ chức core; chưa đạt giả thuyết tile chỉ còn 1.375 LUT. Không cần đạt cả hai quota cũ mới xuống dưới 35k.

## 2. Kiến trúc đã thực sự dựng

- Giữ 16 engine cùng khả năng FFT32/64/128 và NTT32; bốn lá 16×16 mỗi engine, tổng 64 DSP. FFT rộng vẫn tính theo phần trong từng engine; không đổi tên thành PE hợp tác.
- A: 8/4/2 context BF cho FFT32/64/128, các mảng side/X/W 16 entry, tổng 3M 8 entry. Input xen kẽ re_k, im_k; giữ real/root trước đó bằng 64 FF mỗi engine để bỏ cổng đọc PRE.
- Một chương trình nhân FFT chung phát product/step; dữ liệu, carry và tích lũy ở engine. Montgomery ba lượt dùng lại chính bốn lá nhân; CT/GS giữ nguyên số học.
- CG: 32 bank ×256×32 bit, hai buffer cùng RAM. Với M≥64: bank(p)=low5(p) XOR(top_bit(p)<<4); transform nhỏ dùng active mask theo tầng.
- Mỗi input engine chọn tối đa bốn bank ứng viên; mỗi cổng ghi bank chọn tối đa bốn nhánh kết quả. Host là nguồn riêng ở chế độ idle, đã được tính trong synth; không tính nguồn host vào con số bốn của mạng compute.
- Hmin NTT được đưa thành row plane; phần thực/ảo và limb FFT cũng là row plane. Dùng chung bộ đếm k, plane, địa chỉ và stage descriptor.
- Mọi engine NTT cùng pha, nhận một BF mỗi ba nhịp khi tầng dùng đủ 16 engine; rào cuối tầng chờ kết quả ghi xong.
- Root: 16 RAM ×512×32 bit, một cổng đọc đồng bộ mỗi lane, một cổng host ghi. Stage descriptor gồm active mask16, base9, period mask5; tối đa 10 tầng.
- Host có ready và serializer 4 word/line cho load/read; mapper giữ thứ tự tự nhiên. Toàn bộ adapter và chọn bank đọc về nằm trong top.

## 3. Đổi khác và chi phí phải tính

**Root cache chỉ giữ một context cho một chiều.** Bản cũ có các bảng root NTT/FFT cố định và metadata cho 16 slot modulus. Bản mới yêu cầu host nạp bảng root và descriptor trước mỗi context mới.
16 root RAM và toàn bộ đường ghi root đã được synthesis: **48 RAMB18 = 32 data + 16 root**. Không tie-off root hoặc loại host khỏi top. Nhưng kho bảng nguồn và phần mềm sinh/đóng gói root nằm ngoài core, tương tự phần mềm host cung cấp hằng số.
Cache có thể tái dùng cho nhiều job cùng cấu hình mà không cfg lại; đổi chiều/precision/modulus cần bảng phù hợp. Chưa có cơ chế tự chuyển giữa nhiều bảng resident.
Số word root mỗi lane tại N1024: NTT 67; FFT32 70; FFT64 140; FFT128 280. Cổng host nạp một word/nhịp nên cold-load FFT128 cần **4.480 nhịp ghi root**, chưa tính 9 descriptor/config/commit.
Host nạp dữ liệu 128 bit mỗi 5 nhịp (nhận line + bốn lượt ghi), đọc cần request + bốn lượt đọc và trả lời; driver chờ response xong trước request tiếp. Đây là chi phí thật, không giả định một line/nhịp như core cũ.
Top chưa có AXI/DMA/DDR hay wrapper board. Phạm vi host ở đây là cổng giao dịch tự nhiên của core, cùng loại phạm vi tổng hợp OOC của baseline.
Bản này dùng rào giữa các tầng; chưa hoàn thiện overlap. Đặc biệt chưa giữ tốc độ NTT 984 nhịp. Không kết luận đạt giả thuyết throughput hoặc hiệu năng sinh khóa FN-DSA.

## 4. Chu kỳ RTL đã đo

Kernel không gồm nạp dữ liệu/root và đọc về. Cột toàn ca đo từ trước cfg đến sau đọc toàn output bằng driver, gồm root và host; không phải phép đo end-to-end PQC. Baseline kernel lấy từ tài liệu so sánh đã có.

| Workload xuôi N1024 | Baseline kernel | Nguyên mẫu kernel | Toàn ca cold context |
|---|---:|---:|---:|
| NTT q12289 | 984 | 1,174 | 5,332 |
| FFT32 | 644 | 597 | 4,802 |
| FFT64 | 2,031 | 1,920 | 10,317 |
| FFT128 | 7,510 | 7,113 | 23,894 |

FFT N1024 ở đây là 1.024 thành phần scalar = 512 điểm phức, đúng fixture/reference đang dùng. Không so với paper FFT 1.024 điểm phức mà không quy đổi.

## 5. Kiểm tra

- Verilator: **138/138 ca khớp từng word32**, gồm 48 ca golden NTT, 24 ca modulus survey/generic và 66 ca FFT/IFFT 32/64/128.
- NTT tổng cộng 23 cấu hình (q,N,hmin), 10 modulus: 3329, 7681, 10753, 12289, 18433, 64513, 8380417, 20972417, 25166081, 2013265921. Có q31 bit 2013265921, hmin 0/1/2 và NTT/INTT.
- Icarus bốn trạng thái: **14 ca**, gồm N1024 NTT và cả ba precision FFT xuôi/ngược, so bằng `!==` để bắt cả X/Z.
- Assertion kiểm req_ready không làm rơi request và các lane active trả kết quả cùng pha; start thiếu cấu hình phải bị từ chối.
- So với golden/reference có sẵn, giữ 3M, wrap, carry, rounding, div2e và Montgomery theo contract; không giảm độ chính xác để cắt LUT.
- Đây là bằng chứng mô phỏng các kernel và cấu hình đã kiểm, chưa phải formal proof hay chứng nhận toàn bộ FN-DSA.
- SHA256 xác nhận các source RTL chính không đổi; hash source nguyên mẫu, fixture, log, report và DCP nằm trong JSON.

Đã mở lại synthesized checkpoint: đếm đúng **32 RAMB18 dữ liệu, 16 RAMB18 root, 64 DSP và 0 black box**; các cổng host/root/config đều có kết nối tới logic trong netlist. [Audit](../build/a_cg_prototype/synth/audit.txt).

## 6. Tệp và chạy lại

- Source độc lập: [a_cg_core.sv](../../experiments/a_cg/rtl/a_cg_core.sv), [tile A sinh từ bản chụp source](../../experiments/a_cg/rtl/tile_a.sv).
- Generator và fixture: [build.py](../../experiments/a_cg/build.py).
- Chạy `powershell -NoProfile -ExecutionPolicy Bypass -File experiments/a_cg/run.ps1 -Synthesize`.
- Test Icarus: compile `tb_four_state.sv` với ba file RTL trên, chạy vvp với `+FIXTURE=study/build/a_cg_prototype/four_state.bin`.
- [Utilization](../build/a_cg_prototype/synth/util.rpt), [phân cấp](../build/a_cg_prototype/synth/util_hier.rpt), [timing](../build/a_cg_prototype/synth/timing.rpt).
- [JSON số đo, ca kiểm và hash](a_cg_prototype.json).

**Chốt phạm vi kết quả:** đã có RTL A + CG thực sự dưới 35k LUT, giữ 16 engine và multi-precision/multi-modulus; chưa có kết quả dưới 35k với đầy đủ root resident, giao thức host và throughput của baseline.
