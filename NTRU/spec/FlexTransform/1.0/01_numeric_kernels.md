# 01 — Normative numeric and kernel contract

## 01.1 Các phép cơ sở FFT

`W∈{32,64,128}`, `F=W/2`. `wrap_W(x)` lấy residue modulo 2^W rồi diễn giải
signed two's complement. Nhân và phép cộng bias ở vế phải dưới đây dùng số
nguyên đủ rộng trước khi áp dụng wrap được chỉ rõ. `floor` làm tròn về −∞.

```text
add(a,b) = wrap_W(a+b)
sub(a,b) = wrap_W(a-b)
mul(a,b) = wrap_W(floor((a*b + 2^(F-1)) / 2^F))
div2e(a,0) = a
div2e(a,s>0) = signed(wrap_W(a + 2^(s-1))) >>> s
```

Nhân round-nearest/ties toward +∞; không phải ties-to-even hoặc toward-zero.
`div2e` wrap **trước** arithmetic shift. Không saturate. Mọi output có đúng W
bit; không phát thêm flag overflow có ảnh hưởng số học. (FT-NUM-001..004)

```text
cmul(ar,ai,br,bi):
    p0 = mul(ar,br)
    p1 = mul(ai,bi)
    p2 = mul(add(ar,ai),add(br,bi))
    re = sub(p0,p1)
    im = sub(sub(p2,p0),p1)
```

Mỗi real product round riêng. MUST NOT dùng 4M, dời rounding ra sau complex
combine, mở rộng pre-add không wrap hoặc dùng phép tính float. Lưu ba product
theo context/lane; chưa đủ triplet thì không được retire. (FT-NUM-005)

## 01.2 Limb fusion

Tách operand thành limb 32 bit; limb thấp unsigned, chỉ limb cao nhất signed.
Từng raw product có container ít nhất 65 bit để chứa cả unsigned32×unsigned32.
Bên trong raw32×32, dùng cùng quy tắc sign cho half16. Không sign-extend limb
thấp dựa trên bit31 của chính limb thấp. (FT-NUM-006)

| W | Số limb32 | Độ rộng giữ A=W+F | Bias | Slice output |
|---:|---:|---:|---:|---|
| 32 | 1 | 48 | 2^15 | [47:16] |
| 64 | 2 | 96 | 2^31 | [95:32] |
| 128 | 4 | 192 | 2^63 | [191:64] |

```text
acc = sum(raw(a_i*b_j) << (32*(i+j))) mod 2^A
rounded = (acc + 2^(F-1)) mod 2^A
out_bits = rounded[A-1:F]
```

MUST giữ carry từ vùng thấp vào slice. Term có trọng số >=A đóng góp zero
modulo 2^A và MAY bỏ exact. Không round/truncate mỗi partial product tùy ý.
Container raw65 phải được sign-extend đúng trước shift khi là tích âm.
(FT-NUM-007)

## 01.3 FFT root table

Authority: [assets/fft_q64_64.mem](assets/fft_q64_64.mem), 1024 row, mỗi row
256 bit `[255:128]=real`, `[127:0]=imag`, lấy nguyên bit từ R8 commit
`ad1e5bf7714d53230ad457364db8a46a1b459c94`. Row index là root index, không
tái tạo bằng sin/cos hoặc float. SHA256 ở manifest. (FT-NUM-008)

Forward chọn `(wr,wi)`. Inverse tạo `(wr,wrap128(-wi))` ở Q64.64 trước khi
quantize sang W thấp. Với W<128, `d=64-F`:

```text
Q_W(x) = wrap_W(floor((signed128(x) + 2^(d-1)) / 2^d))
```

W128 dùng nguyên word. Tổng root cho phase2 được tạo bằng `add(wr_W,wi_W)`
sau quantization, không quantize một tổng Q64.64 để thay thế. (FT-NUM-009)

## 01.4 FFT layout và thuật toán

N word component lưu split-real/imag: `a[0:hn]` real, `a[hn:N]` imag,
`hn=N/2`. Đây là N component biểu diễn N/2 complex, không phải N complex.
Không thêm bit reversal ở đầu/cuối. Với N=1 hoặc 2, FFT/IFFT là identity.

```text
FFT, logn>=2:
    span=hn; groups=2
    while span>=2:
        half=span/2
        for g=0 .. groups/2-1:
            root=GM[groups+g]
            for off=0 .. half-1:
                j=g*span+off
                A=(a[j], a[j+hn])
                B=(a[j+half], a[j+half+hn])
                T=cmul(B,root)
                (a[j],a[j+hn])=A+T   # componentwise add()
                (a[j+half],a[j+half+hn])=A-T
        span=half; groups*=2

IFFT, logn>=2:
    stride=1; groups=N
    while groups>2:
        for g=0 .. groups/4-1:
            root=conj(GM[groups/2+g])
            for off=0 .. stride-1:
                j=2*g*stride+off
                A=(a[j],a[j+hn]); B=(a[j+stride],a[j+stride+hn])
                (a[j],a[j+hn])=A+B
                (a[j+stride],a[j+stride+hn])=cmul(A-B,root)
        stride*=2; groups/=2
    for i=0 .. N-1: a[i]=div2e(a[i],logn-1)
```

All component adds/subtracts use wrap. IFFT scaling MAY fuse with final write
if it gives exactly the same per-component output; never scale each stage.
Các butterfly trong một tầng có thể reorder vì disjoint destination, nhưng
tầng sau phải thấy toàn bộ output tầng trước đã commit. (FT-KER-001..002)

## 01.5 CMUL / SPLIT / MERGE

CMUL: cho j=0..hn−1, output A[j],A[j+hn] là
`cmul(A[j],A[j+hn],B[j],B[j+hn])`. B không đổi. (FT-KER-003)

SPLIT: `qn=N/4`, input A length N; C chứa f0 length hn rồi f1 length hn.
N=2: `C[0]=A[0]`, `C[1]=A[1]`. Với N>=4:

```text
for j=0 .. qn-1:
    X=(A[2*j],A[2*j+hn]); Y=(A[2*j+1],A[2*j+1+hn])
    S=componentwise add(X,Y); D=componentwise sub(X,Y)
    f0[j]=div2e(S.re,1); f0[j+qn]=div2e(S.im,1)
    T=cmul(D,conj(GM[j+hn]))
    f1[j]=div2e(T.re,1); f1[j+qn]=div2e(T.im,1)
C = concatenate(f0,f1)
```

MERGE: A=f0 length hn, B=f1 length hn, output C length N.
N=2: `C[0]=A[0]`, `C[1]=B[0]`. Với N>=4:

```text
for j=0 .. qn-1:
    K=(A[j],A[j+qn])
    T=cmul(B[j],B[j+qn],GM[j+hn])
    (C[2*j],C[2*j+hn]) = K+T
    (C[2*j+1],C[2*j+1+hn]) = K-T
```

SPLIT/MERGE không ghi đè input A/B; dùng C để tránh alias. (FT-KER-004..005)

## 01.6 NTT modular primitives và domain

q theo profile, R=65536. Coefficient, root và kết quả primitive đều canonical
0<=x<q. Không có lazy residue, signed residue hoặc input không canonical trong
contract v1.0. Host chịu trách nhiệm valid range; checker phần cứng MAY thêm,
nhưng không được dựa vào việc checker tồn tại. Output ngoài domain không có
cam kết nếu input vi phạm domain. (FT-NUM-010)

| q | qprime=−q^−1 mod R | R mod q | R² mod q |
|---:|---:|---:|---:|
| 12289 | 12287 | 4091 | 10952 |
| 3329 | 3327 | 2285 | 1353 |

```text
addq(a,b) = (a+b >= q) ? a+b-q : a+b
subq(a,b) = (a>=b) ? a-b : a-b+q
Mont(a,b):
    T=a*b                        # full unsigned product
    m=(T*qprime) mod R
    u=(T+m*q)/R                  # exact integer division, low16 must be zero
    return (u>=q) ? u-q : u
```

Canonical operands imply T<q²<qR, hence u<2q; one subtraction is enough.
Implementation MAY dùng compact/CSA/shift-add equivalent, nhưng MUST giữ đúng
carry, input domain và canonical output. Không dùng rule cắt tích FFT để cắt
T của Montgomery. (FT-NUM-011..012)

`wbar = wR mod q`. CT: `t=Mont(B,wbar)`, out `(addq(A,t),subq(A,t))`.
GS: `s=addq(A,B)`, `d=subq(A,B)`, out `(s,Mont(d,wbar))`.
Butterfly không tự đổi representation của coefficient; root đã encoded R
làm cho multiplication tương đương nhân root thường. (FT-NUM-013)

## 01.7 NTT roots, order và normalization

Assets `ntt_q{q}_{forward,inverse}.mem` lưu scalar rootbar 16 bit/index.
Profile0 có 1024 root từ C R8; profile1 có 128 root:
`GM[k]=R*17^bitreverse7(k) mod3329`, inverse dùng nghịch đảo của root thường
rồi nhân R. Không lấy nghịch đảo trực tiếp giá trị Montgomery. (FT-NUM-014)

```text
NTT:
    stride=N/2; groups=1
    minimum_stride=2 if q==3329 and N==256 else 1
    while stride>=minimum_stride:
        for g=0 .. groups-1:
            for off=0 .. stride-1:
                i=2*g*stride+off; j=i+stride
                (a[i],a[j])=CT(a[i],a[j],GM[groups+g])
        stride/=2; groups*=2

INTT:
    stride=minimum_stride
    while stride<=N/2:
        groups=N/(2*stride)
        for g=0 .. groups-1:
            for off=0 .. stride-1:
                i=2*g*stride+off; j=i+stride
                (a[i],a[j])=GS(a[i],a[j],IGM[groups+g])
        stride*=2
    L=logn-1 if q==3329 and N==256 else logn
    factorbar=R*inverse_mod(2^L,q) mod q
    for i=0 .. N-1: a[i]=Mont(a[i],factorbar)
```

INTT dùng root inverse **và** final normalization; không dùng root thuận để
thay GS. Forward output giữ thứ tự do các loops này tạo; không reorder thành
natural frequency order. Inverse nhận đúng order đó. (FT-KER-006..007)

TOMONT: `out=Mont(x,R² modq)=xR modq`.
MODMUL: `out=Mont(A,B)=ABR^−1 modq`; không phải phép nhân thường AB modq.
Muốn normal-domain product từ A,B cần caller tổ chức TOMONT/domain riêng.
Không gọi MODMUL là BASEMUL q3329. (FT-KER-008..009)

## 01.8 Một/two-layer tile contract

NTT vector input x0..x3, root bundle low-to-high `[w_common,w0,w1]`:

- CT pair: BF(x0,x2,common), BF(x1,x3,common), giữ natural coefficient
  order; rồi BF(y0,y1,w0), BF(y2,y3,w1).
- GS pair: BF(x0,x1,w0), BF(x2,x3,w1), giữ coefficient order;
  rồi BF(y0,y2,common), BF(y1,y3,common).
- Tail CT: BF(x0,x2,w0), BF(x1,x3,w1), output đúng vị trí x0..x3.
  Tail GS: BF(x0,x1,w0), BF(x2,x3,w1), output đúng vị trí x0..x3.
  Hai root low-to-high là [w0,w1]. Chỉ tầng đầu; bypass có cùng valid/context
  và không bị thay bằng output tầng hai. Intermediate không ghi coefficient RAM.

Mode scalar có bốn BF độc lập/tile trên tám word, có thể dùng `(0,a)` để lấy
Mont(a,b) từ output tổng. NTT paired/tail giữ toàn bộ bốn output word/tile.
Mỗi job MUST giữ riêng bộ chỉ số và root schedule. (FT-KER-010)
