#include <iostream>
#include <cstring>
#include <cstdio>
#include "aes.hpp"


static void printHex(const char* label, const uint8_t* data, size_t len) {
    printf("%-14s: ", label);
    for (size_t i = 0; i < len; i++) printf("%02x ", data[i]);
    printf("\n");
}


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
    uint8_t expected_ct[32] = { 
        0x39,0x25,0x84,0x1d, 0x02,0xdc,0x09,0xfb,
        0xdc,0x11,0x85,0x97, 0x19,0x6a,0x0b,0x32,
        0xd8,0xf1,0xd0,0x4a, 0x84,0x47,0xfc,0x8a,
        0x05,0xa1,0x04,0x45, 0x9f,0xb9,0x2c,0x3b
    };

    AES::AES aes(key, AES::AES_128);

    AES::Result ct = aes.encryptECB(plain, 16);
    printHex("plaintext ", plain,   16);
    printHex("ciphertext", ct.data, ct.len);

    bool enc_ok = ct.ok && ct.len >= 16 &&
                  (memcmp(ct.data, expected_ct, 16) == 0);
    printf("[%s] encrypt block 0\n", enc_ok ? "PASS" : "FAIL");

    AES::Result pt = aes.decryptECB(ct.data, ct.len);
    bool dec_ok = check("decrypt round-trip", pt.data, pt.len, plain, 16);

    AES::freeResult(ct);
    AES::freeResult(pt);
    return enc_ok && dec_ok;
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
//  main
// ================================================================
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

    run(test_nist_fips197,        "NIST FIPS-197");
    run(test_nist_sp800_38a_128,  "NIST SP800-38A AES-128");
    run(test_nist_sp800_38a_256,  "NIST SP800-38A AES-256");
    run(test_arbitrary_length,    "Arbitrary length");
    run(test_padding_edge_cases,  "Padding edge cases");

    printf("\n================================================\n");
    printf("  %d / %d tests passed\n", passed, total);
    printf("================================================\n");

    return (passed == total) ? 0 : 1;
}