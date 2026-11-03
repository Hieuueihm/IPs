# AES IP Core — Simple Specification

> **Mục tiêu:** Chuyển implementation AES C++ hiện tại sang SystemVerilog RTL, giữ nguyên thuật toán và cách hoạt động. Thiết kế xử lý **mỗi lần 1 block = 16 byte (128 bit)**. Không bổ sung AXI, DMA, padding hay các tính năng nằm ngoài code C++.

## 1. Chức năng

Tương ứng với class `AES` trong code C++:

| C++                          | SystemVerilog IP                                                |
| ---------------------------- | --------------------------------------------------------------- |
| `AES(AESKeyLength, AESMode)` | Chọn độ dài khóa qua parameter `KEY_BITS`; chọn mode qua `mode` |
| `keyExpansion(key)`          | Nạp khóa bằng `key_load`, sinh các round key vào `w`            |
| `setMode(mode)`              | Cấp `mode` khi bắt đầu xử lý block                              |
| `setIV(iv)`                  | Nạp IV/counter bằng `iv_load`                                   |
| `cipher(data)`               | `start=1`, `decrypt=0`                                          |
| `decrypt(data)`              | `start=1`, `decrypt=1`                                          |

Hỗ trợ:

- AES-128: `Nk=4`, `Nr=10`
- AES-192: `Nk=6`, `Nr=12`
- AES-256: `Nk=8`, `Nr=14`
- ECB, CBC, CTR
- Encryption và Decryption

`KEY_BITS` là parameter cố định khi tạo instance, giống việc chọn `key_length` trong constructor C++. Muốn đổi độ dài khóa thì dùng instance/cấu hình phần cứng khác; không thay đổi giữa chừng khi đang chạy.

## 2. Giao diện đề xuất

```systemverilog
module aes_core #(
    parameter int KEY_BITS = 128
) (
    input  logic                  clk,
    input  logic                  rst_n,

    input  logic                  key_load,
    input  logic [KEY_BITS-1:0]   key_in,
    output logic                  key_ready,

    input  logic                  iv_load,
    input  logic [127:0]          iv_in,

    input  logic [1:0]            mode,
    input  logic                  decrypt,
    input  logic                  start,
    input  logic [127:0]          data_in,

    output logic [127:0]          data_out,
    output logic                  busy,
    output logic                  done
);
```

Quy ước:

- `mode = 2'b00`: ECB; `2'b01`: CBC; `2'b10`: CTR. `2'b11`: không hỗ trợ.
- `decrypt = 0`: mã hóa; `decrypt = 1`: giải mã.
- `key_load`: xung 1 chu kỳ để bắt đầu `keyExpansion`; `key_ready=1` khi đã tạo xong round keys.
- `iv_load`: xung 1 chu kỳ để nạp lại thanh ghi IV/counter từ `iv_in`.
- `start`: xung 1 chu kỳ để xử lý một block; chỉ nhận khi `busy=0` và `key_ready=1`.
- `busy=1`: đang xử lý block (hoặc đang mở rộng khóa, nếu dùng chung datapath).
- `done=1`: xung 1 chu kỳ khi `data_out` đã hợp lệ. `data_out` giữ nguyên đến kết quả tiếp theo.
- `mode`, `decrypt`, `data_in` được chốt ở thời điểm nhận `start`.
- `key_load`, `iv_load` chỉ được chấp nhận khi `busy=0`; không gửi đồng thời với `start` hoặc với nhau.
- Reset xóa cờ điều khiển và làm mất hiệu lực khóa/IV đã nạp. Cần nạp lại khóa trước khi xử lý block.

## 3. Thanh ghi và dữ liệu nội bộ

| Tên            | Ý nghĩa                                           |
| -------------- | ------------------------------------------------- |
| `state[0:15]`  | 16 byte dữ liệu hiện tại, giống `byte state[16]`  |
| `w[]`          | Các round key đã mở rộng, giống con trỏ `this->w` |
| `iv_reg[0:15]` | IV/counter hiện tại, giống `this->iv`             |
| `round`        | Round AES đang xử lý                              |
| `Nk`, `Nr`     | Xác định từ `KEY_BITS`                            |

Số byte lưu trong `w` là `16*(Nr+1)` (AES-128: 176; AES-192: 208; AES-256: 240).

**Thứ tự byte:** `state[0] = data_in[127:120]`, ..., `state[15] = data_in[7:0]`. `key_in` và `iv_in` sử dụng cùng thứ tự (byte 0 ở phía MSB). Đây là cách ánh xạ 128-bit vector sang mảng byte để các phép `shiftRows()`/`mixColumns()` giữ nguyên ý nghĩa như C++.

## 4. Các phép biến đổi AES

Triển khai giống các hàm đang có trong C++:

| C++ function         | Mô tả RTL                                                            |
| -------------------- | -------------------------------------------------------------------- |
| `xtime()`            | Nhân với `02` trong GF(2^8): dịch trái, XOR `8'h1b` nếu bit 7 bằng 1 |
| `subBytes()`         | `state[i] = SBOX[state[i]]`                                          |
| `invSubBytes()`      | `state[i] = INV_SBOX[state[i]]`                                      |
| `shiftRows()`        | Hoán vị các byte theo đúng index C++                                 |
| `invShiftRows()`     | Hoán vị ngược                                                        |
| `mixColumns()`       | Dùng `xtime()` và XOR như C++                                        |
| `invMixColumns()`    | Dùng các hệ số `0e`, `0b`, `0d`, `09` như C++                        |
| `addRoundKey(round)` | XOR 16 byte state với `w[round*16 +: 16 byte]`                       |

Có thể dùng ROM/`case` để lưu `SBOX`, `INV_SBOX` và `RCON`.

## 5. Key Expansion

Giữ đúng vòng lặp `keyExpansion()`:

1. Copy `Nk*4` byte khóa gốc vào đầu `w`.
2. Với `i` chạy từ `Nk` đến `4*(Nr+1)-1`:
   - `temp = w[i-1]` (1 word = 4 byte).
   - Nếu `i % Nk == 0`: `RotWord(temp)` → `SubWord(temp)` → XOR `RCON[i/Nk]` vào byte đầu.
   - Nếu `Nk > 6 && i % Nk == 4`: `SubWord(temp)`.
   - `w[i] = w[i-Nk] XOR temp`.
3. Báo `key_ready=1`.

Không cần tạo lại round keys cho mỗi block nếu khóa không thay đổi.

## 6. Xử lý một AES block

### 6.1. Encryption — `cipherBlock()`

```text
state = input
AddRoundKey(state, 0)
for round = 1 .. Nr-1:
    SubBytes(state)
    ShiftRows(state)
    MixColumns(state)
    AddRoundKey(state, round)
SubBytes(state)
ShiftRows(state)
AddRoundKey(state, Nr)
output = state
```

### 6.2. Decryption — `invCipherBlock()`

```text
state = input
AddRoundKey(state, Nr)
for round = Nr-1 .. 1:
    InvShiftRows(state)
    InvSubBytes(state)
    AddRoundKey(state, round)
    InvMixColumns(state)
InvShiftRows(state)
InvSubBytes(state)
AddRoundKey(state, 0)
output = state
```

## 7. Xử lý ECB, CBC, CTR

Giữ đúng logic trong hai hàm `cipher()` và `decrypt()`:

| Mode | `decrypt=0`                    | `decrypt=1`                    | Cập nhật `iv_reg`                                     |
| ---- | ------------------------------ | ------------------------------ | ----------------------------------------------------- |
| ECB  | `AES_Encrypt(data)`            | `AES_Decrypt(data)`            | Không đổi                                             |
| CBC  | `AES_Encrypt(data XOR iv_reg)` | `AES_Decrypt(data) XOR iv_reg` | Encrypt: ciphertext output; Decrypt: ciphertext input |
| CTR  | `data XOR AES_Encrypt(iv_reg)` | `data XOR AES_Encrypt(iv_reg)` | Tăng counter sau mỗi block                            |

Trong CTR, **luôn dùng `cipherBlock()`**, kể cả khi `decrypt=1`, giống code C++.

`incrementCounter()` phải giống C++: tăng từ byte `iv_reg[15]` ngược về `iv_reg[0]`, có carry, tương đương cộng 1 vào số nguyên big-endian 128 bit. Counter tăng đúng một lần sau khi hoàn thành block CTR.

CBC/CTR giữ `iv_reg` sau mỗi block. Muốn xử lý một thông điệp mới, cần `iv_load` lại IV/counter ban đầu, giống gọi `setIV()` trong C++.
