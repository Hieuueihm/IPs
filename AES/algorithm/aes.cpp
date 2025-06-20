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


	void AES::rCon(bytes b, int n) {

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
	
		// for(int i = 0; i <= (this->Nr); i++){
		// 	std::cout << "round " << i << " ";
		// 	info_hex_array_range(this->w, i * 16, i * 16 + 16); 
		// }

	}
	void AES::addRoundKey(int leftIndex, int rightIndex, bytes b, int roundIndex){
		// bytes temp;
		// temp = b;		
		// info(leftIndex - roundIndex * (4 * this->Nk))
		// info(rightIndex - roundIndex * (4 * this->Nk))
		for(int i = leftIndex ; i < rightIndex; i++){

			// info_hex(b[i - roundIndex * (4 * this->Nk)])
			// info_hex(this->w[i])
			// std::cout << std::endl;
			b[i - roundIndex * (4 * this->Nk) ] = (b[i - roundIndex * (4 * this->Nk)]^(this->w[i]));

		}

	}
	void AES::subBytes(bytes b){
		for(int i = 0;i < (4 * this->Nk); i++){
			b[i] = sbox[b[i] / 16][b[i] % 16];
		}
	}
	void AES::shiftRows(bytes b){
		uint8_t state[4][(this->Nk)];
		for (int col = 0; col < this -> Nk; ++col) {
	        for (int row = 0; row < 4; ++row) {
	            state[row][col] = b[col * 4 + row];

	        }
    	}
    	// for (int row = 0; row < 4; ++row) {
        // for (int col = 0; col < 4; ++col) {
        //     std::cout << std::hex << std::setw(2) << std::setfill('0') 
        //               << (int)state[row][col] << " ";
        // }
        // std::cout << std::endl;
    	// 	}
    	// 	std::cout << std::endl;
         uint8_t temp;

	    // Shift row 1 (dịch trái 1 lần)
	    temp = state[1][0];
	    state[1][0] = state[1][1];
	    state[1][1] = state[1][2];
	    state[1][2] = state[1][3];
	    state[1][3] = temp;

	    std::swap(state[2][0], state[2][2]);
    	std::swap(state[2][1], state[2][3]);

    	temp = state[3][3];
	    state[3][3] = state[3][2];
	    state[3][2] = state[3][1];
	    state[3][1] = state[3][0];
	    state[3][0] = temp;

    	// for (int row = 0; row < 4; ++row) {
        // for (int col = 0; col < 4; ++col) {
        //     std::cout << std::hex << std::setw(2) << std::setfill('0') 
        //               << (int)state[row][col] << " ";
        // }
        // std::cout << std::endl;
    	// }
	    for (int col = 0; col < this -> Nk; ++col) {
	        for (int row = 0; row < 4; ++row) {
	            b[col * 4 + row] = state[row][col];
	        }
	    }
    

	}
	byte xtime(byte x) {
	    return (x << 1) ^ ((x & 0x80) ? 0x1b : 0x00);
	}


	void AES::mixColumns(bytes b){
		for(int i = 0 ; i < (this-> Nk); i++){
			byte a = b[i * this -> Nk];
			byte bx = b[i * this -> Nk + 1];
			byte c = b[i * this -> Nk + 2];
			byte d = b[i * this -> Nk + 3];

				// info("inpt")
		        // info_hex(a)
		        // info_hex(bx);
		        // info_hex(c);
		        // info_hex(d);

		    byte t0 = xtime(a) ^ (xtime(bx) ^ bx) ^ c ^ d;
		    byte t1 = a ^ xtime(bx) ^ (xtime(c) ^ c) ^ d;
		    byte t2 = a ^ bx ^ xtime(c) ^ (xtime(d) ^ d);
		    byte t3 = (xtime(a) ^ a) ^ bx ^ c ^ xtime(d);

		        // info("outp")
		        // info_hex(t0)
		        // info_hex(t1);
		        // info_hex(t2);
		        // info_hex(t3);


		    b[i * this -> Nk] = t0;
		    b[i * this -> Nk + 1] = t1;
		    b[i * this -> Nk + 2] = t2;
		    b[i * this -> Nk + 3] = t3;

		}
		// info_hex_array(bx, 16);


	}

	int8_t AES::cipher(bytes input, bytes output){	
		if(this->type_err == -1){
			return -1;
		}
		this->keyExpansion();

		// add round key
		byte b[4 * (this->Nk)];
		for(int i = 0; i < (4 * this->Nk); i++){
			b[i] = input[i];
		}

		this->addRoundKey(0, (4 * this->Nk), b, 0);

		// info_hex_array(b, 16);
		int i;
		for(i =  1; i < (this -> Nr); i++){

			subBytes(b);
			// info_hex_array(b, 16);
			shiftRows(b);
			//info_hex_array(b, 16);
			mixColumns(b);
			// info_hex_array(b, 16);
			// std::cout << std::endl;
			addRoundKey(i * (4 * this->Nk), ((i * (4 * this->Nk)) + (4 * this->Nk)), b, i);


			// info_hex_array(b, 16);
		}


		// Nr round


		// subBytes
		subBytes(b);

		// shiftRows
		shiftRows(b);

		// add round key
		addRoundKey(i * (4 * this->Nk), ((i * (4 * this->Nk)) + (4 * this->Nk)), b, i);
		info_hex_array(b, 16);




		return 0;
	}


}
