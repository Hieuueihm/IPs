#include "aes.hpp"
#include "aes_tables.hpp"

byte xtime(byte x)
{
    return (x << 1) ^ ((x & 0x80) ? 0x1b : 0x00);
}
AES::AES(AESKeyLength key_length, AESMode mode, bytes key, bytes iv)
{
    switch (key_length)
    {
    case AES128_L:
        this->Nk = 4;
        this->Nr = 10;
        break;
    case AES192_L:
        this->Nk = 6;
        this->Nr = 12;
        break;
    case AES256_L:
        this->Nk = 8;
        this->Nr = 14;
        break;
    default:
        throw std::invalid_argument("Invalid key length");
    }
    this->mode = mode;
    this->key = key;
    this->iv = iv;
}

AES::~AES()
{

    delete[] key;
    delete[] iv;
}

void AES::setMode(AESMode mode)
{
    this->mode = mode;
}
void AES::setIV(bytes iv)
{
    this->iv = iv;
}

void AES::subBytes(bytes state)
{
    for (int i = 0; i < 16; i++)
    {
        state[i] = SBOX[state[i]];
    }
}

void AES::shiftRows(bytes s)
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
void AES::mixColumns(bytes s)
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

void AES::addRoundKey(bytes state, int round)
{
    const byte *rk = this->w + round * 16;
    for (int i = 0; i < 16; i++)
        state[i] ^= rk[i];
}

void AES::keyExpansion(bytes key, bytes w)
{
    memcpy(w, key, 4 * Nk); // Copy the original key into the first Nk words of w
    printf("=== Original Key ===\n");
    printByte16("Key Input", key);

    for (int i = Nk; i < 4 * (Nr + 1); i++)
    {
        byte temp[4];
        memcpy(temp, w + (i - 1) * 4, 4);
        printf("================================\n");
        printf("=== Round %d ===\n", i);
        printByte4("Temp", temp);
        if (i % Nk == 0)
        {
            byte t = temp[0];

            // rot word
            temp[0] = temp[1];
            temp[1] = temp[2];
            temp[2] = temp[3];
            temp[3] = t;

            printf("Rotated Temp\n");
            printByte4("Temp", temp);

            for (int j = 0; j < 4; j++)
            {
                temp[j] = SBOX[temp[j]];
            }
            printf("Substituted Temp\n");
            printByte4("Temp", temp);

            temp[0] ^= RCON[i / Nk];
            printf("RCON Applied Temp\n");
            printByte4("Temp", temp);
        }
        else if (Nk > 6 && i % Nk == 4)
        {
            for (int j = 0; j < 4; j++)
                temp[j] = SBOX[temp[j]];
        }
        const bytes prev = w + (i - Nk) * 4;
        bytes cur = w + i * 4;

        for (int j = 0; j < 4; j++)
            cur[j] = prev[j] ^ temp[j];

        printf("Final Word\n");
        printByte4("W", cur);
        printf("========================\n");
    }
}

//