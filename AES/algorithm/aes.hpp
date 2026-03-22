#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdlib>

// ----------------------------------------------------------------
//  Kiểu dữ liệu cơ bản
// ----------------------------------------------------------------
using byte  = uint8_t;
using bytes = uint8_t*;

namespace AES {

// ----------------------------------------------------------------
//  Lựa chọn độ dài key
// ----------------------------------------------------------------
enum KeySize {
    AES_128 = 16,   // Nk=4,  Nr=10
    AES_192 = 24,   // Nk=6,  Nr=12
    AES_256 = 32,   // Nk=8,  Nr=14
};

// ----------------------------------------------------------------
//  Các mode hoạt động
// ----------------------------------------------------------------
enum Mode {
    ECB,    // Electronic Codebook          — không IV, không an toàn nhưng đơn giản
    CBC,    // Cipher Block Chaining        — cần IV ngẫu nhiên
    CFB,    // Cipher FeedBack (s=128)      — cần IV ngẫu nhiên, không padding
    OFB,    // Output FeedBack              — cần IV duy nhất, không padding
    CTR,    // Counter                      — cần Nonce duy nhất, không padding
};

// ----------------------------------------------------------------
//  Kết quả trả về
// ----------------------------------------------------------------
struct Result {
    bytes  data;    // caller phải gọi freeResult() sau khi dùng xong
    size_t len;
    bool   ok;
    const char* err;

    Result() : data(nullptr), len(0), ok(false), err(nullptr) {}
};

void freeResult(Result& r);

// ----------------------------------------------------------------
//  Lớp AES chính
// ----------------------------------------------------------------
class AES {
public:
    // key     : con trỏ đến key bytes (16, 24, hoặc 32 bytes)
    // keySize : AES_128 / AES_192 / AES_256
    AES(const byte* key, KeySize keySize);
    ~AES();

    // Đặt mode và IV/Nonce trước khi encrypt/decrypt
    // iv phải là 16 bytes với CBC, CFB, OFB
    // nonce phải là 12 bytes với CTR (4 bytes còn lại là counter, bắt đầu = 1)
    void setMode(Mode mode);
    void setIV(const byte* iv);          // CBC, CFB, OFB: 16 bytes
    void setNonce(const byte* nonce);    // CTR: 12 bytes

    // ------- ECB -------
    // Tự động pad/unpad PKCS#7
    // Người dùng truyền bất kỳ độ dài nào
    Result encryptECB(const byte* plain, size_t plainLen);
    Result decryptECB(const byte* cipher, size_t cipherLen);

    // ------- CBC -------
    // Phải gọi setIV(iv, 16) trước — IV là 16 bytes ngẫu nhiên
    // Tự động pad/unpad PKCS#7 giống ECB
    //
    // Encrypt:  C_i = AES_K( P_i XOR C_{i-1} ),  C_0 = IV
    // Decrypt:  P_i = AES_K_inv( C_i ) XOR C_{i-1}
    //
    // LƯU Ý: mỗi lần gọi encrypt/decryptCBC đều dùng IV đã set.
    // Nếu mã hóa nhiều message khác nhau, phải setIV() lại với IV mới.
    Result encryptCBC(const byte* plain, size_t plainLen);
    Result decryptCBC(const byte* cipher, size_t cipherLen);

    // ------- (CFB / OFB / CTR sẽ thêm sau) -------

private:
    // --- Tham số AES ---
    int Nk;     // số 32-bit words trong key  (4 / 6 / 8)
    int Nr;     // số vòng                     (10 / 12 / 14)

    // --- Key schedule ---
    byte* w;    // expanded key: 16 * (Nr+1) bytes
    void  keyExpansion(const byte* key);

    // --- IV (CBC, CFB, OFB dùng chung) ---
    byte iv_[16];           // IV được copy vào đây khi setIV() được gọi
    bool ivSet_ = false;    // guard: báo lỗi nếu quên setIV()

    // --- Primitive (1 block = 16 bytes) ---
    void encryptBlock(const byte* in, byte* out) const;
    void decryptBlock(const byte* in, byte* out) const;

    // --- Các bước trong 1 vòng AES ---
    void addRoundKey  (byte* state, int round) const;
    void subBytes     (byte* state) const;
    void shiftRows    (byte* state) const;
    void mixColumns   (byte* state) const;
    void invSubBytes  (byte* state) const;
    void invShiftRows (byte* state) const;
    void invMixColumns(byte* state) const;

    // --- Padding ---
    static bytes   pkcs7Pad  (const byte* in, size_t inLen, size_t& outLen);
    static size_t  pkcs7Unpad(const byte* in, size_t inLen);

    // --- Tiện ích ---
    static byte xtime(byte x);
    static byte gmul (byte a, byte b);
};

} // namespace AES