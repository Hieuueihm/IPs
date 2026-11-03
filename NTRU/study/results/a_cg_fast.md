# A + CG bản nhanh: số đo RTL và correctness ứng dụng

**Đạt 34,062 LUT, dưới 35.000 LUT, còn dư 938 LUT.**
Ngày 02/11/2026. Bản riêng tại `experiments/a_cg_fast`. Không đổi production HDL, PLAN, spec hoặc nguyên mẫu 28.466 LUT; chưa commit.

## 1. Tài nguyên toàn top

Vivado2018.1, xczu7ev-ffvc1156-2-e, out-of-context synth, flatten rebuilt. Clock báo cáo 5 ns đặt sau synth giống các baseline. Chưa place/route hoặc đo Fmax.

| Tài nguyên | A + CG cũ | Bản nhanh + native NTRUGen |
|---|---:|---:|
| LUT tổng | 28,466 | 34,062 |
| FF | 20,415 | 24,950 |
| DSP48 | 64 | 64 |
| RAMB18 | 48 | 48 |
| RAMB36 | 0 | 0 |

WNS sau synth **+1.127 ns** ở clock báo cáo 5 ns; I/O chưa có input/output delay. Đây không phải cam kết chạy 200 MHz sau routing.
Đã mở checkpoint và đếm **32 RAMB18 data, 16 RAMB18 root, 64 DSP, 0 black box**. Cổng host/root/config còn nối vào logic. Dư địa LUT nhỏ, thêm AXI/DMA hoặc tính năng khác phải đo lại.

Lần đầu thêm đủ tính năng ra 38.700 LUT. Đã giảm bằng tăng A một lần cho cả hai nhánh GS, tái dùng operand register để giữ limb thấp, và chuyển engine nội bộ sang nhận lịch từ core. Không cắt độ chính xác, số engine hoặc khả năng precision.
Mode/q chỉ đổi tại CONFIG_TILE sau reset; bộ đếm idle/admission tổng quát riêng từng engine được bỏ khỏi hardware. Assertion vẫn kiểm buffer sống ≤8/4/2, request không rơi, phase output, host bank conflict và same-edge RAW.

## 2. Chu kỳ đã đo trên RTL

Tăng tốc ở cùng clock. Kernel không gồm host/root. Toàn ca gồm config, descriptor, cold root load, input và readback; driver đọc burst. Các số không phải speedup toàn thuật toán PQC.

| Kernel | A + CG cũ | Bản nhanh | Speedup |
|---|---:|---:|---:|
| NTT q12289 N1024 | 1,174 | 985 | 1.19× |
| NTT q3329 N256 hmin1 | 319 | 265 | 1.20× |
| NTT q8380417 N256 | 364 | 301 | 1.21× |
| FFT32 N1024 | 597 | 453 | 1.32× |
| FFT64 generic N1024 | 1,920 | 1,752 | 1.10× |
| FFT128 R8 N1024 | 7,113 | 6,937 | 1.03× |

**FFT64 native NTRUGen N1024:** forward 1,752, inverse 1,754 chu kỳ. Đây là contract riêng, không dùng FFT64 generic thay thế.
FFT N1024 là 1.024 thành phần scalar =512 điểm phức. Với N nhỏ, chọn lịch rào khi overlap không có lợi; không tự hạ precision.

| Toàn ca N1024, cold root | A + CG cũ | Bản nhanh | Speedup |
|---|---:|---:|---:|
| NTT q12289 N1024 | 5,332 | 2,536 | 2.10× |
| FFT32 N1024 | 4,802 | 2,002 | 2.40× |
| FFT64 generic N1024 | 10,317 | 4,941 | 2.09× |
| FFT128 R8 N1024 | 23,894 | 17,396 | 1.37× |

Host load phase0 tại cạnh handshake, read response pipeline qua ranh giới line. Giữ layout natural: FFT32/64/128 dùng 1/2/4 lượt bank mỗi line ở N lớn; có xử lý va chạm N rất nhỏ.
Root multicast chỉ gộp word32 có bit-pattern giống nhau, không nén mất bit. Cache vẫn một context; đổi q/chiều/precision/contract phải nạp đúng root và descriptor. Bảng gap host được sinh bằng model RAM đã kiểm, không phải microcode bất kỳ tự được phần cứng chứng minh an toàn.

## 3. Correctness đã xác nhận

- **454/454 ca Verilator khớp từng word**, bao gồm 138 ca cũ, 40 ca native FFT64 NTRUGen, 176 FFT/IFFT C R8 và 100 NTT/INTT C NTRUGen (năm prime31 bit, N2..1024, hai chiều).
- **16/16 ca Icarus bốn trạng thái** khớp bằng `!==`, gồm cả ba precision, hai chiều và native NTRUGen. Assertion buffer/phase/RAM/host đều qua.
- Số chu kỳ 454 ca khớp model schedule; model không được dùng thay output RTL.
- Root native NTRUGen lấy nguyên bit từ GM_TAB C; nhân floor, signed rounded-half trước nhân mỗi tầng inverse. Bộ 40 vector native đã qua, gồm 35 ca bị lệch trước đây; giữ generic FFT64 như một chế độ khác.
- Không sửa reference hoặc expected vector để hợp RTL; không chuyển FFT128 signing xuống precision thấp.

## 4. C thực sự tiêu thụ output từ RTL cuối

**74 lời gọi FFT/IFFT/NTT/INTT** từ workload R8 N512/N1024 được chạy qua simulator của bản cuối, ghi raw output thật. C chạy lại cùng seed, kiểm từng live input rồi lấy output đó; không fallback về C cho bốn transform đã thay.

- Bốn chữ ký được verifier C gốc độc lập chấp nhận; thông điệp sai bị từ chối. Luồng ứng dụng cũng từ chối chữ ký sửa bit.
- Khóa bí mật/công khai, expanded key, chữ ký và thông điệp giống từng byte với capture C gốc (14 artifact).
- Sửa live input trong replacement bị từ chối với BRIDGE_FAIL ở cả N512/N1024; không tiếp tục bằng C reference.
- Phần còn ở C: CMUL/SPLIT/MERGE, TOMONT/MODMUL, NTRUGen keygen, sampling, SHAKE, codec và các phép khác. Kiểm native FFT64 hiện là kernel với vector C, chưa phải keygen dùng RTL.
- Chưa chạy full ML-KEM/ML-DSA application KAT, chưa kết luận tuân thủ toàn bộ FN-DSA/constant-time/side-channel. Kết quả trên tập kiểm thử không phải formal proof mọi input.

## 5. Tệp và chạy lại

- [Source và contract](../../experiments/a_cg_fast/README.md).
- [Top RTL](../../experiments/a_cg_fast/rtl/a_cg_fast.sv), [generator tile/fixture](../../experiments/a_cg_fast/build.py).
- [Utilization](../build/a_cg_fast/synth/util.rpt), [phân cấp](../build/a_cg_fast/synth/util_hier.rpt), [timing](../build/a_cg_fast/synth/timing.rpt), [checkpoint audit](../build/a_cg_fast/synth/audit.txt).
- [Ứng dụng C và verifier](../build/a_cg_fast/application/application_results.json), [74 record output RTL](../build/a_cg_fast/application/rtl_records.json).
- [JSON ca kiểm, số đo và SHA256](a_cg_fast.json).
Chạy các lệnh trong README. Giữ source/hash/log/DCP để phân biệt kết quả đo với model và lần thử 38.700 LUT.
