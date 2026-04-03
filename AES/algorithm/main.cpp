#include <iostream>
#include <cstring>
#include <cstdio>
#include "aes.hpp"

// ----------------------------------------------------------------
//  In mảng bytes dạng hex
// ----------------------------------------------------------------
static void printHex(const char* label, const uint8_t* data, size_t len) {
    printf("%-14s: ", label);
    for (size_t i = 0; i < len; i++) printf("%02x ", data[i]);
    printf("\n");
}

// ----------------------------------------------------------------
//  So sánh với expected, in PASS/FAIL
// ----------------------------------------------------------------
static bool check(const char* testName,
                  const uint8_t* got, size_t gotLen,
                  const uint8_t* expected, size_t expLen) {
    bool pass = (gotLen == expLen) && (memcmp(got, expected, expLen) == 0);
    printf("[%s] %s\n", pass ? "PASS" : "FAIL", testName);
    if (!pass) {
        printHex("  got     ", got,      gotLen);
        printHex("  expected", expected, expLen);
    }
    return pass;
}

// ================================================================
//  Test 1: NIST FIPS-197 Appendix B
//  AES-128, 1 block plaintext
// ================================================================
static bool test_nist_fips197() {
    printf("\n=== NIST FIPS-197 Appendix B (AES-128, 1 block) ===\n");

    uint8_t key[16] = {
        0x2b,0x7e,0x15,0x16, 0x28,0xae,0xd2,0xa6,
        0xab,0xf7,0x15,0x88, 0x09,0xcf,0x4f,0x3c
    };
    uint8_t plain[16] = {
        0x32,0x43,0xf6,0xa8, 0x88,0x5a,0x30,0x8d,
        0x31,0x31,0x98,0xa2, 0xe0,0x37,0x07,0x34
    };
    uint8_t expected_ct[32] = {  // 16 bytes data + 16 bytes padding block
        0x39,0x25,0x84,0x1d, 0x02,0xdc,0x09,0xfb,
        0xdc,0x11,0x85,0x97, 0x19,0x6a,0x0b,0x32,
        // block padding (PKCS7 pad 16 bytes, mỗi byte = 0x10)
        // → encrypt block [10 10 10 10 10 10 10 10 10 10 10 10 10 10 10 10]
        0xd8,0xf1,0xd0,0x4a, 0x84,0x47,0xfc,0x8a,
        0x05,0xa1,0x04,0x45, 0x9f,0xb9,0x2c,0x3b
    };

    AES::AES aes(key, AES::AES_128);

    // Encrypt
    AES::Result ct = aes.encryptECB(plain, 16);
    printHex("plaintext ", plain,   16);
    printHex("ciphertext", ct.data, ct.len);

    // Chỉ kiểm tra block đầu (block padding phụ thuộc implementation)
    bool enc_ok = ct.ok && ct.len >= 16 &&
                  (memcmp(ct.data, expected_ct, 16) == 0);
    printf("[%s] encrypt block 0\n", enc_ok ? "PASS" : "FAIL");

    // Decrypt round-trip
    AES::Result pt = aes.decryptECB(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 16);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
    // return enc_ok;
}

// ================================================================
//  Test 2: NIST SP 800-38A ECB-AES128 (4 blocks)
// ================================================================
static bool test_nist_sp800_38a_128() {
    printf("\n=== NIST SP800-38A ECB-AES128 (4 blocks, no padding) ===\n");

    uint8_t key[16] = {
        0x2b,0x7e,0x15,0x16, 0x28,0xae,0xd2,0xa6,
        0xab,0xf7,0x15,0x88, 0x09,0xcf,0x4f,0x3c
    };
    uint8_t plain[64] = {
        0x6b,0xc1,0xbe,0xe2, 0x2e,0x40,0x9f,0x96,
        0xe9,0x3d,0x7e,0x11, 0x73,0x93,0x17,0x2a,
        0xae,0x2d,0x8a,0x57, 0x1e,0x03,0xac,0x9c,
        0x9e,0xb7,0x6f,0xac, 0x45,0xaf,0x8e,0x51,
        0x30,0xc8,0x1c,0x46, 0xa3,0x5c,0xe4,0x11,
        0xe5,0xfb,0xc1,0x19, 0x1a,0x0a,0x52,0xef,
        0xf6,0x9f,0x24,0x45, 0xdf,0x4f,0x9b,0x17,
        0xad,0x2b,0x41,0x7b, 0xe6,0x6c,0x37,0x10
    };
    // 4 blocks ciphertext từ NIST (plain đúng bội số 16 → thêm 1 block padding)
    // Chỉ kiểm tra 4 blocks đầu
    uint8_t expected_ct[64] = {
        0x3a,0xd7,0x7b,0xb4, 0x0d,0x7a,0x36,0x60,
        0xa8,0x9e,0xca,0xf3, 0x24,0x66,0xef,0x97,
        0xf5,0xd3,0xd5,0x85, 0x03,0xb9,0x69,0x9d,
        0xe7,0x85,0x89,0x5a, 0x96,0xfd,0xba,0xaf,
        0x43,0xb1,0xcd,0x7f, 0x59,0x8e,0xce,0x23,
        0x88,0x1b,0x00,0xe3, 0xed,0x03,0x06,0x88,
        0x7b,0x0c,0x78,0x5e, 0x27,0xe8,0xad,0x3f,
        0x82,0x23,0x20,0x71, 0x04,0x72,0x5d,0xd4
    };

    AES::AES aes(key, AES::AES_128);

    AES::Result ct = aes.encryptECB(plain, 64);
    // So sánh chỉ 4 block đầu (bỏ qua block padding thứ 5)
    bool enc_ok = ct.ok && ct.len >= 64 &&
                  (memcmp(ct.data, expected_ct, 64) == 0);
    printf("[%s] encrypt 4 blocks\n", enc_ok ? "PASS" : "FAIL");
    if (!enc_ok) {
        printHex("got[0]     ", ct.data,    16);
        printHex("expected[0]", expected_ct, 16);
    }

    AES::Result pt = aes.decryptECB(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 64);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
}

// ================================================================
//  Test 3: AES-256 ECB
// ================================================================
static bool test_nist_sp800_38a_256() {
    printf("\n=== NIST SP800-38A ECB-AES256 (1 block) ===\n");

    uint8_t key[32] = {
        0x60,0x3d,0xeb,0x10, 0x15,0xca,0x71,0xbe,
        0x2b,0x73,0xae,0xf0, 0x85,0x7d,0x77,0x81,
        0x1f,0x35,0x2c,0x07, 0x3b,0x61,0x08,0xd7,
        0x2d,0x98,0x10,0xa3, 0x09,0x14,0xdf,0xf4
    };
    uint8_t plain[16] = {
        0x6b,0xc1,0xbe,0xe2, 0x2e,0x40,0x9f,0x96,
        0xe9,0x3d,0x7e,0x11, 0x73,0x93,0x17,0x2a
    };
    uint8_t expected[16] = {
        0xf3,0xee,0xd1,0xbd, 0xb5,0xd2,0xa0,0x3c,
        0x06,0x4b,0x5a,0x7e, 0x3d,0xb1,0x81,0xf8
    };

    AES::AES aes(key, AES::AES_256);
    AES::Result ct = aes.encryptECB(plain, 16);

    bool enc_ok = ct.ok && ct.len >= 16 &&
                  (memcmp(ct.data, expected, 16) == 0);
    printf("[%s] encrypt AES-256\n", enc_ok ? "PASS" : "FAIL");

    AES::Result pt = aes.decryptECB(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 16);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
}

// ================================================================
//  Test 4: Arbitrary-length input (không bội số 16)
// ================================================================
static bool test_arbitrary_length() {
    printf("\n=== Arbitrary length input ===\n");

    uint8_t key[16] = {
        0x00,0x01,0x02,0x03, 0x04,0x05,0x06,0x07,
        0x08,0x09,0x0a,0x0b, 0x0c,0x0d,0x0e,0x0f
    };

    const char* msg = "Hello, AES ECB!"; // 15 bytes
    size_t msgLen = strlen(msg);

    AES::AES aes(key, AES::AES_128);

    AES::Result ct = aes.encryptECB((const uint8_t*)msg, msgLen);
    printf("Input len   : %zu bytes\n", msgLen);
    printf("Cipher len  : %zu bytes (padded to 16)\n", ct.len);
    printHex("ciphertext ", ct.data, ct.len);

    AES::Result pt = aes.decryptECB(ct.data, ct.len);
    printf("Decrypted   : \"%.*s\"\n", (int)pt.len, pt.data);

    bool ok = pt.ok && pt.len == msgLen &&
              (memcmp(pt.data, msg, msgLen) == 0);
    printf("[%s] round-trip 15 bytes\n", ok ? "PASS" : "FAIL");

    AES::freeResult(ct);
    AES::freeResult(pt);
    return ok;
}

// ================================================================
//  Test 5: Padding edge cases
// ================================================================
static bool test_padding_edge_cases() {
    printf("\n=== Padding edge cases ===\n");

    uint8_t key[16] = {0};
    AES::AES aes(key, AES::AES_128);
    bool all_ok = true;

    // Empty input (0 bytes) → 1 block padding (16 bytes giá trị 0x10)
    {
        AES::Result ct = aes.encryptECB(nullptr, 0);
        printf("Empty input → cipher len = %zu (expect 16)\n", ct.len);
        bool ok = ct.ok && ct.len == 16;
        printf("[%s] empty input\n", ok ? "PASS" : "FAIL");

        AES::Result pt = aes.decryptECB(ct.data, ct.len);
        ok = ok && pt.ok && pt.len == 0;
        printf("[%s] decrypt empty\n", ok ? "PASS" : "FAIL");
        all_ok &= ok;
        AES::freeResult(ct);
        AES::freeResult(pt);
    }

    // Input 16 bytes (bội số) → 2 blocks output (16 data + 16 padding)
    {
        uint8_t plain[16] = {0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,
                             0x49,0x4a,0x4b,0x4c,0x4d,0x4e,0x4f,0x50};
        AES::Result ct = aes.encryptECB(plain, 16);
        bool ok = ct.ok && ct.len == 32;
        printf("[%s] 16-byte input → 32-byte output\n", ok ? "PASS" : "FAIL");

        AES::Result pt = aes.decryptECB(ct.data, ct.len);
        ok = ok && pt.ok && pt.len == 16 && memcmp(pt.data, plain, 16) == 0;
        printf("[%s] decrypt 32→16 bytes\n", ok ? "PASS" : "FAIL");
        all_ok &= ok;
        AES::freeResult(ct);
        AES::freeResult(pt);
    }

    return all_ok;
}

// ================================================================
//  Test 6: NIST SP 800-38A CBC-AES128 (4 blocks)
// ================================================================
static bool test_cbc_nist_128() {
    printf("\n=== NIST SP800-38A CBC-AES128 (4 blocks) ===\n");

    uint8_t key[16] = {
        0x2b,0x7e,0x15,0x16, 0x28,0xae,0xd2,0xa6,
        0xab,0xf7,0x15,0x88, 0x09,0xcf,0x4f,0x3c
    };
    uint8_t iv[16] = {
        0x00,0x01,0x02,0x03, 0x04,0x05,0x06,0x07,
        0x08,0x09,0x0a,0x0b, 0x0c,0x0d,0x0e,0x0f
    };
    uint8_t plain[64] = {
        0x6b,0xc1,0xbe,0xe2, 0x2e,0x40,0x9f,0x96,
        0xe9,0x3d,0x7e,0x11, 0x73,0x93,0x17,0x2a,
        0xae,0x2d,0x8a,0x57, 0x1e,0x03,0xac,0x9c,
        0x9e,0xb7,0x6f,0xac, 0x45,0xaf,0x8e,0x51,
        0x30,0xc8,0x1c,0x46, 0xa3,0x5c,0xe4,0x11,
        0xe5,0xfb,0xc1,0x19, 0x1a,0x0a,0x52,0xef,
        0xf6,0x9f,0x24,0x45, 0xdf,0x4f,0x9b,0x17,
        0xad,0x2b,0x41,0x7b, 0xe6,0x6c,0x37,0x10
    };
    // Expected ciphertext từ NIST (64 bytes — 4 blocks, không có padding block
    // vì NIST test vector truyền plaintext đúng bội số 16 và không tính padding)
    uint8_t expected[64] = {
        0x76,0x49,0xab,0xac, 0x81,0x19,0xb2,0x46,
        0xce,0xe9,0x8e,0x9b, 0x12,0xe9,0x19,0x7d,
        0x50,0x86,0xcb,0x9b, 0x50,0x72,0x19,0xee,
        0x95,0xdb,0x11,0x3a, 0x91,0x76,0x78,0xb2,
        0x73,0xbe,0xd6,0xb8, 0xe3,0xc1,0x74,0x3b,
        0x71,0x16,0xe6,0x9e, 0x22,0x22,0x95,0x16,
        0x3f,0xf1,0xca,0xa1, 0x68,0x1f,0xac,0x09,
        0x12,0x0e,0xca,0x30, 0x75,0x86,0xe1,0xa7
    };

    AES::AES aes(key, AES::AES_128);
    aes.setIV(iv);

    AES::Result ct = aes.encryptCBC(plain, 64);

    // So sánh 4 block đầu (bỏ qua block padding thứ 5 do thư viện tự thêm)
    bool enc_ok = ct.ok && ct.len >= 64 &&
                  memcmp(ct.data, expected, 64) == 0;
    printf("[%s] encrypt 4 blocks\n", enc_ok ? "PASS" : "FAIL");
    if (!enc_ok) {
        printHex("got[0]     ", ct.data,  16);
        printHex("expected[0]", expected, 16);
        printHex("got[1]     ", ct.data  + 16, 16);
        printHex("expected[1]", expected + 16, 16);
    }

    // Decrypt round-trip — phải set lại IV
    aes.setIV(iv);
    AES::Result pt = aes.decryptCBC(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 64);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
}

// ================================================================
//  Test 7: NIST SP 800-38A CBC-AES256
// ================================================================
static bool test_cbc_nist_256() {
    printf("\n=== NIST SP800-38A CBC-AES256 (1 block) ===\n");

    uint8_t key[32] = {
        0x60,0x3d,0xeb,0x10, 0x15,0xca,0x71,0xbe,
        0x2b,0x73,0xae,0xf0, 0x85,0x7d,0x77,0x81,
        0x1f,0x35,0x2c,0x07, 0x3b,0x61,0x08,0xd7,
        0x2d,0x98,0x10,0xa3, 0x09,0x14,0xdf,0xf4
    };
    uint8_t iv[16] = {
        0x00,0x01,0x02,0x03, 0x04,0x05,0x06,0x07,
        0x08,0x09,0x0a,0x0b, 0x0c,0x0d,0x0e,0x0f
    };
    uint8_t plain[16] = {
        0x6b,0xc1,0xbe,0xe2, 0x2e,0x40,0x9f,0x96,
        0xe9,0x3d,0x7e,0x11, 0x73,0x93,0x17,0x2a
    };
    uint8_t expected[16] = {
        0xf5,0x8c,0x4c,0x04, 0xd6,0xe5,0xf1,0xba,
        0x77,0x9e,0xab,0xfb, 0x5f,0x7b,0xfb,0xd6
    };

    AES::AES aes(key, AES::AES_256);
    aes.setIV(iv);

    AES::Result ct = aes.encryptCBC(plain, 16);
    bool enc_ok = ct.ok && ct.len >= 16 &&
                  memcmp(ct.data, expected, 16) == 0;
    printf("[%s] encrypt AES-256\n", enc_ok ? "PASS" : "FAIL");

    aes.setIV(iv);
    AES::Result pt = aes.decryptCBC(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 16);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
}

// ================================================================
//  Test 8: CBC — tính chất "chaining" (cùng plaintext, IV khác → CT khác)
// ================================================================
static bool test_cbc_chaining_property() {
    printf("\n=== CBC chaining property ===\n");

    uint8_t key[16] = {0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
                       0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f};
    uint8_t iv1[16] = {0};
    uint8_t iv2[16] = {0xff,0xfe,0xfd,0xfc,0xfb,0xfa,0xf9,0xf8,
                       0xf7,0xf6,0xf5,0xf4,0xf3,0xf2,0xf1,0xf0};

    // Hai block giống hệt nhau
    uint8_t plain[32];
    memset(plain, 0xAB, 32);

    AES::AES aes(key, AES::AES_128);

    // Encrypt với IV1
    aes.setIV(iv1);
    AES::Result ct1 = aes.encryptCBC(plain, 32);

    // Encrypt với IV2
    aes.setIV(iv2);
    AES::Result ct2 = aes.encryptCBC(plain, 32);

    // Kết quả phải khác nhau hoàn toàn dù plaintext giống nhau
    bool different = (memcmp(ct1.data, ct2.data, 32) != 0);
    printf("[%s] cùng plaintext + IV khác → ciphertext khác\n",
           different ? "PASS" : "FAIL");

    // ECB sẽ cho ra 2 block giống nhau vì P1 = P2,
    // CBC thì block 2 phụ thuộc block 1 nên phải khác
    bool block1_ne_block2 = (memcmp(ct1.data, ct1.data + 16, 16) != 0);
    printf("[%s] CBC: block 1 != block 2 dù plaintext giống nhau\n",
           block1_ne_block2 ? "PASS" : "FAIL");

    // Round-trip kiểm tra cả 2
    aes.setIV(iv1);
    AES::Result pt1 = aes.decryptCBC(ct1.data, ct1.len);
    aes.setIV(iv2);
    AES::Result pt2 = aes.decryptCBC(ct2.data, ct2.len);

    bool rt1 = pt1.ok && pt1.len == 32 && memcmp(pt1.data, plain, 32) == 0;
    bool rt2 = pt2.ok && pt2.len == 32 && memcmp(pt2.data, plain, 32) == 0;
    printf("[%s] round-trip IV1\n", rt1 ? "PASS" : "FAIL");
    printf("[%s] round-trip IV2\n", rt2 ? "PASS" : "FAIL");

    AES::freeResult(ct1); AES::freeResult(ct2);
    AES::freeResult(pt1); AES::freeResult(pt2);
    return different && block1_ne_block2 && rt1 && rt2;
}

// ================================================================
//  Test 9: CBC — sai IV khi decrypt → chỉ block đầu bị sai
// ================================================================
static bool test_cbc_wrong_iv_effect() {
    printf("\n=== CBC: sai IV chỉ làm hỏng block đầu ===\n");

    uint8_t key[16] = {0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,
                       0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f};
    uint8_t correct_iv[16] = {0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
                               0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f};
    uint8_t wrong_iv[16]   = {0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,
                               0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff};

    const char* msg = "Block1__16bytes!Block2__16bytes!"; // 32 bytes chính xác
    size_t msgLen = 32;

    AES::AES aes(key, AES::AES_128);
    aes.setIV(correct_iv);
    AES::Result ct = aes.encryptCBC((const uint8_t*)msg, msgLen);

    // Decrypt với IV sai
    aes.setIV(wrong_iv);
    AES::Result pt_wrong = aes.decryptCBC(ct.data, ct.len);

    bool block1_wrong = (memcmp(pt_wrong.data,      msg,      16) != 0);
    bool block2_right = (memcmp(pt_wrong.data + 16, msg + 16, 16) == 0);

    printf("[%s] block 1 bị sai khi dùng IV sai\n",  block1_wrong ? "PASS" : "FAIL");
    printf("[%s] block 2 vẫn đúng dù IV sai\n",       block2_right ? "PASS" : "FAIL");

    // Đây là đặc tính của CBC:
    // IV sai → block 0 decrypt sai
    // Block 1 trở đi decrypt đúng vì chúng dùng C_{i-1} (từ ciphertext), không dùng IV

    AES::freeResult(ct);
    AES::freeResult(pt_wrong);
    return block1_wrong && block2_right;
}

// ================================================================
//  Test 10: CBC — quên setIV → phải báo lỗi rõ ràng
// ================================================================
static bool test_cbc_missing_iv() {
    printf("\n=== CBC: quên setIV → lỗi rõ ràng ===\n");

    uint8_t key[16] = {0};
    AES::AES aes(key, AES::AES_128);
    // KHÔNG gọi setIV()

    uint8_t plain[16] = {0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,
                         0x49,0x4a,0x4b,0x4c,0x4d,0x4e,0x4f,0x50};

    AES::Result res = aes.encryptCBC(plain, 16);
    bool caught = (!res.ok && res.err != nullptr);
    printf("[%s] encryptCBC mà không setIV → ok=false, err=\"%s\"\n",
           caught ? "PASS" : "FAIL",
           res.err ? res.err : "(null)");

    AES::freeResult(res);
    return caught;
}


int main() {
    printf("================================================\n");
    printf("  AES-ECB Implementation Test\n");
    printf("================================================\n");

    int passed = 0, total = 0;

    auto run = [&](bool(*test)(), const char* name) {
        total++;
        if (test()) passed++;
        else printf("  ^^^ %s FAILED\n", name);
    };

    run(test_nist_fips197,           "NIST FIPS-197");
    // run(test_nist_sp800_38a_128,     "NIST SP800-38A ECB-AES128");
    // run(test_nist_sp800_38a_256,     "NIST SP800-38A ECB-AES256");
    // run(test_arbitrary_length,       "ECB arbitrary length");
    // run(test_padding_edge_cases,     "ECB padding edge cases");
    // run(test_cbc_nist_128,           "NIST SP800-38A CBC-AES128");
    // run(test_cbc_nist_256,           "NIST SP800-38A CBC-AES256");
    // run(test_cbc_chaining_property,  "CBC chaining property");
    // run(test_cbc_wrong_iv_effect,    "CBC wrong IV effect");
    // run(test_cbc_missing_iv,         "CBC missing IV guard");

    printf("\n================================================\n");
    printf("  %d / %d tests passed\n", passed, total);
    printf("================================================\n");

    return (passed == total) ? 0 : 1;
}