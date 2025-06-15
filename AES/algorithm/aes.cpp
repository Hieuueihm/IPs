#include <iostream>
#include "aes.hpp"

namespace AES {
	AES::AES(aes_type_e aes_type, bytes key){
		if(aes_type == AES_128){
			this->Nk = 4;
			this->Nr = 10;
			info("AES_128");
		} else if(aes_type == AES_192){
			this->Nk = 6;
			this->Nr = 12;
			info("AES_192");
		} else if(aes_type == AES_256){
			this->Nk = 8;
			this->Nr = 14;
			info("AES_256");

		} else {
			this->type_err = -1;
			error("Unexpected type");
		}
		if(this-> type_err != - 1) {
			this->key = key;
			info_hex_array(this->key, 16);


		}

	}
	void AES::rotWord(bytes b){
		unsigned char t = b[0];
		b[0] = b[1];
		b[1] = b[2];
		b[2] = b[3];
		b[3] = t;
	}
	void AES::subWord(bytes b){
		int i;
		 for (i = 0; i < 4; i++) {
		    b[i] = sbox[b[i] / 16][b[i] % 16];
		 }
	}


	void AES::rCon(bytes b, unsigned int n) {

		  b[0] = rConLUT[n];
		  b[1] = b[2] = b[3] = 0;
	}
	void AES::xorWord(bytes a, bytes b, bytes c){
		for(int i = 0; i < 4; i++){
			c[i] = a[i] ^ b[i];
		}
	}

	void AES::keyExpansion(){
		// wi wi+1 wi+2 wi+3
		// need to calculate wi+4 wi+5 wi+6 wi+7 from wi-> wi+3
		// wi+5 = wi+4 xor wi+1
		// wi+6 = wi+5 xor wi+2
		// wi+7 = wi+6 xor wi+3
		// wi+4 = wi xor g(wi+3)
		// g consists of 3 steps
		// 	rotword
		// 	subword
		//  Rcon (round constant )

		// for(int i = 0; i < Nk; i++){
		// 	for(int j = 0; j < 4; j++){
		// 		this->w[i * Nk + j] = this->key[i + j * Nk];
		// 	}
		// }
		for(int i = 0 ; i < 4 * Nk; i++){
			this->w[i] = this->key[i];
		}
		byte temp[4];
		byte rcon[4];

		// info("check initial round key");
		// info_hex_array(this->w, 16);
		// int i = 4 * Nk;
		// info(wordIndex);

		for(int i =  4 * Nk; i < (4 * (this->Nk) * (this->Nr + 1)); i +=  4){
				int wordIndex = i / 4;
				temp[0] = this->w[i - 4 + 0]; 
				temp[1] = this->w[i - 4 + 1]; 
				temp[2] = this->w[i - 4 + 2]; 
				temp[3] = this->w[i - 4 + 3];
			if(wordIndex % 4 ==0) {
				// info("wi4");
				this->rotWord(temp);
				// info_hex_array(temp, 4);
				this->subWord(temp);
				// info_hex_array(temp, 4);
				this->rCon(rcon, i / Nk / 4);
				// info_hex_array(rcon, 4);
				this->xorWord(temp, rcon, temp);
				// info_hex_array(temp, 4);

			}else if(this->Nk > 6 && (wordIndex % this->Nk == 4)){
				this->subWord(temp);
			}
			this->w[i + 0] = this->w[i - 4 * this->Nk] ^ temp[0];
		    this->w[i + 1] = this->w[i - 4 * this->Nk + 1] ^ temp[1];
		    this->w[i + 2] = this->w[i - 4 * this->Nk + 2] ^ temp[2];
		    this->w[i + 3] = this->w[i - 4 * this->Nk + 3] ^ temp[3];
		    // info("check word");
		    // info_hex_array_range(this->w, i, i + 4); 


			
		}
	
		for(int i = 0; i <= (this->Nr); i++){
			std::cout << "round " << i << " ";
			info_hex_array_range(this->w, i * 16, i * 16 + 16); 
		}

	}

	void AES::cipher(bytes input, bytes output){
		this->keyExpansion();
	}


}
