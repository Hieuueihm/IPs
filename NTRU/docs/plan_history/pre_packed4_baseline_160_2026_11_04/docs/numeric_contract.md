# Numeric contract và kiểm chứng trực tiếp bằng R8 C

> **Baseline hiện hành 2026-11-04:** [a_cg_z020_system160](../experiments/BASELINE.md), [contract 3.0](../spec/FlexTransform/3.0/01_so_hoc.md). Phân tích C và các số đo theo ngày bên dưới được giữ làm lịch sử; không lấy nguồn RTL hoặc số PPA cũ thay cho baseline.

> Cập nhật ứng dụng: [C tiêu thụ kernel RTL-backed và verifier độc lập chấp nhận chữ ký](pqc_application_cosim.md).

Phân tích C/model ngày 25/10/2026: Q64.64 của FFT128. Cập nhật 26/10:
[ghép nhân RTL, stall và replay R8](stream_core_results.md); FFT32/64 chưa được xác nhận bằng reference R8 precision thấp.

## 1. Reference và cấu hình

- Upstream: [fixed-point-fndsa/fixed-point-c](https://github.com/fixed-point-fndsa/fixed-point-c).
- Commit: `ad1e5bf7714d53230ad457364db8a46a1b459c94`.
- Checkout: `third_party/r8`, source không sửa; wrapper ghi vector ở [r8_capture.c](../sim/ref/r8_capture.c).
- `FALCON_FPR_MODE=2`, `FALCON_AVX2=0`; nhánh scalar, không bật `TEST_REFERENCE`.
- Build bằng GCC Linux LP64 trong WSL, `-O2 -fno-strict-aliasing`. Toàn bộ lệnh compiler,
  hash source C/H và hash vector nằm trong [manifest](../study/vectors/r8/manifest.json).
- Tắt nguồn RNG hệ điều hành bằng `FALCON_RAND_WIN32=0`; workload dùng seed SHAKE cố định.
  Việc này không đổi các phép toán số học hoặc điều kiện chấp nhận khóa/chữ ký.

R8 dùng `__builtin_clzl` trong phép chia với toán hạng 64 bit. GCC MinGW trên Windows
có `long` 32 bit, nên không dùng build đó để tuyên bố đúng luồng ký. Driver yêu cầu LP64;
không vá reference hoặc đổi builtin bằng macro để vượt qua kiểm tra này.

## 2. Hợp đồng số học

Giá trị lưu là signed two's complement 128 bit với 64 bit phần lẻ.
Đặt wrap128(x) là residue modulo 2^128, diễn giải signed.

| Phép | Kết quả bit chính xác |
|---|---|
| Cộng/trừ | wrap128(x ± y) |
| Nhân | wrap128(floor((x*y + 2^63)/2^64)) |
| Chia 2^n | wrap128(x + floor(2^n/2)) dịch phải số học n bit |
| Chia khi n=0 | Đồng nhất |

Nhân là round-nearest, ties toward +infinity, không phải ties-to-even.
Phép cộng trước chia wrap trước khi dịch; không đổi thành dịch một tổng vô hạn bit.

Nhân phức 3M giữ đúng ranh giới của R8:

~~~text
p0 = mul(ar, br)
p1 = mul(ai, bi)
p2 = mul(wrap128(ar+ai), wrap128(br+bi))
re = wrap128(p0-p1)
im = wrap128(p2-wrap128(p0+p1))
~~~

Không thay bằng 4M, không gom các tích exact rồi chỉ rounding một lần, không thêm
guard bit để thay kết quả wrap của reference. Cờ debug không thay output.

## 3. Cây nhân đang được kiểm

Golden model [r8_golden.py](../model/r8_golden.py) tách signed operands thành limb
16 hoặc 32 bit. Limb thấp unsigned; chỉ limb cao nhất có dấu. Thứ tự leaf đan bit
chỉ số i,j; dịch theo cấp:

- Leaf32, W128: 32, 32, 64, 64.
- Leaf16, W128: 16, 16, 32, 32, 64, 64.

Output cần bit [64,192) của product sau khi cộng 2^63. Vì vậy có thể bỏ những hạng
có trọng số >=192 và wrap từng nút ở 192 bit mà giữ nguyên output 128 bit.
Model đi qua từng cấp cây, không chỉ tính tích vô hạn bit rồi cắt ở cuối.
Không bỏ carry từ vùng thấp vào các bit giữ lại.

Đây là model số học; không dimension register/carry paths/mux của RTL.
NTT vẫn phải lấy T đầy đủ: không áp dụng phép rút gọn dành cho FFT vào product NTT.

## 4. FFT/iFFT và các kernel khác

FFT dùng đúng CT, layout n/2 số phức trên n word và thứ tự root của R8.
iFFT dùng GS, twiddle liên hợp và phép chia cuối `fpr_div2e(x, logn-1)`.
`logn=0` không chia, `logn=1` chia 2^0 là đồng nhất.

Các kernel được ghi và phát lại:

- FFT và iFFT đầy đủ, không chỉ một butterfly.
- `poly_mul_fft` (CMUL pointwise).
- `poly_split_fft` và `poly_merge_fft`, gồm nhánh biên N=2.

Không kiểm iFFT(FFT(x)) == x một cách máy móc: fixed-point có rounding.
Oracle là output chính xác của từng lời gọi C R8 trên cùng input.

## 5. Twiddle ROM

Bảng `fpr_gm_tab` gồm 2048 word Q64.64 được xuất trực tiếp từ executable C.
Không dùng sin/cos, float/double hoặc thư viện toán để tạo lại constants.

Hai file ROM dành cho testbench/RTL sau này:

- [Thuận](../study/vectors/r8/twiddle_forward_q64_64.mem).
- [Nghịch](../study/vectors/r8/twiddle_inverse_q64_64.mem).

Mỗi file có 1024 dòng 384 bit; thứ tự ghép mỗi dòng:

~~~text
[383:256] real
[255:128] imag được chọn theo chiều
[127:  0] wrap128(real + imag được chọn)
~~~

Chiều thuận: imag=wi, tổng=wrap128(wr+wi).
Chiều nghịch: imag=wrap128(−wi), tổng=wrap128(wr−wi).
Chỉ số root giữ nguyên vị trí trong bảng R8, kể cả các entry không dùng.
[JSON tương ứng](../study/vectors/r8/twiddle_q64_64.json) cho phép kiểm tra từng word.

Đây là nội dung ROM, chưa phải kết luận cách ánh xạ block RAM hoặc băng thông ROM.

## 6. Cách ghi vector không thay source

Chỉ khi compile `fft.c`, năm symbol kernel được đổi tên thành `r8_original_*`.
Các wrapper giữ nguyên symbol mà phần ký gọi, sao chép input, gọi đúng kernel C
gốc một lần rồi ghi output. Không đổi đối số, kết quả, sampler hoặc luồng rejection.
Không dùng Python viết lại R8 để tạo expected outputs.

Driver kiểm commit, Git status (chuẩn hóa CRLF của checkout Windows), và SHA-256
các file source trước/sau. Mọi object/executable/log nằm ngoài checkout reference.

Vector có hai nguồn:

1. 364 lời gọi synthetic: zero, impulse, alternating integers, biên/rounding ties,
   random nhỏ, random đủ 128 bit và ±LSB; N=1..1024 cho FFT/iFFT, N=2..1024 cho ba kernel còn lại.
2. Lời gọi thực từ mở rộng khóa và `sign_tree` của R8, cho N=512 và N=1024;
   khóa/message/PRNG được tạo từ seed kiểm thử cố định. Chữ ký được verifier C R8 kiểm lại.

Ở commit này, `falcon_sign_dyn` gọi `Zf_ref(sign_dyn)` nên không dùng nó để gán
workload cho đường fixed-point đã chốt. Dùng `falcon_sign_tree` không bật TEST_REFERENCE.
Keygen mặc định dùng NTRUGen Q32.32: không có capture Q64.64 từ keygen chỉ vì đã chạy keygen.
Các vector Q64.64 thực tế được gắn origin `expand_privkey` và `sign_tree`.

## 7. Dữ liệu, kết quả và chạy lại

- [Driver](../scripts/validate_r8.py).
- [Vector và provenance](../study/vectors/r8/manifest.json).
- [Báo cáo](../study/results/r8_differential.md), [JSON](../study/results/r8_differential.json).

Kết quả đã chạy: **3 842 kernel calls**, gồm 364 synthetic, 1 542 từ mở rộng khóa,
1 936 từ luồng ký. Mỗi model leaf16/leaf32 khớp **171 464 word output Q64.64**, 0 sai khác.
R8 keygen/expand/sign_tree/verify trả 0 cho cả N512 và N1024; chữ ký tương ứng 654 và 1273 byte.

Chạy toàn bộ bằng GCC/Python Linux trong WSL, từ PowerShell:

~~~powershell
wsl --exec python3 -X utf8 /mnt/d/IPs/NTRU/scripts/validate_r8.py
~~~

Phát lại vector đã ghi bằng Python Windows, không cần compiler:

~~~powershell
python -X utf8 scripts/validate_r8.py --replay-only
~~~

JSONL được nén gzip; mỗi dòng kernel có input/output word hex128, op, logn,
transaction ID, case và origin. Testbench RTL có thể dùng lại nguyên expected words.
Manifest kiểm SHA-256 trước replay. Driver còn kiểm hai negative controls: thay 3M
bằng 4M và dùng root thuận trong iFFT; cả hai phải bị phát hiện sai output.

Kết quả đúng trên các vector này không thay proof về mọi input. Báo cáo C/model gốc
không kiểm pipeline hoặc handshake. Đợt cập nhật [stream core](stream_core_results.md)
đã kiểm RTL nhân rộng và backpressure, rồi đưa kết quả RTL vào bốn kernel FFT/iFFT
đã capture; chưa thay core transform phần cứng vào signer hoặc có kết luận bảo mật mới.
FFT32/64 và arithmetic Q32.32 trong NTRUGen chưa được xác nhận bởi R8 Q64.64.
