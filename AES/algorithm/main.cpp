#include <iostream>
#include "aes.hpp"
int main(){
	  uint8_t key[16] = {
        0x2b, 0x7e, 0x15, 0x16,
        0x28, 0xae, 0xd2, 0xa6,
        0xab, 0xf7, 0x97, 0x66,
        0x76, 0x15, 0x13, 0x01
    };
    bytes output;
    bytes input;
	 AES::AES aes(AES_128, key); 
     aes.cipher(input, output);	 
     return 0;

}
