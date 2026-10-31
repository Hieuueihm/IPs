# 01 — Số học và thuật toán cấp kernel

Định dạng 0–3 và profile 0–1 **giữ nguyên như [01 của bản 1.0](../1.0/01_numeric_kernels.md)**: FFT theo bản
chuẩn ký FN-DSA (làm tròn nửa-lên, nhân phức 3 tích, FFT ngược chia ở cuối); NTT 16 bit với Montgomery R = 2¹⁶.
Tài liệu này chỉ định nghĩa phần mới.

Mọi mã giả dưới đây đã được chạy lại bằng Python và cho kết quả trùng với vector chuẩn
([scripts/check_spec2_kernel_assets.py](../../../scripts/check_spec2_kernel_assets.py)).

## 1. Nhắc lại cách tính ở cấp tile

Mọi phép nhân modulo và butterfly cấp kernel dùng đúng định nghĩa của [hợp đồng tile](10_hop_dong_tile.md), mục 4.5.
Mỗi request của tile là đúng một butterfly hoặc một phép nhân modulo (mục 4.6 của hợp đồng đó). Kết quả kernel không
phụ thuộc thứ tự phát các butterfly trong một tầng, vì chúng độc lập nhau. (Cách gom nhịp hai tầng của [03](03_bo_nho.md)
thuộc hợp đồng tile trước và chưa được cập nhật.)

## 2. FFT 64 bit theo NTRUGen (định dạng 5)

Bản chuẩn: `vect_FFT` / `vect_iFFT` trong `ng_fxp.c` của NTRUGen đi kèm bản FN-DSA đã ghim, build `NTRUGEN_AVX2 = 0`.

### 2.1 Phép cơ sở

Mọi giá trị là số có dấu 64 bit. `wrap64` lấy mod 2⁶⁴ rồi hiểu theo bù hai. `>>` là dịch số học.

```text
cộng(a, b) = wrap64(a + b);   trừ(a, b) = wrap64(a − b)
nhân(a, b) = wrap64( floor(a·b / 2^32) )          // CẮT BỚT, không cộng 2^31
nửa(v)     = wrap64(v + 1) >> 1                    // cộng 1 (quay vòng) rồi dịch phải 1
nhân phức(s, y):                                    // 3 tích, đúng thứ tự này
    z0 = nhân(s.re, y.re);  z1 = nhân(s.im, y.im)
    z2 = nhân(cộng(s.re, s.im), cộng(y.re, y.im))
    re = trừ(z0, z1);       im = trừ(trừ(z2, z0), z1)
```

Ở phần cứng, `nhân` là cửa sổ bit [95:32] của tích 128 bit, **hằng làm tròn bằng 0**. Đây là cùng bộ trích cửa sổ
với định dạng 1, chỉ khác hằng.

### 2.2 Bảng root

[assets/fft_ntrugen_q32_32.mem](assets/fft_ntrugen_q32_32.mem): 1 024 dòng, mỗi dòng 128 bit, `[127:64]` phần thực,
`[63:0]` phần ảo. Chép nguyên bit từ `GM_TAB` của `ng_fxp.c`; **không** suy ra từ bảng Q64.64 bằng làm tròn. Không lấy
liên hợp trước: FFT ngược tự đổi dấu phần ảo.

### 2.3 Cách đặt dữ liệu

Giống định dạng 1 của 1.0: N phần tử 64 bit, `a[0 : N/2]` là phần thực, `a[N/2 : N]` là phần ảo; phần tử i chiếm 4 ô
16 bit liên tiếp, ô thấp trước.

### 2.4 Thuật toán

N = 2^logn, logn = 1..10, hn = N/2. Với logn = 1 cả hai phép là đồng nhất.

```text
FFT:
    t = hn
    với lm = 1 .. logn−1:
        m = 2^lm;  ht = t/2
        với i = 0 .. m/2 − 1:
            s = GM[m + i]
            với j = i·t .. i·t + ht − 1:
                x = (a[j], a[j+hn]);  y = nhân phức(s, (a[j+ht], a[j+ht+hn]))
                (a[j], a[j+hn])           = (cộng(x.re, y.re), cộng(x.im, y.im))
                (a[j+ht], a[j+ht+hn])     = (trừ(x.re, y.re),  trừ(x.im, y.im))
        t = ht

FFT ngược:
    ht = 1
    với lm = logn−1 xuống 1:
        m = 2^lm;  t = 2·ht
        với i = 0 .. m/2 − 1:
            s = liên hợp(GM[m + i])                            // đổi dấu phần ảo, quay vòng
            với j = i·t .. i·t + ht − 1:
                x = (a[j], a[j+hn]);  y = (a[j+ht], a[j+ht+hn])
                (a[j], a[j+hn])           = (nửa(cộng(x.re, y.re)), nửa(cộng(x.im, y.im)))
                (a[j+ht], a[j+ht+hn])     = nhân phức(s, (nửa(trừ(x.re, y.re)), nửa(trừ(x.im, y.im))))
        ht = t
    // KHÔNG có bước chia ở cuối
```

Khác định dạng 1 ở ba điểm:
1. Phép nhân cắt bớt.
2. Chia đôi cả hai nhánh ở **mọi** tầng, trước phép nhân, theo kiểu số có dấu.
3. Dùng bảng root riêng.

Lịch chỉ số (thứ tự tầng, cặp phần tử, chỉ số root) trùng FFT của định dạng 0–2, nên dùng chung bộ sinh địa chỉ.

## 3. NTT 32 bit, q = 8380417 (profile 2)

### 3.1 Hằng số

| Hằng | Giá trị |
|---|---:|
| q | 8 380 417 |
| R | 2³² |
| q′ = −q⁻¹ mod R | 4 236 238 847 |
| R mod q | 4 193 792 |
| R² mod q (dùng cho phép 0x7) | 2 365 951 |
| ψ (căn nguyên thủy bậc 512) | 1 753 |
| Hệ số cuối NTT ngược, R·256⁻¹ mod q | 16 382 |

### 3.2 Bảng root

[assets/ntt_q8380417_forward.mem](assets/ntt_q8380417_forward.mem) và
[assets/ntt_q8380417_inverse.mem](assets/ntt_q8380417_inverse.mem), 256 dòng 32 bit:

```text
GM[k]  = R · ψ^(đảo_bit_8(k))  mod q
IGM[k] = R · ψ^(−đảo_bit_8(k)) mod q
```

Thứ tự GM trùng bảng `zetas` của bản chuẩn ML-DSA (Dilithium), nhưng Dilithium giữ giá trị có dấu và không rút gọn đủ.
Ở đây mọi giá trị nằm trong [0, q).

### 3.3 Thuật toán

N = 256. Cách đặt: hệ số i của đa thức j ở ô 16 bit `2(j·N + i)` (nửa thấp) và `2(j·N + i) + 1` (nửa cao).

```text
NTT:          vòng lặp NTT của 1.0 mục 01.7 với GM ở trên, Mont với R = 2^32, minimum_stride = 1
NTT ngược:    vòng lặp INTT của 1.0 mục 01.7 với IGM ở trên; cuối cùng a[i] = Mont(a[i], 16 382)
phép 0x7:     a[i] = Mont(a[i], 2 365 951)  = a[i]·R mod q
phép 0x8:     a[i] = Mont(A[i], B[i])
```

Kết quả NTT ở vị trí j bằng a(ψ^(2·đảo_bit_8(j) + 1)) mod q. Bộ kiểm dùng chính tính chất này làm phép kiểm độc lập.

## 4. NTT modulo prime 31 bit đã nạp (profile 3)

Bản chuẩn: `mp_NTT`, `mp_iNTT`, `mp_mkgmigm` trong `ng_mp31.c` của NTRUGen.

### 4.1 Prime và hằng số

Do phép nạp prime cung cấp ([02](02_giao_dien.md)):
- p lẻ, 3 ≤ p < 2³¹;
- p0i = −p⁻¹ mod 2³² (chính là q′);
- R² mod p với R = 2³² (trong NTRUGen gọi là R2);
- logn của bảng;
- hai bảng gm, igm, mỗi bảng N số 32 bit.

Với các prime của bảng `PRIMES` trong NTRUGen:

```text
gm[đảo_bit_logn(u)]  = g_N^u · R mod p
igm[đảo_bit_logn(u)] = (1/2) · g_N^(−u) · R mod p          // đã gộp hệ số 1/2
g_N = căn nguyên thủy bậc 2N (g của PRIMES bình phương 10 − logn lần)
```

Lõi không tính lại các bảng này; nó dùng đúng giá trị host nạp.

### 4.2 Thuật toán

```text
NTT:        giống NTT của mục 3.3 với GM = gm (N = 2^logn)
NTT ngược:  stride = 1
            khi stride ≤ N/2:
                groups = N / (2·stride)
                với g = 0 .. groups − 1, off = 0 .. stride − 1:
                    i = 2·g·stride + off;  j = i + stride
                    s = (a[i] + a[j]) mod p;  d = (a[i] − a[j]) mod p
                    a[i] = (s + (s lẻ ? p : 0)) / 2           // chia đôi modulo, MỌI tầng
                    a[j] = Mont(d, igm[groups + g])
                stride = 2·stride
            // KHÔNG nhân hệ số ở cuối
phép 0x7:   a[i] = Mont(a[i], R² mod p)
phép 0x8:   a[i] = Mont(A[i], B[i])
```

Trong khối tile, phép này là chế độ 4 GS với `cfg_halve = 1`.

## 5. Miền giá trị

- Như 1.0: hệ số và root của NTT phải nằm trong [0, q). Host chịu trách nhiệm; lõi không cam kết kết quả nếu vi phạm.
- FFT các định dạng không bão hòa, không báo tràn; mọi phép quay vòng như mô tả.
