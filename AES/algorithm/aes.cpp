#include "aes.hpp"
#include "aes_tables.hpp"

byte xtime(byte x)
{
    return (x << 1) ^ ((x & 0x80) ? 0x1b : 0x00);
}
AES::AES(AESKeyLength key_length, AESMode mode)
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
    this->w = new byte[4 * (Nr + 1) * 4];
    this->iv = new byte[16];
}

AES::~AES()
{
    delete[] this->w;
    delete[] this->iv;
}

void AES::setMode(AESMode mode)
{
    this->mode = mode;
}
void AES::setIV(bytes iv)
{
    memcpy(this->iv, iv, 16);
}

void AES::subBytes(bytes state)
{
    for (int i = 0; i < 16; i++)
    {
        state[i] = SBOX[state[i]];
    }
}
void AES::invSubBytes(bytes state)
{
    for (int i = 0; i < 16; i++)
    {
        state[i] = INV_SBOX[state[i]];
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

void AES::invShiftRows(bytes s)
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
void AES::invMixColumns(bytes s)
{
    for (int c = 0; c < 4; c++)
    {
        byte *col = s + c * 4;

        byte a = col[0];
        byte b = col[1];
        byte cc = col[2];
        byte d = col[3];

        byte a2 = xtime(a);
        byte a4 = xtime(a2);
        byte a8 = xtime(a4);

        byte b2 = xtime(b);
        byte b4 = xtime(b2);
        byte b8 = xtime(b4);

        byte c2 = xtime(cc);
        byte c4 = xtime(c2);
        byte c8 = xtime(c4);

        byte d2 = xtime(d);
        byte d4 = xtime(d2);
        byte d8 = xtime(d4);

        // 0E = 8 + 4 + 2
        // 0B = 8 + 2 + 1
        // 0D = 8 + 4 + 1
        // 09 = 8 + 1

        col[0] =
            (a8 ^ a4 ^ a2) ^
            (b8 ^ b2 ^ b) ^
            (c8 ^ c4 ^ cc) ^
            (d8 ^ d);

        col[1] =
            (a8 ^ a) ^
            (b8 ^ b4 ^ b2) ^
            (c8 ^ c2 ^ cc) ^
            (d8 ^ d4 ^ d);

        col[2] =
            (a8 ^ a4 ^ a) ^
            (b8 ^ b) ^
            (c8 ^ c4 ^ c2) ^
            (d8 ^ d2 ^ d);

        col[3] =
            (a8 ^ a2 ^ a) ^
            (b8 ^ b4 ^ b) ^
            (c8 ^ cc) ^
            (d8 ^ d4 ^ d2);
    }
}

void AES::addRoundKey(bytes state, int round)
{
    const byte *rk = this->w + round * 16;
    for (int i = 0; i < 16; i++)
        state[i] ^= rk[i];
}
void AES::keyExpansion(bytes key)
{
    // printf("=== Key Expansion ===\n");
    memcpy(this->w, key, 4 * Nk); // Copy the original key into the first Nk words of w
#ifdef DEBUG_KEY_EXPAN
    printf("=== Original Key ===\n");
    printByte16("Key Input", key);
#endif
    for (int i = Nk; i < 4 * (Nr + 1); i++)
    {
        byte temp[4];
        memcpy(temp, this->w + (i - 1) * 4, 4);
#ifdef DEBUG_KEY_EXPAN
        printf("================================\n");
        printf("=== Round %d ===\n", i);
        printByte4("Temp", temp);
#endif
        if (i % Nk == 0)
        {
            byte t = temp[0];

            // rot word
            temp[0] = temp[1];
            temp[1] = temp[2];
            temp[2] = temp[3];
            temp[3] = t;
#ifdef DEBUG_KEY_EXPAN
            printf("Rotated Temp\n");
            printByte4("Temp", temp);
#endif
            for (int j = 0; j < 4; j++)
            {
                temp[j] = SBOX[temp[j]];
            }
#ifdef DEBUG_KEY_EXPAN
            printf("Substituted Temp\n");
            printByte4("Temp", temp);
#endif
            temp[0] ^= RCON[i / Nk];
#ifdef DEBUG_KEY_EXPAN
            printf("RCON Applied Temp\n");
            printByte4("Temp", temp);
#endif
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
#ifdef DEBUG_KEY_EXPAN
        printf("Final Word\n");
        printByte4("W", cur);
        printf("========================\n");
#endif
    }
}

void AES::cipherBlock(bytes state)
{
    addRoundKey(state, 0);

    for (int round = 1; round < Nr; round++)
    {
        subBytes(state);
        shiftRows(state);
        mixColumns(state);
        addRoundKey(state, round);
    }

    subBytes(state);
    shiftRows(state);
    addRoundKey(state, Nr);
}

void AES::invCipherBlock(bytes state)
{
    // printByte16("State Input", state);
    // printByte16("Round Key", this->w + Nr * 16);
    addRoundKey(state, Nr);
    // printByte16("After AddRoundKey", state);

    for (int round = Nr - 1; round > 0; round--)
    {
        // printf("================================\n");
        // printf("=== Round %d ===\n", round);
        invShiftRows(state);
        // printByte16("After InvShiftRows", state);
        invSubBytes(state);
        // printByte16("After InvSubBytes", state);
        addRoundKey(state, round);
        // printByte16("After AddRoundKey", state);
        invMixColumns(state);
        // printByte16("After InvMixColumns", state);
        // printf("================================\n");
    }

    invShiftRows(state);
    invSubBytes(state);
    addRoundKey(state, 0);
}
void AES::incrementCounter()
{
    for (int i = 15; i >= 0; i--)
    {
        this->iv[i]++;

        if (this->iv[i] != 0)
            break;
    }
}
bytes AES::cipher(bytes data)
{
    bytes state = new byte[16];

    memcpy(state, data, 16);

    if (this->mode == AES_ECB)
    {
        cipherBlock(state);
    }

    else if (this->mode == AES_CBC)
    {
        for (int i = 0; i < 16; i++)
        {
            state[i] ^= this->iv[i];
        }

        cipherBlock(state);

        memcpy(this->iv, state, 16);
    }

    else if (this->mode == AES_CTR)
    {
        byte keystream[16];

        memcpy(keystream, this->iv, 16);
        cipherBlock(keystream);
        for (int i = 0; i < 16; i++)
        {
            state[i] ^= keystream[i];
        }
        incrementCounter();
    }

    else
    {
        delete[] state;

        throw std::invalid_argument(
            "Unsupported AES mode");
    }

    return state;
}
bytes AES::decrypt(bytes data)
{
    bytes state = new byte[16];

    memcpy(state, data, 16);

    if (this->mode == AES_ECB)
    {
        invCipherBlock(state);
    }

    else if (this->mode == AES_CBC)
    {

        invCipherBlock(state);

        for (int i = 0; i < 16; i++)
        {
            state[i] ^= this->iv[i];
        }

        memcpy(this->iv, data, 16);
    }

    else if (this->mode == AES_CTR)
    {
        byte keystream[16];

        memcpy(keystream, this->iv, 16);
        cipherBlock(keystream);
        for (int i = 0; i < 16; i++)
        {
            state[i] ^= keystream[i];
        }
        incrementCounter();
    }

    else
    {
        delete[] state;

        throw std::invalid_argument(
            "Unsupported AES mode");
    }

    return state;
}