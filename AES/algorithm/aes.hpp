#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdlib>
#include <iostream>
#include <iomanip>
using byte = uint8_t;
using bytes = uint8_t *;

static void printState(const char* label, const byte state[16])
{
    std::cout << label << ":\n";
    for (int i = 0; i < 16; i++)
    {
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << (int)state[i] << " ";

        if ((i % 4) == 3) std::cout << "\n"; // in theo matrix 4x4
    }
    std::cout << std::dec << "\n";
}

namespace AES
{

    enum KeySize
    {
        AES_128 = 16, // Nk=4,  Nr=10
        AES_256 = 32, // Nk=8,  Nr=14
    };

    enum Mode
    {
        ECB, // Electronic Codebook
        CBC, // Cipher Block Chaining
        CFB, // Cipher FeedBack (s=128)
        OFB, // Output FeedBack
        CTR, // Counter
    };

    struct Result
    {
        bytes data;
        size_t len;
        bool ok;
        const char *err;

        Result() : data(nullptr), len(0), ok(false), err(nullptr) {}
    };

    void freeResult(Result &r);

    class AES
    {
    public:
        AES(const byte *key, KeySize keySize);
        ~AES();

        void setMode(Mode mode);
        void setIV(const byte *iv); // CBC, CFB, OFB: 16 bytes
        void setNonce(const byte *nonce);

        Result encryptECB(const byte *plain, size_t plainLen);
        Result decryptECB(const byte *cipher, size_t cipherLen);

        Result encryptCBC(const byte *plain, size_t plainLen);
        Result decryptCBC(const byte *cipher, size_t cipherLen);

    private:
        int Nk;
        int Nr;

        byte *w;
        void keyExpansion(const byte *key);

        byte iv_[16];
        bool ivSet_ = false;

        void encryptBlock(const byte *in, byte *out) const;
        void decryptBlock(const byte *in, byte *out) const;

        void addRoundKey(byte *state, int round) const;
        void subBytes(byte *state) const;
        void shiftRows(byte *state) const;
        void mixColumns(byte *state) const;
        void invSubBytes(byte *state) const;
        void invShiftRows(byte *state) const;
        void invMixColumns(byte *state) const;

        static bytes pkcs7Pad(const byte *in, size_t inLen, size_t &outLen);
        static size_t pkcs7Unpad(const byte *in, size_t inLen);

        static byte xtime(byte x);
        static byte gmul(byte a, byte b);
    };

}