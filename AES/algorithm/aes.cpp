#include "aes.hpp"
#include "aes_tables.hpp"
#include <cassert>
#include <cstdio>

namespace AES
{

    void freeResult(Result &r)
    {
        free(r.data);
        r.data = nullptr;
        r.len = 0;
    }

    byte AES::xtime(byte x)
    {
        return (x << 1) ^ ((x & 0x80) ? 0x1b : 0x00);
    }

    byte AES::gmul(byte a, byte b)
    {
        byte p = 0;
        for (int i = 0; i < 8; i++)
        {
            if (b & 1)
                p ^= a;
            bool hi = (a & 0x80);
            a <<= 1;
            if (hi)
                a ^= 0x1b;
            b >>= 1;
        }
        return p;
    }

    AES::AES(const byte *key, KeySize keySize)
    {
        switch (keySize)
        {
        case AES_128:
            Nk = 4;
            Nr = 10;
            break;
        case AES_256:
            Nk = 8;
            Nr = 14;
            break;
        }
        w = (byte *)malloc(16 * (Nr + 1));
        keyExpansion(key);
    }

    AES::~AES()
    {
        memset(w, 0, 16 * (Nr + 1));
        free(w);
    }

    void AES::setMode(Mode /*mode*/) {} // sẽ dùng khi thêm CFB/OFB/CTR
    void AES::setNonce(const byte * /*nonce*/) {}

    void AES::setIV(const byte *iv)
    {
        memcpy(iv_, iv, 16);
        ivSet_ = true;
    }

    void AES::keyExpansion(const byte *key)
    {
        memcpy(w, key, 4 * Nk);

        for (int i = Nk; i < 4 * (Nr + 1); i++)
        {
            byte temp[4];
            memcpy(temp, w + (i - 1) * 4, 4);

            if (i % Nk == 0)
            {
                byte t = temp[0];
                temp[0] = temp[1];
                temp[1] = temp[2];
                temp[2] = temp[3];
                temp[3] = t;

                for (int j = 0; j < 4; j++)
                    temp[j] = SBOX[temp[j]];

                temp[0] ^= RCON[i / Nk];
            }
            else if (Nk > 6 && i % Nk == 4)
            {
                for (int j = 0; j < 4; j++)
                    temp[j] = SBOX[temp[j]];
            }

            const byte *prev = w + (i - Nk) * 4;
            byte *cur = w + i * 4;
            for (int j = 0; j < 4; j++)
                cur[j] = prev[j] ^ temp[j];
        }
    }

    void AES::addRoundKey(byte *state, int round) const
    {
        const byte *rk = w + round * 16;
        for (int i = 0; i < 16; i++)
            state[i] ^= rk[i];
    }

    void AES::subBytes(byte *state) const
    {
        for (int i = 0; i < 16; i++)
            state[i] = SBOX[state[i]];
    }

    void AES::invSubBytes(byte *state) const
    {
        for (int i = 0; i < 16; i++)
            state[i] = INV_SBOX[state[i]];
    }

    void AES::shiftRows(byte *s) const
    {
        byte t;
        t = s[1];
        s[1] = s[5];
        s[5] = s[9];
        s[9] = s[13];
        s[13] = t;

        t = s[2];
        s[2] = s[10];
        s[10] = t;
        t = s[6];
        s[6] = s[14];
        s[14] = t;

        t = s[15];
        s[15] = s[11];
        s[11] = s[7];
        s[7] = s[3];
        s[3] = t;
    }

    void AES::invShiftRows(byte *s) const
    {
        byte t;
        t = s[13];
        s[13] = s[9];
        s[9] = s[5];
        s[5] = s[1];
        s[1] = t;

        t = s[2];
        s[2] = s[10];
        s[10] = t;
        t = s[6];
        s[6] = s[14];
        s[14] = t;

        t = s[3];
        s[3] = s[7];
        s[7] = s[11];
        s[11] = s[15];
        s[15] = t;
    }

    void AES::mixColumns(byte *s) const
    {
        for (int c = 0; c < 4; c++)
        {
            byte *col = s + c * 4;
            byte a = col[0], b = col[1], cc = col[2], d = col[3];

            col[0] = xtime(a) ^ (xtime(b) ^ b) ^ cc ^ d;
            col[1] = a ^ xtime(b) ^ (xtime(cc) ^ cc) ^ d;
            col[2] = a ^ b ^ xtime(cc) ^ (xtime(d) ^ d);
            col[3] = (xtime(a) ^ a) ^ b ^ cc ^ xtime(d);
        }
    }

    void AES::invMixColumns(byte *s) const
    {
        for (int c = 0; c < 4; c++)
        {
            byte *col = s + c * 4;
            byte a = col[0], b = col[1], cc = col[2], d = col[3];

            col[0] = gmul(0x0e, a) ^ gmul(0x0b, b) ^ gmul(0x0d, cc) ^ gmul(0x09, d);
            col[1] = gmul(0x09, a) ^ gmul(0x0e, b) ^ gmul(0x0b, cc) ^ gmul(0x0d, d);
            col[2] = gmul(0x0d, a) ^ gmul(0x09, b) ^ gmul(0x0e, cc) ^ gmul(0x0b, d);
            col[3] = gmul(0x0b, a) ^ gmul(0x0d, b) ^ gmul(0x09, cc) ^ gmul(0x0e, d);
        }
    }

    void AES::encryptBlock(const byte *in, byte *out) const
    {
        byte state[16];
        memcpy(state, in, 16);

        addRoundKey(state, 0);

        for (int r = 1; r < Nr; r++)
        {
            subBytes(state);
            shiftRows(state);
            mixColumns(state);
            addRoundKey(state, r);
        }

        subBytes(state);
        shiftRows(state);
        addRoundKey(state, Nr);

        memcpy(out, state, 16);
    }

    void AES::decryptBlock(const byte *in, byte *out) const
    {
        byte state[16];
        memcpy(state, in, 16);

        addRoundKey(state, Nr);

        for (int r = Nr - 1; r >= 1; r--)
        {
            invShiftRows(state);
            invSubBytes(state);
            addRoundKey(state, r);
            invMixColumns(state);
        }

        invShiftRows(state);
        invSubBytes(state);
        addRoundKey(state, 0);

        memcpy(out, state, 16);
    }

    bytes AES::pkcs7Pad(const byte *in, size_t inLen, size_t &outLen)
    {
        byte padByte = (byte)(16 - (inLen % 16)); // luôn từ 1 đến 16
        outLen = inLen + padByte;

        byte *out = (byte *)malloc(outLen);
        memcpy(out, in, inLen);
        memset(out + inLen, padByte, padByte);
        return out;
    }

    size_t AES::pkcs7Unpad(const byte *in, size_t inLen)
    {
        if (inLen == 0 || inLen % 16 != 0)
            return inLen;

        byte padByte = in[inLen - 1];
        if (padByte == 0 || padByte > 16)
            return inLen;

        for (size_t i = inLen - padByte; i < inLen; i++)
        {
            if (in[i] != padByte)
                return inLen;
        }

        return inLen - padByte;
    }

    Result AES::encryptECB(const byte *plain, size_t plainLen)
    {
        Result res;

        size_t paddedLen;
        byte *padded = pkcs7Pad(plain, plainLen, paddedLen);

        res.data = (byte *)malloc(paddedLen);
        res.len = paddedLen;
        res.ok = true;

        for (size_t i = 0; i < paddedLen; i += 16)
            encryptBlock(padded + i, res.data + i);

        free(padded);
        return res;
    }

    Result AES::decryptECB(const byte *cipher, size_t cipherLen)
    {
        Result res;

        if (cipherLen == 0 || cipherLen % 16 != 0)
        {
            res.ok = false;
            res.err = "Ciphertext length must be a multiple of 16";
            return res;
        }

        byte *decrypted = (byte *)malloc(cipherLen);
        for (size_t i = 0; i < cipherLen; i += 16)
            decryptBlock(cipher + i, decrypted + i);

        size_t realLen = pkcs7Unpad(decrypted, cipherLen);
        if (realLen == cipherLen && decrypted[cipherLen - 1] > 16)
        {
            free(decrypted);
            res.ok = false;
            res.err = "Invalid PKCS#7 padding — wrong key or corrupted data";
            return res;
        }

        res.data = (byte *)malloc(realLen);
        res.len = realLen;
        res.ok = true;
        memcpy(res.data, decrypted, realLen);
        free(decrypted);
        return res;
    }

    Result AES::encryptCBC(const byte *plain, size_t plainLen)
    {
        Result res;
        if (!ivSet_)
        {
            res.ok = false;
            res.err = "IV chưa được set — gọi setIV() trước khi encrypt";
            return res;
        }

        size_t paddedLen;
        byte *padded = pkcs7Pad(plain, plainLen, paddedLen);

        res.data = (byte *)malloc(paddedLen);
        res.len = paddedLen;
        res.ok = true;

        const byte *prev = iv_;

        for (size_t i = 0; i < paddedLen; i += 16)
        {
            byte xored[16];
            for (int j = 0; j < 16; j++)
                xored[j] = padded[i + j] ^ prev[j];

            encryptBlock(xored, res.data + i);

            prev = res.data + i;
        }

        free(padded);
        return res;
    }

    Result AES::decryptCBC(const byte *cipher, size_t cipherLen)
    {
        Result res;
        if (!ivSet_)
        {
            res.ok = false;
            res.err = "IV chưa được set — gọi setIV() trước khi decrypt";
            return res;
        }
        if (cipherLen == 0 || cipherLen % 16 != 0)
        {
            res.ok = false;
            res.err = "Ciphertext CBC phải là bội số 16 bytes";
            return res;
        }

        byte *decrypted = (byte *)malloc(cipherLen);

        for (size_t i = 0; i < cipherLen; i += 16)
        {
            byte aesOut[16];
            decryptBlock(cipher + i, aesOut);

            const byte *prev = (i == 0) ? iv_ : cipher + i - 16;
            for (int j = 0; j < 16; j++)
                decrypted[i + j] = aesOut[j] ^ prev[j];
        }

        size_t realLen = pkcs7Unpad(decrypted, cipherLen);
        if (realLen == cipherLen && decrypted[cipherLen - 1] > 16)
        {
            free(decrypted);
            res.ok = false;
            res.err = "Padding không hợp lệ — sai key, sai IV, hoặc data bị hỏng";
            return res;
        }

        res.data = (byte *)malloc(realLen);
        res.len = realLen;
        res.ok = true;
        memcpy(res.data, decrypted, realLen);
        free(decrypted);
        return res;
    }

} // namespace AES