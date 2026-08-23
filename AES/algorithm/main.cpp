#include <cstdio>
#include <cstring>

#include "aes.hpp"
#include "nist_vectors.hpp"

// ============================================================
// Utilities
// ============================================================

bool equal16(const byte *a, const byte *b)
{
    return std::memcmp(a, b, 16) == 0;
}

void printBytes(const char *label, const byte *data, std::size_t len)
{
    std::printf("%-12s: ", label);

    for (std::size_t i = 0; i < len; ++i)
        std::printf("%02X%s", data[i], (i + 1 == len) ? "" : " ");

    std::printf("\n");
}

void printMismatch(const byte *got, const byte *expected)
{
    for (int i = 0; i < 16; ++i)
    {
        if (got[i] != expected[i])
        {
            std::printf(
                "  byte[%2d] : got %02X, expected %02X\n",
                i, got[i], expected[i]);
        }
    }
}

void printSummary(const char *name, int passed, int total)
{
    std::printf("\n========================================\n");
    std::printf("%s\n", name);
    std::printf("Passed : %d / %d\n", passed, total);
    std::printf("Result : %s\n", (passed == total) ? "PASS" : "FAIL");
    std::printf("========================================\n");
}

void prepareKey(byte key[32], const byte *source, std::size_t keyLen)
{
    std::memset(key, 0, 32);
    std::memcpy(key, source, keyLen);
}

// ============================================================
// FIPS 197 - single-block AES/ECB-style tests
// ============================================================

bool runECBWithAES(AES &aes, const nist::ECBCase &tc)
{
    byte key[32];
    byte data[16];

    prepareKey(key, tc.key, tc.keyLen);
    std::memcpy(data, tc.plaintext, 16);

    aes.keyExpansion(key);

    bytes ciphertext = aes.cipher(data);
    const bool pass = equal16(ciphertext, tc.expected);

    std::printf("\n[%s] %s\n", pass ? "PASS" : "FAIL", tc.name);

    if (!pass)
    {
        printBytes("Plaintext", tc.plaintext, 16);
        printBytes("Key", tc.key, tc.keyLen);
        printBytes("Got", ciphertext, 16);
        printBytes("Expected", tc.expected, 16);
        printMismatch(ciphertext, tc.expected);
    }

    delete[] ciphertext;
    return pass;
}

bool runECBCase(const nist::ECBCase &tc)
{
    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_ECB);
        return runECBWithAES(aes, tc);
    }
    case 24:
    {
        AES aes(AES192_L, AES_ECB);
        return runECBWithAES(aes, tc);
    }
    case 32:
    {
        AES aes(AES256_L, AES_ECB);
        return runECBWithAES(aes, tc);
    }
    default:
        return false;
    }
}

void FIPS197()
{
    std::printf("\n========================================\n");
    std::printf("          FIPS-197 CIPHER TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::FIPS_CASES)
        passed += runECBCase(tc);

    printSummary(
        "FIPS-197 SUMMARY",
        passed,
        static_cast<int>(nist::FIPS_CASE_COUNT));
}

// ============================================================
// Shared multi-block checker
// ============================================================

bool checkBlock(
    int block,
    const byte *plaintext,
    const byte *ciphertext,
    const byte *expected)
{
    const bool pass = equal16(ciphertext, expected);

    std::printf(
        "  [%s] Block %d\n",
        pass ? "PASS" : "FAIL",
        block + 1);

    if (!pass)
    {
        printBytes("Plaintext", plaintext, 16);
        printBytes("Got", ciphertext, 16);
        printBytes("Expected", expected, 16);
        printMismatch(ciphertext, expected);
    }

    return pass;
}

// ============================================================
// CBC - NIST SP 800-38A F.2
// ============================================================

bool runCBCWithAES(AES &aes, const nist::MultiBlockCase &tc)
{
    byte key[32];
    byte iv[16];

    prepareKey(key, tc.key, tc.keyLen);
    std::memcpy(iv, nist::CBC_IV, 16);

    aes.keyExpansion(key);
    aes.setIV(iv);

    bool pass = true;

    for (int block = 0; block < 4; ++block)
    {
        byte data[16];
        std::memcpy(data, nist::SP_PT[block], 16);

        bytes ciphertext = aes.cipher(data);
        const byte *expected = tc.expected + block * 16;

        pass &= checkBlock(
            block,
            nist::SP_PT[block],
            ciphertext,
            expected);

        delete[] ciphertext;
    }

    return pass;
}

bool runCBCCase(const nist::MultiBlockCase &tc)
{
    std::printf("\n%s\n", tc.name);

    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_CBC);
        return runCBCWithAES(aes, tc);
    }
    case 24:
    {
        AES aes(AES192_L, AES_CBC);
        return runCBCWithAES(aes, tc);
    }
    case 32:
    {
        AES aes(AES256_L, AES_CBC);
        return runCBCWithAES(aes, tc);
    }
    default:
        return false;
    }
}

void SP800_38A_CBC()
{
    std::printf("\n========================================\n");
    std::printf("      NIST SP 800-38A CBC TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::CBC_CASES)
        passed += runCBCCase(tc);

    printSummary(
        "SP 800-38A CBC SUMMARY",
        passed,
        static_cast<int>(nist::CBC_CASE_COUNT));
}

// ============================================================
// CTR - NIST SP 800-38A F.5
// ============================================================

bool runCTRWithAES(AES &aes, const nist::MultiBlockCase &tc)
{
    byte key[32];
    byte counter[16];

    prepareKey(key, tc.key, tc.keyLen);
    std::memcpy(counter, nist::CTR_INITIAL_COUNTER, 16);

    aes.keyExpansion(key);
    aes.setCounter(counter);

    bool pass = true;

    for (int block = 0; block < 4; ++block)
    {
        byte data[16];
        std::memcpy(data, nist::SP_PT[block], 16);

        bytes ciphertext = aes.cipher(data);
        const byte *expected = tc.expected + block * 16;

        pass &= checkBlock(
            block,
            nist::SP_PT[block],
            ciphertext,
            expected);

        delete[] ciphertext;
    }

    return pass;
}

bool runCTRCase(const nist::MultiBlockCase &tc)
{
    std::printf("\n%s\n", tc.name);

    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_CTR);
        return runCTRWithAES(aes, tc);
    }
    case 24:
    {
        AES aes(AES192_L, AES_CTR);
        return runCTRWithAES(aes, tc);
    }
    case 32:
    {
        AES aes(AES256_L, AES_CTR);
        return runCTRWithAES(aes, tc);
    }
    default:
        return false;
    }
}

void SP800_38A_CTR()
{
    std::printf("\n========================================\n");
    std::printf("      NIST SP 800-38A CTR TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::CTR_CASES)
        passed += runCTRCase(tc);

    printSummary(
        "SP 800-38A CTR SUMMARY",
        passed,
        static_cast<int>(nist::CTR_CASE_COUNT));
}

bool runInvECBWithAES(AES &aes, const nist::ECBCase &tc)
{
    byte key[32];
    byte ciphertext[16];

    prepareKey(key, tc.key, tc.keyLen);

    std::memcpy(ciphertext, tc.expected, 16);

    aes.keyExpansion(key);

    bytes plaintext = aes.decrypt(ciphertext);

    const bool pass = equal16(
        plaintext,
        tc.plaintext);

    std::printf(
        "\n[%s] INV %s\n",
        pass ? "PASS" : "FAIL",
        tc.name);

    if (!pass)
    {
        printBytes(
            "Ciphertext",
            tc.expected,
            16);

        printBytes(
            "Key",
            tc.key,
            tc.keyLen);

        printBytes(
            "Got",
            plaintext,
            16);

        printBytes(
            "Expected",
            tc.plaintext,
            16);

        printMismatch(
            plaintext,
            tc.plaintext);
    }

    delete[] plaintext;

    return pass;
}
bool runInvECBCase(const nist::ECBCase &tc)
{
    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_ECB);

        return runInvECBWithAES(
            aes,
            tc);
    }

    case 24:
    {
        AES aes(AES192_L, AES_ECB);

        return runInvECBWithAES(
            aes,
            tc);
    }

    case 32:
    {
        AES aes(AES256_L, AES_ECB);

        return runInvECBWithAES(
            aes,
            tc);
    }

    default:
        return false;
    }
}

void FIPS197_INV()
{
    std::printf("\n");
    std::printf("========================================\n");
    std::printf("       FIPS-197 INVERSE CIPHER TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::FIPS_CASES)
    {
        passed += runInvECBCase(tc);
    }

    printSummary(
        "FIPS-197 INVERSE SUMMARY",
        passed,
        static_cast<int>(nist::FIPS_CASE_COUNT));
}

// ============================================================
// CBC DECRYPT - NIST SP 800-38A F.2
// ============================================================

bool runInvCBCWithAES(
    AES &aes,
    const nist::MultiBlockCase &tc)
{
    byte key[32];
    byte iv[16];

    prepareKey(key, tc.key, tc.keyLen);
    std::memcpy(iv, nist::CBC_IV, 16);

    aes.keyExpansion(key);

    aes.setIV(iv);

    bool pass = true;

    for (int block = 0; block < 4; ++block)
    {
        byte ciphertext[16];

        const byte *cipherBlock =
            tc.expected + block * 16;

        std::memcpy(
            ciphertext,
            cipherBlock,
            16);

        bytes plaintext =
            aes.decrypt(ciphertext);

        const bool blockPass =
            equal16(
                plaintext,
                nist::SP_PT[block]);

        std::printf(
            "  [%s] Block %d\n",
            blockPass ? "PASS" : "FAIL",
            block + 1);

        if (!blockPass)
        {
            printBytes(
                "Ciphertext",
                cipherBlock,
                16);

            printBytes(
                "Got",
                plaintext,
                16);

            printBytes(
                "Expected",
                nist::SP_PT[block],
                16);

            printMismatch(
                plaintext,
                nist::SP_PT[block]);

            pass = false;
        }

        delete[] plaintext;
    }

    return pass;
}

bool runInvCBCCase(
    const nist::MultiBlockCase &tc)
{
    std::printf(
        "\nINV %s\n",
        tc.name);

    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_CBC);
        return runInvCBCWithAES(aes, tc);
    }

    case 24:
    {
        AES aes(AES192_L, AES_CBC);
        return runInvCBCWithAES(aes, tc);
    }

    case 32:
    {
        AES aes(AES256_L, AES_CBC);
        return runInvCBCWithAES(aes, tc);
    }

    default:
        return false;
    }
}

void SP800_38A_CBC_INV()
{
    std::printf("\n");
    std::printf("========================================\n");
    std::printf("   NIST SP 800-38A CBC DECRYPT TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::CBC_CASES)
    {
        passed += runInvCBCCase(tc);
    }

    printSummary(
        "SP 800-38A CBC DECRYPT SUMMARY",
        passed,
        static_cast<int>(
            nist::CBC_CASE_COUNT));
}

// ============================================================
// CTR DECRYPT - NIST SP 800-38A F.5
// ============================================================

bool runInvCTRWithAES(
    AES &aes,
    const nist::MultiBlockCase &tc)
{
    byte key[32];
    byte counter[16];

    prepareKey(key, tc.key, tc.keyLen);

    std::memcpy(
        counter,
        nist::CTR_INITIAL_COUNTER,
        16);

    aes.keyExpansion(key);

    aes.setCounter(counter);

    bool pass = true;

    for (int block = 0; block < 4; ++block)
    {
        byte ciphertext[16];

        const byte *cipherBlock =
            tc.expected + block * 16;

        std::memcpy(
            ciphertext,
            cipherBlock,
            16);

        bytes plaintext =
            aes.decrypt(ciphertext);

        const bool blockPass =
            equal16(
                plaintext,
                nist::SP_PT[block]);

        std::printf(
            "  [%s] Block %d\n",
            blockPass ? "PASS" : "FAIL",
            block + 1);

        if (!blockPass)
        {
            printBytes(
                "Ciphertext",
                cipherBlock,
                16);

            printBytes(
                "Got",
                plaintext,
                16);

            printBytes(
                "Expected",
                nist::SP_PT[block],
                16);

            printMismatch(
                plaintext,
                nist::SP_PT[block]);

            pass = false;
        }

        delete[] plaintext;
    }

    return pass;
}

bool runInvCTRCase(
    const nist::MultiBlockCase &tc)
{
    std::printf(
        "\nINV %s\n",
        tc.name);

    switch (tc.keyLen)
    {
    case 16:
    {
        AES aes(AES128_L, AES_CTR);
        return runInvCTRWithAES(aes, tc);
    }

    case 24:
    {
        AES aes(AES192_L, AES_CTR);
        return runInvCTRWithAES(aes, tc);
    }

    case 32:
    {
        AES aes(AES256_L, AES_CTR);
        return runInvCTRWithAES(aes, tc);
    }

    default:
        return false;
    }
}

void SP800_38A_CTR_INV()
{
    std::printf("\n");
    std::printf("========================================\n");
    std::printf("   NIST SP 800-38A CTR DECRYPT TEST\n");
    std::printf("========================================\n");

    int passed = 0;

    for (const auto &tc : nist::CTR_CASES)
    {
        passed += runInvCTRCase(tc);
    }

    printSummary(
        "SP 800-38A CTR DECRYPT SUMMARY",
        passed,
        static_cast<int>(
            nist::CTR_CASE_COUNT));
}
int main()
{
    // FIPS197();
    // SP800_38A_CBC();
    // SP800_38A_CTR();

        // bytes ciphertext = new byte[16]{0x69, 0xC4, 0xE0, 0xD8, 0x6A, 0x7B, 0x04, 0x30,
    //                                 0xD8, 0xCD, 0xB7, 0x80, 0x70, 0xB4, 0xC5, 0x5A};
    // bytes key = new byte[16]{0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    //                          0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F};

    // AES aes(AES128_L, AES_ECB);
    // aes.keyExpansion(key);
    // bytes plaintext = aes.decrypt(ciphertext);
    // printBytes("Plaintext", plaintext, 16);

    FIPS197_INV();

    SP800_38A_CBC_INV();
    SP800_38A_CTR_INV();

    return 0;
}