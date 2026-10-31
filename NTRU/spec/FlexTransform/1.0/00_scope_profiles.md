# 00 — Scope, profiles, cấu hình và ownership

## 00.1 Phạm vi chức năng

| Opcode | Kernel | Input | Output | Hướng/normalization |
|---:|---|---|---|---|
| 0x0 | FFT | A: N component | A: N component | CT theo chỉ số R8 |
| 0x1 | IFFT | A: N component | A: N component | GS, cuối cùng chia 2^(logN−1) |
| 0x2 | CMUL | A,B: N component/store | A: N component | Pointwise complex 3M |
| 0x3 | SPLIT | A: N component | C: f0 rồi f1, mỗi mảng N/2 | Đúng split R8 |
| 0x4 | MERGE | A=f0, B=f1, mỗi mảng N/2 | C: N component | Đúng merge R8 |
| 0x5 | NTT | A: N residue/job | A: N residue/job | CT, không normalization |
| 0x6 | INTT | A: N residue/job | A: N residue/job | GS, scale inverse theo số tầng |
| 0x7 | TOMONT | A: N residue/job | A: N residue/job | x → xR mod q |
| 0x8 | MODMUL | A,B: N residue/job/store | A: N residue/job | abR^−1 mod q |

0x9..0xf reserved. Không có RECIP, division tổng quát, BFP/block exponent,
floating point IEEE, arbitrary modulus, RNS, BASEMUL hoặc full keygen/signer.

## 00.2 Format encoding

| fmt[1:0] | Ý nghĩa | Bit/component | F | Opcode được phép |
|---:|---|---:|---:|---|
| 0 | Q16.16 | 32 signed | 16 | 0..4 |
| 1 | Q32.32 | 64 signed | 32 | 0..4 |
| 2 | Q64.64 | 128 signed | 64 | 0..4 |
| 3 | RES16 | 16 unsigned canonical | — | 5..8 |

FFT128/Q64.64 MUST bit-exact với reference R8 đã pin. W32/64 chỉ có contract
số nguyên riêng; không được quảng bá là precision ký FN-DSA đã được chứng minh.
Không tự hạ fmt cho một command để tăng lane. (FT-SCP-001..004)

## 00.3 N và modulus

`N=2^logn`. FFT/IFFT: logn=0..10; CMUL/SPLIT/MERGE: logn=1..10.
FFT family yêu cầu profile=0; profile khác là BAD_PROFILE.

| Profile | q | logn | Tầng NTT | Normalization INTT |
|---:|---:|---|---|---|
| 0 | 12289 | 3..10 | logn | inverse(2^logn) mod q |
| 1 | 3329 | 3..7 | logn | inverse(2^logn) mod q |
| 1 | 3329 | 8 | 7, dừng ở stride=2 | inverse(128) mod q |

TOMONT/MODMUL dùng cùng miền N/profile. Profile 2/3 reserved.
q không phải input số học runtime: profile chọn bảng constant/reducer đã định.
q3329 và q12289 cùng dùng lane 16 bit; không có cam kết tăng số lane khi q nhỏ.
N nhỏ là transform contract/test configuration; không định nghĩa tham số ML-KEM mới.

## 00.4 Batch và job

`jobs=cmd_jobs_m1+1`, tối đa 8. FFT family MUST jobs=1. NTT family:

- N=8: jobs=1..8.
- N=16: jobs=1..4.
- N=32: jobs=1..2.
- N>=64: jobs=1.

Một batch chung op, fmt, profile, logn và root schedule. Job j được nhận dạng
bởi `(cmd_tag,j)` và dữ liệu là một đa thức độc lập. Completion chung cho batch;
thành công chỉ khi tất cả job hoàn thành. Không sửa jobs hoặc ghép batch có
cấu hình khác trong lúc command đang chạy. (FT-SCP-005..008)

## 00.5 REF16 parameter set

| Parameter | REF16 |
|---|---:|
| TILE_COUNT | 16 |
| LEAF_WIDTH / LEAVES_PER_TILE | 16 / 4 |
| REAL_COMPONENT_MAX_BITS | 128 |
| CONTEXT_COUNT | 2 |
| BANKS_PER_STORE / BANK_WIDTH / ROWS | 64 / 16 / 128 |
| STORE_COUNT | 3: A=0, B=1, C=2 |
| HOST_LINE_BITS / HOST_BYTE_ENABLE_BITS | 128 / 16 |
| FFT_ROOT_READ_PORTS | 1 complex root/cycle |
| NTT_BUNDLE_BANKS / BUNDLE_BITS / ROWS | 16 / 48 / 32 mỗi profile/hướng |
| EPOCH_BITS / CONTEXT_ID_BITS / JOB_INDEX_BITS | 4 / 1 / 3 |
| TAG_BITS / STAGE_ID_BITS / LANE_MASK_BITS | 32 / 4 / 16 |
| MAX_ACTIVE_CYCLES | 1,048,576 cho một valid command |

Dung lượng working data 48 KiB. NTT q3329 bundle chỉ dùng những row có dữ liệu
hợp lệ; padded row không được request và không tham gia số học. Không được suy ra kích thước vật lý BRAM
từ dung lượng logic này. Cây fusion, buffer và root ROM không nằm trong 48 KiB.

## 00.6 Ownership và tính xác định

Host nạp mọi input cần dùng trước CMD. Trong RUN, host-memory request không
được nhận. DONE cho phép host đọc; write trong DONE được nhận để trả STATE_ERR,
không sửa RAM. Sau completion ACK và sau khi host response cũ đã drain, IDLE
cho phép nạp command mới. Core không đọc coefficient chưa được host khởi tạo.

Với cùng command, trạng thái điều khiển khởi đầu, địa chỉ/footprint và
flow-control trace, lịch điều khiển MUST độc lập giá trị coefficient; không skip zero, shortcut theo dấu hoặc đổi
precision theo dữ liệu. Đây là yêu cầu hành vi, chưa phải chứng minh side-channel.
Nội dung RAM không reset/zeroize tự động. Unwritten bytes không có giá trị quy
định; phần mềm/testbench chỉ so các bytes output hợp lệ. (FT-SCP-009..011)
