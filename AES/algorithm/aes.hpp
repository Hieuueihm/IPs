#pragma once
#include <stdio.h>
#include <cstdint>
#include <stdexcept>
#include <cstring>
using byte = uint8_t;
using bytes = uint8_t *;
byte xtime(byte x);
enum AESKeyLength
{
    AES128_L = 16,
    AES192_L = 24,
    AES256_L = 32
};
enum AESMode
{
    AES_ECB,
    AES_CBC,
    AES_CTR
};
struct Result
{
    bytes data;
    size_t len;
    bool is_ok;
    char *err;

    Result() : data(nullptr), len(0), is_ok(false), err(nullptr) {}
};
class AES
{
public:
    AES(AESKeyLength key_length, AESMode mode, bytes key, bytes iv = nullptr);
    ~AES();

    void setMode(AESMode mode);
    void setIV(bytes iv);
    void keyExpansion(bytes key, bytes w);

    // Result cipher(bytes data, size_t len);
    // Result decrypt(bytes data, size_t len);

private:
    int Nk, Nr;
    bytes w;

    AESMode mode;
    bytes key;
    bytes iv;

    void addRoundKey(bytes state, int round);
    void subBytes(bytes state);
    void shiftRows(bytes s);
    void mixColumns(bytes s);
};

static void printByte4(const char *label, const byte *b)
{
    printf("%s: %02X %02X %02X %02X\n", label, b[0], b[1], b[2], b[3]);
}
static void printByte16(const char *label, const byte *b)
{
    printf("%s: %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X\n", label, b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}