# Kiểm chứng ứng dụng PQC: C tiêu thụ kết quả từ RTL

Ngày 26/10/2026. Đã chạy luồng R8 với các kernel được hỗ trợ nhận kết quả dựng từ RTL,
rồi xác minh chữ ký bằng executable C độc lập không có hook. Đây là functional co-simulation,
không phải toàn bộ thuật toán ký đã được triển khai bằng RTL.

## Kết quả ứng dụng

| N | Thông điệp | Ký | Verify qua adapter | Verifier C độc lập | Sai thông điệp/chữ ký |
|---|---:|---|---|---|---|
| 512 | 0 | Thành công | Chấp nhận | Chấp nhận | Từ chối / từ chối |
| 512 | 1 | Thành công | Chấp nhận | Chấp nhận | Từ chối / từ chối |
| 1024 | 0 | Thành công | Chấp nhận | Chấp nhận | Từ chối / từ chối |
| 1024 | 1 | Thành công | Chấp nhận | Chấp nhận | Từ chối / từ chối |

- **5,472 lời gọi kernel C**, **223,232 word đầu ra** khớp reference.
- **315,753 giao dịch RTL khác nhau**, dùng chung cùng `flex_stream_banked` có FIFO, stall và routing.
- Khóa bí mật/công khai, expanded key và cả bốn chữ ký **giống từng byte** so với luồng C gốc dùng cùng seed.
- NTT dùng bảng `GMb/iGMb` xuất trực tiếp từ C R8; không tự tái tạo root theo một quy ước khác.

## Chính xác phần nào chạy bằng RTL?

| Phần | RTL đang làm | Host/C đang làm |
|---|---|---|
| FFT/iFFT, CMUL, SPLIT, MERGE | Mọi tích thực Q64.64 của năm kernel này | Cộng/trừ wrap, thứ tự 3M, scaling và điều phối kernel |
| NTT/iNTT q12289 | Butterfly CT/GS qua cụm một/hai tầng, gather/scatter bank | Sinh stage/row/request và chuyển dữ liệu giữa các pass |
| Chuẩn hóa iNTT | Nhân Montgomery với R/N | Chọn hệ số chuẩn hóa |
| TOMONT, MODMUL | Montgomery multiplication trên đường NTT của cùng mảng | Gom/tách các batch hệ số |
| Phần còn lại của ứng dụng | Chưa đưa lên RTL | Sampling, chia, SHAKE, codec, NTRUGen keygen và các phép ngoài nhóm kernel đã thay |

Số giao dịch duy nhất theo phần tính:

| Loại frame | Số lượt sử dụng | Input trùng được tái dùng chính xác | Giao dịch RTL duy nhất |
|---|---:|---:|---:|
| NTT_banked_pass | 2,280 | 1,080 | 1,200 |
| NTT_scalar_montgomery | 384 | 168 | 216 |
| FFT128_real_product | 323,328 | 8,991 | 314,337 |

Tái dùng chỉ áp dụng cho các input giống hệt; không lượng tử hóa hay xấp xỉ. Các frame duy nhất
được trộn và chạy qua cùng pipeline có backpressure. Số cycle mô phỏng có bubbles/stall kiểm thử,
không dùng làm latency hoặc speedup của thuật toán ký.

## Vì sao đây là kiểm chứng ứng dụng mạnh hơn replay vector riêng?

1. Capture chạy reference để ghi input/output và các artifact gốc.
2. Host adapter phân rã kernel thành frame của mảng RTL. Đầu ra thực từ simulator được dùng để dựng lại kernel,
   bao gồm việc đưa kết quả RTL tầng NTT trước vào input tầng sau.
3. C chạy lại từ keygen với cùng seed. Tại từng lời gọi, wrapper kiểm toàn bộ input **đang chạy**; khớp mới nhận output từ RTL-backed file.
   Nhánh replay không gọi kernel C đã thay và không có fallback khi thiếu record.
4. Chính luồng C này tạo chữ ký, sau đó verifier gốc độc lập xác minh. Các artifact được so byte với baseline.

Trace được cố định để co-simulation theo hai lượt. Đây là liên kết chức năng qua file, không phải giao tiếp bus
trực tiếp hay hệ thống tăng tốc thời gian thực. Việc kiểm input sống và cấm fallback giúp tránh chỉ kiểm vector
bên ngoài trong khi signer vẫn dùng kết quả kernel C.

## Kiểm soát âm và provenance

- Thông điệp sửa một byte bị cả đường adapter và verifier độc lập từ chối.
- Chữ ký sửa một bit bị từ chối; trường hợp decoder phát hiện sai format có thể dừng trước NTT.
- Sửa một word input trong file thay thế khiến C dừng với `BRIDGE_FAIL`, không tiếp tục bằng C reference.
- Sửa một bit kết quả nhân RTL bị phát hiện ở ranh giới output kernel.

Reference pin tại `ad1e5bf7714d53230ad457364db8a46a1b459c94`; `FALCON_FPR_MODE=2`, scalar/AVX2=0, GCC Linux LP64.
Checkout reference không đổi. NTT static được nối hook bằng bản TU sinh trong build: chỉ đổi bốn tên định nghĩa,
giữ nguyên lời gọi và thân số học, rồi thêm wrapper capture/replay bên ngoài. Verifier độc lập dùng `vrfy.c` gốc.
SHA256 của source, TU sinh, vector, kết quả RTL, file thay thế và artifact nằm trong các manifest/JSON.

## Giới hạn còn lại

- Kết quả hiện xác nhận **pinned R8 Falcon, Q64.64/q12289, N512/N1024**, mỗi kích thước một khóa và hai thông điệp.
- FFT32/64 chưa được xác nhận bằng reference PQC precision thấp; q3329 chưa có kiểm chứng ứng dụng Kyber/ML-KEM.
- Chưa có full FFT butterfly/controller/RAM bằng RTL, hardware signer hoặc phép đo toàn ứng dụng trên FPGA.
- Không suy ra tuân thủ toàn bộ chuẩn FN-DSA, constant-time phần cứng hoặc khả năng chống side-channel từ thử nghiệm này.
- Kết quả đúng trên tập kiểm thử không thay thế proof cho mọi input.

## Chạy lại và dữ liệu

~~~powershell
python -X utf8 scripts/validate_pqc_application.py
python -X utf8 scripts/report_pqc_application.py
~~~

`--reuse-capture` tái dùng capture sau khi kiểm hash C/harness. Mô phỏng mặc định tối đa ba process;
`--jobs 1` chạy tuần tự. Batch cache kiểm input/output và hash RTL/testbench trước khi dùng lại.

- [Kết quả ứng dụng](../study/results/pqc_application.json).
- [Audit từng batch RTL](../study/results/pqc_application_audit.json).
- [Adapter kernel](../model/pqc_kernel_adapter.py), [driver](../scripts/validate_pqc_application.py), [C bridge](../sim/ref/r8_pqc_cosim.c).
