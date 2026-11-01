# Đọc và phân tích triển khai FFT/NTT hiện có

Ngày 01/11/2026. Đọc trực tiếp C, RTL, generator, testbench và kết quả trong
workspace hiện tại. Không sửa RTL/spec trong lượt này. Đây là snapshot review,
không là nghiệm thu đầy đủ spec2.0. Source hashes và log mới nằm ở
[code_review_2026_11_01](../study/build/code_review_2026_11_01/).

## 1. Kết luận theo source hiện tại

Đã có hai thế hệ RTL thực sự khác nhau:

| Nhánh | Entry point | Tính chất |
|---|---|---|
| Baseline cũ | [flex_kernel_engine.sv](../hdl/core/flex_kernel_engine.sv) → [flex_stream_array.sv](../hdl/proto/flex_stream_array.sv) | Chín kernel; ba store; FFT rộng ghép không gian giữa tile; FFT controller tuần tự; bằng chứng application replay thuộc nhánh này |
| Nhánh mới | [ntt_core.sv](../hdl/core_ntt/ntt_core.sv) → [tile_thu.sv](../hdl/tile/tile_thu.sv) và mạng bank | Core transform mới, 16 tile; NTT32 reduction trên mảng; FFT32/64/128 butterfly trong tile, ghép limb theo thời gian |
| Bản nháp | [hdl/tile_thu/tile_thu.sv](../hdl/tile_thu/tile_thu.sv) | Interface/bối cảnh cũ; không biên dịch chung với tile nghiệm thu cùng tên module |
| Mô hình mở rộng | [ntt_prime_core.py](../model/ntt_prime_core.py), [fft_wide_tile.py](../model/fft_wide_tile.py) | Là mô hình, không tự chứng minh prime-load/FFT NTRUGen đã tích hợp vào core RTL |

Nhận định trước đây rằng core chỉ có NTT16 hai q, chưa có ML-DSA-width hoặc
FFT64/128 cần được cập nhật theo nhánh. Tile mới đã có arithmetic lane32;
core mới có profile2 q8380417 và code FFT64/128. Tuy nhiên prime-load runtime,
NTRUGen FFT semantics và signer kernels chưa được nối đầy đủ vào core mới.

**Phát hiện chức năng:** fresh regression NTT core 48/48 PASS; FFT32 N8 có
mismatch tái lập, liên quan lịch chuyển tầng cũ không theo latency tile hiện tại.
Không dùng log FFT PASS cũ để gọi source hiện tại đã nghiệm thu.

## 2. C đang thực sự yêu cầu những gì?

### 2.1 Signing R8

[sign.c](../third_party/r8/sign.c), đoạn đang thực thi quanh1475–1556:

1. FFT challenge rồi nhân với basis và scale theo inverse q.
2. IFFT hai mục tiêu, tách phần nguyên/phần lẻ theo fixed-point implementation.
3. FFT các phần lẻ, gọi `ffSampling_fft_root`.
4. Sampler đệ quy dùng SPLIT/MERGE và cập nhật bằng CMUL/cộng/trừ.
5. Nhân basis lần nữa, IFFT rồi tạo signature/check norm.

Đoạn alternative ở1434–1466 nằm trong comment, không tính là đường đang chạy.
Đây là code fixed-point R8 đã sửa so với bản reference trên website. Cần pin
đúng semantics, không lấy macro/reference floating-point khác làm oracle tùy ý.

Đếm lại từ JSON [fn_dsa_workload_mot_lan.json](../study/results/fn_dsa_workload_mot_lan.json),
chia theo4key×8signature, các lần gọi trung bình mỗi signature:

| N | FFT | IFFT | CMUL | SPLIT | MERGE |
|---:|---:|---:|---:|---:|---:|
| 512 | 3 | 4 | 133 | 254 | 254 |
| 1024 | 3 | 4 | 261 | 510 | 510 |

Đây là mẫu của build/profile đang lưu, không phải định luật cho mọi signing
implementation hoặc mọi retry. Điểm kiến trúc: transform hoàn chỉnh không là
toàn bộ FFT-domain workload. Core mới thiếu CMUL/SPLIT/MERGE nên chưa thay được
toàn bộ kernel calls của signer; không suy phần trăm thời gian từ số call.

### 2.2 Modular arithmetic Falcon

[vrfy.c](../third_party/r8/vrfy.c): `verify_raw` tại645 chuyển s2, NTT,
Montgomery pointwise với h đã chuẩn bị, iNTT, trừ challenge rồi center/check norm.
`compute_public` tại693 dùng hai forwardNTT, division theo tọa độ rồi inverse.
NTT core không tự bao gồm modular inversion, norm, hash hay codec.

### 2.3 NTRUGen có contract riêng

[ng_inner.h](../third_party/r8/ntrugen/src/ng_inner.h), `fxr_mul` tại1036 lấy
signed product >>32, không cộng rounding bias. `vect_iFFT` trong
[ng_fxp.c](../third_party/r8/ntrugen/src/ng_fxp.c) chia đôi cả sum/difference
ở mỗi tầng trước nhân, thay vì chỉ scale cuối như R8 formats0–2.

Vì vậy FFT64 Q32.32 R8-format1 **khác** FFT64 Q32.32 NTRUGen-format5. Cùng
width chưa đủ tương đương. Core mới chỉ có start_fmt2bit và reject3, chưa có
đường chọn format5/root/scale NTRUGen. Các asset/model NTRUGen đã có là nền
đối chiếu, chưa là bằng chứng RTL tích hợp.

NTRUGen prime31 có mô hình đối chiếu C trong [ntt_prime_core.py](../model/ntt_prime_core.py);
RTL core hiện vẫn reject profile3 tại `bad`. Khả năng q31 của tile khác khả
năng nạp/kiểm root, prime và chạy toàn kernel ở core.

## 3. Tile mới chia sẻ arithmetic như thế nào?

### 3.1 Cùng bốn leaf, dùng lại qua nhiều lượt

`tl_leaves` ghép bốn16×16 thành raw32×32 container65bit. FFT dùng sign theo
limb; NTT canonical dùng unsigned. Đây là phần nhân vật lý chung.

Với `TREN_MANG=1`, mỗi Mont32 dùng ba lượt trên multiplier đó:

```text
T=a*b
m=low32(T)*qprime mod2^32
mq=m*q
u=high32(T)+high32(mq)+[low32(T)!=0]
out= u>=q ? u-q : u
```

q lẻ3≤q<2^31; kết quả canonical. Hai slot q/qprime được chọn theo request và
đi cùng pipeline. Mặc định FUSE5; ba lượt cách5cycle rơi vào ba phase khác nhau
modulo3, nên một modmul mới mỗi3cycle, latency19 ở tile mặc định. Không phải
mỗi clock một modmul. `TREN_MANG=3` dùng reduction riêng làm đối chứng.

CT và GS dùng chung `tl_addsub`: GS đặt cộng/trừ trước nhân, CT đặt sau nhân;
mode/direction khóa khi tile còn việc. FFT cũng dùng khối này với q=0 để có
wrap add/sub và carry/borrow qua limb. Đây là chia sẻ hậu xử lý thật trong code.

### 3.2 FFT mode5

Mode5 nhận real limbs rồi imaginary limbs, giữ operand/root/A-side trong buffer,
tự tạo ba product và complex result. Không cần một complex-butterfly unit riêng
ở core. Một real product32/64/128 dùng1/4/15 raw32×32; một complex3M tương ứng
3/12/45 raw products. Bỏ a3*b3 ở128 là exact vì trọng số của term nằm ngoài
192 retained bits; không là giảm precision hay bỏ carry thấp.

`wacc`68bit cộng theo cột; pre-add/combine/output scale có carry/borrow theo
limb. FFT128 mới vì vậy là **temporal limb fusion trong tile**, trong khi
baseline cũ ghép product giữa nhiều tile. Các tile khác vẫn có thể chạy các
butterfly độc lập; khối2/4tile của core rộng hỗ trợ cấp limb và phân phối việc,
không ghép DSP của cả khối thành một phép nhân rộng duy nhất.

### 3.3 Protocol của tile

Tile có `en` chung và `req_valid/req_ready`; output không có rsp_ready,
`rsp_valid=rv & en`. Đây là port advance/enable đã định trong hợp đồng tile,
không là external ready/valid protocol1.0. Muốn backpressure phải dừng đúng
toàn tile và đường side-data; không ghép trực tiếp như một AXI-stream endpoint.
Core hiện hardwire `en=1`, nên tile-stall PASS không chứng minh core pause/flush.

## 4. Core mới tận dụng RAM và root

- Một storeA gồm64bank16×128row; NTT canonical lưu32bit/hệ số cho cả q nhỏ.
- Mạng chọn nguồn có cấu trúc: [ntt_bank_net_s.sv](../hdl/net/ntt_bank_net_s.sv).
- Bốn root-pack ROM bank, hai cổng đọc, mỗi bank3072×96bit trong source hiện tại.
- NTT phát tile theo phase t/6: số tile nhận mỗi clock là6/6/4. Phù hợp mỗi
  tile nhận một butterfly mỗi3cycle, giảm áp lực root/routing so với đồng pha.
- Mapping butterfly→tile và lịch theo tầng được generator ghi thành bảng.
  NTT chồng tầng khi mọi dependency/bank/tile-port condition của mô hình cho phép.
- INTT chia sum mỗi tầng và dùng inverse-root đã chứa1/2 cho nhánh product:
  kết quả normalization tương đương mà không cần pass scale cuối.
- NTT hiện dùng mode4, một butterfly/request. Không gán cho nhánh này tính năng
  paired-two-layer tile của `flex_stream_tile` cũ.

Hạn chế cấp lõi hiện tại: một đa thức/lệnh, ba profile cố định, host port giản
đơn chỉ lúc idle; chưa có native CMD/CPL hoàn chỉnh, pause/flush, nhiều store,
base addresses, prime-load, batch jobs hoặc hai polynomial context như fullspec.
Đây là phạm vi tối thiểu có chủ đích, không kết luận các extension đã tồn tại
chỉ từ tile/model support.

## 5. Lỗi đã tái lập: FFT32 chuyển tầng sớm

Source liên quan:
- [gen_ntt_core.py](../scripts/gen_ntt_core.py) dòng66–70: delta FFT32 vẫn
  hardcode `3*count+15` cùng comment theo latency cũ.
- [ntt_core.sv](../hdl/core_ntt/ntt_core.sv) dòng564: `layer_sw` theo delta,
  không kiểm commit-count theo tầng.
- [tile_thu.sv](../hdl/tile/tile_thu.sv): mode5 dùng engine product-scanning mới.

Ca nhỏ: `vectors_fft.txt`, ONLY1, format0/FFT N8. Chạy độc lập sau reset vẫn
sai8/8component, `not_ready=0`; không chỉ là đổi format giữa hai command.
[Log tái lập](../study/build/code_review_2026_11_01/fft8_reproduce.log).

Monitor chỉ quan sát, đặt ngoài RTL:

```text
cycle29: layer_sw, hlog1, delta18, lt17, wdone0
cycle35–36: result của tầng trước
cycle38–39: write của tầng trước
```

[Log monitor](../study/build/code_review_2026_11_01/fft8_monitor.log).
Tầng tiếp bắt đầu khi tầng trước chưa commit, phá dependency. Đây là cơ chế
lỗi xác nhận được, không phải sai số chấp nhận được của fixed-point.

Ưu tiên sửa sau review: lấy latency/last-commit từ đúng tile implementation
để sinh delta, hoặc barrier theo commit thực; sau đó chạy lại FFT mọi N/W/hướng
và sequence đổi cấu hình. Không chọn một số delay vá riêng cho N8. Chưa sửa RTL
hay generator trong lượt này.

## 6. Fresh verification của lượt đọc này

Icarus hiện có trên máy, compile trực tiếp source hiện tại, không dùng binary
simulation cũ và không regenerate/ghi đè generated RTL:

| Kiểm | Kết quả | Giới hạn |
|---|---|---|
| Tile mode5 wide, KIND4, stall30%/burst/seed12 | 11.520 case, err0 PASS | Một cấu hình regression chọn lọc |
| Tile NTT, MIX/stall20%/burst/sparse/seed32 | 16.110 case, err0 PASS | Không thay full tile acceptance |
| Core NTT toàn vectors.txt | 48 case thực chạy, err0 PASS | Profile0/1/2; chưa profile3 |
| Core FFT32 N8 độc lập | err8 FAIL | Tái lập và monitor như mục5 |
| Core FFT32 N1024 độc lập | err0, cycles_a572 | Không dùng pass này suy ra mọi N đúng |
| Core FFT64 N1024 inverse độc lập | err0, cycles_a2007 | Một case |
| Core FFT128 N1024 forward độc lập | err0, cycles_a7470 | Một case |

Full FFT regression đã bắt đầu và phát mismatch từ N8; dừng sau khi lỗi nhỏ đã
tái lập để review. Không tuyên bố54/54fresh PASS hoặc full FFT regression xong.
Các standalone ONLY case in `TOTAL cases=54` là **số record trong file**, không
phải54case đã execute: phải đếm dòng CASE để đánh giá phạm vi thật.

Core NTT cycles_a hiện đo: q12289 N1024 forward984/inverse985;
q3329 N256 forward231/inverse225; q8380417 N256 forward255/inverse249.
cycles_a là firstRAMread→lastRAMwrite cộng1, không gồm host load/read, không
phải latency toàn ứng dụng hay tốc độ tại MHz đã signoff.

Hai thiếu sót của test harness cần xử lý khi nghiệm thu:

1. `tb_ntt_core` kết thúc FAIL bằng `$finish`, không `$fatal`; script
   `sim/core_ntt/run.sh` có `set -e` vẫn có thể trả exit0 khi output chứa FAIL.
2. `sim/tile_thu/run.sh` function `run()` in TOTAL rồi return0;
   `must_fail()` chỉ in “KHÔNG bắt được” khi mutation lọt. Chưa là CI gate fail-closed.

Đây là vấn đề test gating độc lập với giá trị số học; lượt này đã đọc và kiểm
TOTAL/CASE thực tế, không coi exit0 tự động là PASS.

## 7. Tài liệu và bằng chứng cần đồng bộ

- Spec2.0 README vẫn ghi “Chưa có RTL”; core manifest chưa cập nhật FFT64/128.
- `docs/architecture_v1.md` có cả đoạn thiết kế hiện tại lẫn đoạn lịch sử về
  lane16/reducer hằng; dùng source và mốc revision để xác định phần nào đang chạy.
- Các báo cáo timing/WNS có source hash/version riêng; không gán WNS cũ của
  FFT32/NTT-only cho source vừa thêm FFT rộng.
- `fn_dsa_workload_mot_lan.md` phần keygen không khớp call-count cộng lại từ JSON
  cùng tên hiện tại: N512 ng_fft+ng_ifft=1606,5call/key, p31NTT+inverse=3190;
  N1024 tương ứng5054,25 và10123,75. Phải sinh lại report từ cùng snapshot trước
  khi dùng số liệu keygen trong paper. Bảng signing ở mục2 lấy trực tiếp JSON.
- 5992kernel/4signature của baseline cũ vẫn là bằng chứng của nhánh đó; chưa
  xác nhận cùng application replay cho `hdl/core_ntt/ntt_core.sv` mới.

## 8. Ý nghĩa đối với hướng nghiên cứu

Source mới đã làm được phần khó về chia sẻ arithmetic: cùng leaf phục vụ
fixed-point rộng lẫn modular32, reduction tái dùng multiplier, cộng/trừ cũng
chia sẻ giữa CT/GS/FFT. Banking/root được thiết kế theo tốc độ issue thực tế.

Cái giá hiện tại: q nhỏ cũng dùng lane32 và three-pass reduction nên mất mức
song song chuyên dụng16bit; FFT rộng cần nhiều lượt/operand buffers; lịch core
phải theo mọi thay đổi latency. Lỗi FFT32 vừa bắt là một ví dụ cụ thể của chi
phí tích hợp này. Lựa chọn temporal fusion khác mục tiêu spatial PE-fusion
ban đầu, cần mô tả đúng trong paper và baseline comparison.

Thứ tự ưu tiên từ bằng chứng hiện có: sửa integration FFT32 và làm CI fail-closed;
khóa source/model/manifest cùng snapshot; sau đó nối CMUL/SPLIT/MERGE để đánh
giá signing trên core mới. Nếu ưu tiên keygen thì nối NTRUGen-format5 và
prime-load/profile3, kiểm bằng C đã có. Các lựa chọn này cần quyết định workload
đích; không cần tự mở thêm FFT precision hay modulus để giải lỗi hiện tại.
