#include "aes.hpp"
#include "aes_tables.hpp"
#include <cassert>
#include <cstdio>

namespace AES {

// ================================================================
//  Tiện ích
// ================================================================

void freeResult(Result& r) {
    free(r.data);
    r.data = nullptr;
    r.len  = 0;
}

// Nhân đôi trong GF(2^8): dịch trái 1 bit, XOR 0x1b nếu bit cao = 1
byte AES::xtime(byte x) {
    return (x << 1) ^ ((x & 0x80) ? 0x1b : 0x00);
}

// Nhân hai số trong GF(2^8) bằng phép nhân từng bit (Russian peasant)
byte AES::gmul(byte a, byte b) {
    byte p = 0;
    for (int i = 0; i < 8; i++) {
        if (b & 1) p ^= a;
        bool hi = (a & 0x80);
        a <<= 1;
        if (hi) a ^= 0x1b;
        b >>= 1;
    }
    return p;
}

// ================================================================
//  Constructor / Destructor
// ================================================================

AES::AES(const byte* key, KeySize keySize) {
    switch (keySize) {
        case AES_128: Nk = 4;  Nr = 10; break;
        case AES_192: Nk = 6;  Nr = 12; break;
        case AES_256: Nk = 8;  Nr = 14; break;
    }
    // Expanded key: 16 bytes * (Nr + 1) vòng
    w = (byte*)malloc(16 * (Nr + 1));
    keyExpansion(key);
}

AES::~AES() {
    // Xóa key khỏi RAM trước khi free — tránh key còn sót trong heap
    memset(w, 0, 16 * (Nr + 1));
    free(w);
}

void AES::setMode(Mode /*mode*/) {}   // sẽ dùng khi thêm CFB/OFB/CTR
void AES::setNonce(const byte* /*nonce*/) {}

void AES::setIV(const byte* iv) {
    memcpy(iv_, iv, 16);
    ivSet_ = true;
}

// ================================================================
//  Key Expansion — FIPS 197 Section 5.2
// ================================================================
//
//  w[] là mảng các 32-bit word, được lưu thẳng thành bytes:
//  w[0..3]   = word 0   (bytes 0,1,2,3 của expanded key)
//  w[4..7]   = word 1
//  ...
//  Mỗi round key gồm 4 words liên tiếp = 16 bytes.
//
//  Công thức:
//    word[i] = word[i-Nk] XOR temp       (i % Nk == 0: temp = SubWord(RotWord(w[i-1])) XOR Rcon)
//                                         (i % Nk == 4 && Nk>6: temp = SubWord(w[i-1]))
//                                         (else: temp = w[i-1])
// ================================================================

void AES::keyExpansion(const byte* key) {
    // Nk words đầu = key gốc
    memcpy(w, key, 4 * Nk);

    for (int i = Nk; i < 4 * (Nr + 1); i++) {
        // temp = word trước đó (4 bytes)
        byte temp[4];
        memcpy(temp, w + (i - 1) * 4, 4);

        if (i % Nk == 0) {
            // RotWord: xoay trái 1 byte  [a0,a1,a2,a3] → [a1,a2,a3,a0]
            byte t = temp[0];
            temp[0] = temp[1]; temp[1] = temp[2];
            temp[2] = temp[3]; temp[3] = t;

            // SubWord: thay từng byte qua S-Box
            for (int j = 0; j < 4; j++)
                temp[j] = SBOX[temp[j]];

            // XOR với Rcon — chỉ byte đầu, 3 byte còn lại = 0
            temp[0] ^= RCON[i / Nk];

        } else if (Nk > 6 && i % Nk == 4) {
            // AES-256 thêm bước SubWord ở vị trí i%8==4
            for (int j = 0; j < 4; j++)
                temp[j] = SBOX[temp[j]];
        }

        // word[i] = word[i-Nk] XOR temp
        const byte* prev = w + (i - Nk) * 4;
        byte*       cur  = w + i * 4;
        for (int j = 0; j < 4; j++)
            cur[j] = prev[j] ^ temp[j];
    }
}

// ================================================================
//  AddRoundKey
// ================================================================
//  XOR state (16 bytes) với round key của vòng `round`
//  Round key vòng r nằm tại w[r*16 .. r*16+15]

void AES::addRoundKey(byte* state, int round) const {
    const byte* rk = w + round * 16;
    for (int i = 0; i < 16; i++)
        state[i] ^= rk[i];
}

// ================================================================
//  SubBytes / InvSubBytes
// ================================================================
//  Thay từng byte qua S-Box hoặc Inverse S-Box

void AES::subBytes(byte* state) const {
    for (int i = 0; i < 16; i++)
        state[i] = SBOX[state[i]];
}

void AES::invSubBytes(byte* state) const {
    for (int i = 0; i < 16; i++)
        state[i] = INV_SBOX[state[i]];
}

// ================================================================
//  ShiftRows / InvShiftRows
// ================================================================
//
//  State được lưu theo COLUMN-MAJOR trong mảng 16 bytes:
//
//    byte index:  0  4  8  12
//                 1  5  9  13
//                 2  6  10 14
//                 3  7  11 15
//
//  ShiftRows: row 0 giữ nguyên, row 1 dịch trái 1, row 2 dịch trái 2,
//             row 3 dịch trái 3.
//
//  InvShiftRows: ngược lại — dịch phải.

void AES::shiftRows(byte* s) const {
    byte t;
    // Row 1: dịch trái 1   [s[1], s[5], s[9], s[13]]
    t=s[1]; s[1]=s[5]; s[5]=s[9]; s[9]=s[13]; s[13]=t;

    // Row 2: dịch trái 2   swap đôi
    t=s[2]; s[2]=s[10]; s[10]=t;
    t=s[6]; s[6]=s[14]; s[14]=t;

    // Row 3: dịch trái 3 = dịch phải 1
    t=s[15]; s[15]=s[11]; s[11]=s[7]; s[7]=s[3]; s[3]=t;
}

void AES::invShiftRows(byte* s) const {
    byte t;
    // Row 1: dịch phải 1
    t=s[13]; s[13]=s[9]; s[9]=s[5]; s[5]=s[1]; s[1]=t;

    // Row 2: dịch phải 2 = swap đôi (giống forward)
    t=s[2]; s[2]=s[10]; s[10]=t;
    t=s[6]; s[6]=s[14]; s[14]=t;

    // Row 3: dịch phải 3 = dịch trái 1
    t=s[3]; s[3]=s[7]; s[7]=s[11]; s[11]=s[15]; s[15]=t;
}

// ================================================================
//  MixColumns / InvMixColumns
// ================================================================
//
//  Mỗi cột (4 bytes) được nhân với ma trận cố định trong GF(2^8).
//
//  Forward matrix:            Inverse matrix:
//  [ 2 3 1 1 ]                [ 14 11 13  9 ]
//  [ 1 2 3 1 ]                [  9 14 11 13 ]
//  [ 1 1 2 3 ]                [ 13  9 14 11 ]
//  [ 3 1 1 2 ]                [ 11 13  9 14 ]
//
//  State lưu column-major: cột i = bytes [i*4, i*4+1, i*4+2, i*4+3]

void AES::mixColumns(byte* s) const {
    for (int c = 0; c < 4; c++) {
        byte* col = s + c * 4;
        byte a = col[0], b = col[1], cc = col[2], d = col[3];

        // Nhân với ma trận [2,3,1,1 / 1,2,3,1 / 1,1,2,3 / 3,1,1,2]
        // 2*x = xtime(x),  3*x = xtime(x) ^ x
        col[0] = xtime(a) ^ (xtime(b)^b) ^ cc        ^ d;
        col[1] = a        ^ xtime(b)      ^ (xtime(cc)^cc) ^ d;
        col[2] = a        ^ b             ^ xtime(cc) ^ (xtime(d)^d);
        col[3] = (xtime(a)^a) ^ b        ^ cc         ^ xtime(d);
    }
}

void AES::invMixColumns(byte* s) const {
    for (int c = 0; c < 4; c++) {
        byte* col = s + c * 4;
        byte a = col[0], b = col[1], cc = col[2], d = col[3];

        // Nhân với ma trận inverse bằng gmul
        col[0] = gmul(0x0e,a) ^ gmul(0x0b,b) ^ gmul(0x0d,cc) ^ gmul(0x09,d);
        col[1] = gmul(0x09,a) ^ gmul(0x0e,b) ^ gmul(0x0b,cc) ^ gmul(0x0d,d);
        col[2] = gmul(0x0d,a) ^ gmul(0x09,b) ^ gmul(0x0e,cc) ^ gmul(0x0b,d);
        col[3] = gmul(0x0b,a) ^ gmul(0x0d,b) ^ gmul(0x09,cc) ^ gmul(0x0e,d);
    }
}

// ================================================================
//  encryptBlock — mã hóa đúng 1 block 16 bytes
// ================================================================
//
//  FIPS 197 Section 5.1:
//    AddRoundKey(round 0)
//    for round = 1 to Nr-1:
//        SubBytes → ShiftRows → MixColumns → AddRoundKey
//    SubBytes → ShiftRows → AddRoundKey(round Nr)   ← KHÔNG MixColumns

void AES::encryptBlock(const byte* in, byte* out) const {
    byte state[16];
    memcpy(state, in, 16);

    // Vòng 0: chỉ AddRoundKey
    addRoundKey(state, 0);

    // Vòng 1 .. Nr-1
    for (int r = 1; r < Nr; r++) {
        subBytes(state);
        shiftRows(state);
        mixColumns(state);
        addRoundKey(state, r);
    }

    // Vòng cuối: không có MixColumns
    subBytes(state);
    shiftRows(state);
    addRoundKey(state, Nr);

    memcpy(out, state, 16);
}

// ================================================================
//  decryptBlock — giải mã đúng 1 block 16 bytes
// ================================================================
//
//  FIPS 197 Section 5.3 (Equivalent Inverse Cipher không dùng ở đây,
//  dùng chuẩn Inverse Cipher cho dễ hiểu):
//    AddRoundKey(round Nr)
//    for round = Nr-1 to 1:
//        InvShiftRows → InvSubBytes → AddRoundKey → InvMixColumns
//    InvShiftRows → InvSubBytes → AddRoundKey(round 0)

void AES::decryptBlock(const byte* in, byte* out) const {
    byte state[16];
    memcpy(state, in, 16);

    // Vòng cuối đầu tiên
    addRoundKey(state, Nr);

    // Vòng Nr-1 .. 1
    for (int r = Nr - 1; r >= 1; r--) {
        invShiftRows(state);
        invSubBytes(state);
        addRoundKey(state, r);
        invMixColumns(state);
    }

    // Vòng 0
    invShiftRows(state);
    invSubBytes(state);
    addRoundKey(state, 0);

    memcpy(out, state, 16);
}

// ================================================================
//  PKCS#7 Padding
// ================================================================
//
//  Quy tắc:
//  - Nếu data là n bytes, pad thêm (16 - n%16) bytes
//  - Mỗi byte padding có giá trị = số bytes được pad
//  - Nếu n đã là bội số 16: vẫn pad thêm 1 block (16 bytes giá trị 0x10)
//    → decrypt luôn phân biệt được data thật với padding
//
//  Ví dụ:
//    Input 11 bytes → pad 5 bytes → mỗi byte = 0x05
//    Input 16 bytes → pad 16 bytes → mỗi byte = 0x10

bytes AES::pkcs7Pad(const byte* in, size_t inLen, size_t& outLen) {
    byte padByte = (byte)(16 - (inLen % 16)); // luôn từ 1 đến 16
    outLen = inLen + padByte;

    byte* out = (byte*)malloc(outLen);
    memcpy(out, in, inLen);
    memset(out + inLen, padByte, padByte);
    return out;
}

// Trả về độ dài sau khi bỏ padding.
// Trả về inLen (không đổi) nếu padding không hợp lệ.
size_t AES::pkcs7Unpad(const byte* in, size_t inLen) {
    if (inLen == 0 || inLen % 16 != 0) return inLen;

    byte padByte = in[inLen - 1];
    if (padByte == 0 || padByte > 16) return inLen; // giá trị không hợp lệ

    // Kiểm tra tất cả các byte padding đều giống nhau
    for (size_t i = inLen - padByte; i < inLen; i++) {
        if (in[i] != padByte) return inLen; // padding bị lỗi
    }

    return inLen - padByte;
}

// ================================================================
//  ECB Encrypt
// ================================================================
//
//  Luồng:
//    1. pkcs7Pad(plain)         → padded  (bội số 16 bytes)
//    2. encryptBlock() từng block
//    3. Trả về ciphertext
//
//  Người dùng truyền bất kỳ độ dài nào — thư viện tự lo padding.

Result AES::encryptECB(const byte* plain, size_t plainLen) {
    Result res;

    size_t paddedLen;
    byte* padded = pkcs7Pad(plain, plainLen, paddedLen);

    res.data = (byte*)malloc(paddedLen);
    res.len  = paddedLen;
    res.ok   = true;

    for (size_t i = 0; i < paddedLen; i += 16)
        encryptBlock(padded + i, res.data + i);

    free(padded);
    return res;
}

// ================================================================
//  ECB Decrypt
// ================================================================
//
//  Luồng:
//    1. Kiểm tra ciphertext phải là bội số 16 bytes
//    2. decryptBlock() từng block
//    3. pkcs7Unpad()            → trả về đúng plaintext gốc

Result AES::decryptECB(const byte* cipher, size_t cipherLen) {
    Result res;

    if (cipherLen == 0 || cipherLen % 16 != 0) {
        res.ok  = false;
        res.err = "Ciphertext length must be a multiple of 16";
        return res;
    }

    // Giải mã từng block
    byte* decrypted = (byte*)malloc(cipherLen);
    for (size_t i = 0; i < cipherLen; i += 16)
        decryptBlock(cipher + i, decrypted + i);

    // Bỏ padding
    size_t realLen = pkcs7Unpad(decrypted, cipherLen);
    if (realLen == cipherLen && decrypted[cipherLen-1] > 16) {
        // Padding không hợp lệ — có thể sai key hoặc data bị hỏng
        free(decrypted);
        res.ok  = false;
        res.err = "Invalid PKCS#7 padding — wrong key or corrupted data";
        return res;
    }

    res.data = (byte*)malloc(realLen);
    res.len  = realLen;
    res.ok   = true;
    memcpy(res.data, decrypted, realLen);
    free(decrypted);
    return res;
}

// ================================================================
//  CBC Encrypt
// ================================================================
//
//  Công thức:   C_i = AES_K( P_i XOR C_{i-1} ),   C_0 = IV
//
//  Mỗi plaintext block được XOR với ciphertext block trước đó
//  trước khi đưa vào AES — tạo ra sự phụ thuộc giữa các block.
//
//  Đặc điểm quan trọng:
//    - Encrypt PHẢI tuần tự (C_{i-1} phải có trước khi tính C_i)
//    - Decrypt CÓ THỂ song song (mỗi C_i decrypt độc lập, rồi XOR C_{i-1})
//    - Cùng plaintext + IV khác nhau → ciphertext hoàn toàn khác
//    - IV không cần bí mật nhưng PHẢI ngẫu nhiên và không tái sử dụng
//      với cùng key (nếu tái dùng → block đầu bị lộ pattern)

Result AES::encryptCBC(const byte* plain, size_t plainLen) {
    Result res;
    if (!ivSet_) {
        res.ok  = false;
        res.err = "IV chưa được set — gọi setIV() trước khi encrypt";
        return res;
    }

    // Pad plaintext lên bội số 16 bytes (PKCS#7)
    size_t paddedLen;
    byte* padded = pkcs7Pad(plain, plainLen, paddedLen);

    res.data = (byte*)malloc(paddedLen);
    res.len  = paddedLen;
    res.ok   = true;

    // prev = block trước đó trong ciphertext, bắt đầu là IV
    const byte* prev = iv_;

    for (size_t i = 0; i < paddedLen; i += 16) {
        // Bước 1: XOR plaintext block với prev (IV hoặc C_{i-1})
        byte xored[16];
        for (int j = 0; j < 16; j++)
            xored[j] = padded[i + j] ^ prev[j];

        // Bước 2: mã hóa AES
        encryptBlock(xored, res.data + i);

        // Bước 3: C_i trở thành prev cho block tiếp theo
        prev = res.data + i;
    }

    free(padded);
    return res;
}

// ================================================================
//  CBC Decrypt
// ================================================================
//
//  Công thức:   P_i = AES_K_inv( C_i ) XOR C_{i-1},   C_0 = IV
//
//  Ngược lại với encrypt: giải mã AES trước, rồi XOR với block trước.
//  CÓ THỂ song song vì mỗi C_i giải mã độc lập — chỉ cần C_{i-1} để XOR.
//
//  Lưu ý quan trọng khi decrypt:
//    - Phải lưu C_{i-1} TRƯỚC KHI ghi đè vùng nhớ (nếu decrypt in-place)
//    - Code dưới dùng buffer riêng nên không có vấn đề này

Result AES::decryptCBC(const byte* cipher, size_t cipherLen) {
    Result res;
    if (!ivSet_) {
        res.ok  = false;
        res.err = "IV chưa được set — gọi setIV() trước khi decrypt";
        return res;
    }
    if (cipherLen == 0 || cipherLen % 16 != 0) {
        res.ok  = false;
        res.err = "Ciphertext CBC phải là bội số 16 bytes";
        return res;
    }

    byte* decrypted = (byte*)malloc(cipherLen);

    for (size_t i = 0; i < cipherLen; i += 16) {
        // Bước 1: giải mã AES block ciphertext
        byte aesOut[16];
        decryptBlock(cipher + i, aesOut);

        // Bước 2: XOR với C_{i-1} (IV nếu là block đầu)
        const byte* prev = (i == 0) ? iv_ : cipher + i - 16;
        for (int j = 0; j < 16; j++)
            decrypted[i + j] = aesOut[j] ^ prev[j];
    }

    // Bỏ padding PKCS#7
    size_t realLen = pkcs7Unpad(decrypted, cipherLen);
    if (realLen == cipherLen && decrypted[cipherLen - 1] > 16) {
        free(decrypted);
        res.ok  = false;
        res.err = "Padding không hợp lệ — sai key, sai IV, hoặc data bị hỏng";
        return res;
    }

    res.data = (byte*)malloc(realLen);
    res.len  = realLen;
    res.ok   = true;
    memcpy(res.data, decrypted, realLen);
    free(decrypted);
    return res;
}

} // namespace AES