
#ifndef AES_HPP
#define AES_HPP
#include <cstdint>
#include <array>
#include <iomanip> 
#include <assert.h>
#include <cstring>
#define warning(message) {std::cout << "\033[33m[WARNING]\033[0m " << message << std::endl;}
#define info(message) {  std::cout << "\033[34m[INFO]\033[0m " << message << std::endl;}
#define error(message) {    std::cout << "\033[31m[ERROR]\033[0m " << message << std::endl;}
#define info_hex(message) {\
        std::cout << "\033[34m[INFO]\033[0m ";         \
        std::cout << std::hex << std::uppercase << "0x" << std::setw(2) << std::setfill('0') << (int)message << std::endl; \
}
#define info_hex_array(arr, len)                       \
    {                                                  \
        std::cout << "\033[34m[INFO]\033[0m ";         \
        for (int i = 0; i < (len); ++i)                \
            std::cout << std::hex << std::uppercase    \
                      << "0x" << std::setw(2)          \
                      << std::setfill('0')             \
                      << (int)(arr)[i] << " ";         \
        std::cout << std::dec << std::endl;            \
    }
#define info_hex_array_range(arr, a, b)                      \
    {                                                        \
        std::cout << "\033[34m[INFO]\033[0m ";               \
        for (int j = (a); j < (b); ++j)                     \
            std::cout << std::hex << std::uppercase          \
                      << "0x" << std::setw(2)                \
                      << std::setfill('0')                   \
                      << (int)(arr)[j] << " ";               \
        std::cout << std::dec << std::endl;                  \
    }
using byte  = uint8_t;
using bytes = uint8_t*;
namespace AES{

enum KeySize {
    AES_128 = 16,   // Nk=4,  Nr=10
    AES_192 = 24,   // Nk=6,  Nr=12
    AES_256 = 32,   // Nk=8,  Nr=14
};

enum Mode {
    ECB,    // Electronic Codebook        
    CBC,    // Cipher Block Chaining        
    CFB,    // Cipher FeedBack (s=128)      
    OFB,    // Output FeedBack              
    CTR,    // Counter                     
};

struct Result {
    bytes  data;    
    size_t len;
    bool   ok;
    const char* err;

    Result() : data(nullptr), len(0), ok(false), err(nullptr) {}
};

void freeResult(Result& r);

class AES {
public:
    AES(const byte* key, KeySize keySize);
    ~AES();

    void setMode(Mode mode);
    void setIV(const byte* iv);          // CBC, CFB, OFB: 16 bytes
    void setNonce(const byte* nonce);    // CTR: 12 bytes

    Result encryptECB(const byte* plain, size_t plainLen);
    Result decryptECB(const byte* cipher, size_t cipherLen);


private:
    int Nk;     
    int Nr;     

    byte* w;    
    void  keyExpansion(const byte* key);

    void encryptBlock(const byte* in, byte* out) const;
    void decryptBlock(const byte* in, byte* out) const;

    void addRoundKey  (byte* state, int round) const;
    void subBytes     (byte* state) const;
    void shiftRows    (byte* state) const;
    void mixColumns   (byte* state) const;
    void invSubBytes  (byte* state) const;
    void invShiftRows (byte* state) const;
    void invMixColumns(byte* state) const;

    static bytes   pkcs7Pad  (const byte* in, size_t inLen, size_t& outLen);
    static size_t  pkcs7Unpad(const byte* in, size_t inLen);

    static byte xtime(byte x);
    static byte gmul (byte a, byte b);
};

}
#endif