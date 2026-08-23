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

class AES
{
public:
    AES(AESKeyLength key_length, AESMode mode);
    ~AES();
    void keyExpansion(bytes key);
    bytes getExpandedKey()
    {
        return this->w;
    }
    void setMode(AESMode mode);
    void setIV(bytes iv);
    void setCounter(bytes counter)
    {
        memcpy(this->iv, counter, 16);
    }

    bytes cipher(bytes data);
    bytes decrypt(bytes data);

private:
    int Nk, Nr;
    bytes w;
    bytes iv;
    AESMode mode;

    void addRoundKey(bytes state, int round);
    void subBytes(bytes state);
    void shiftRows(bytes s);
    void mixColumns(bytes s);

    void invSubBytes(bytes state);
    void invShiftRows(bytes s);
    void invMixColumns(bytes s);

    void invCipherBlock(bytes state);
    void cipherBlock(bytes state);
    void incrementCounter();
};

static void printByte4(const char *label, const byte *b)
{
    printf("%s: %02X %02X %02X %02X\n", label, b[0], b[1], b[2], b[3]);
}
static void printByte16(const char *label, const byte *b)
{
    printf("%s: %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X\n", label, b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}