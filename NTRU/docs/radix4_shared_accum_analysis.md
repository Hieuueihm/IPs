# Phân tích radix-4 NTT và tích lũy dùng chung với FFT

Ngày 26/10/2026. Phân tích số nguyên chính xác và resource budget; **chưa có RTL/PPA
cho hai ứng viên mới**. Prototype ở [ntt_cluster.md](ntt_cluster.md) giữ nguyên làm baseline.

> Đây là phân tích ban đầu. Đã bổ sung [kết quả RTL reducer và radix-4](reducer_radix4_results.md)
> sau bước phân tích này; các mô tả “chưa có RTL/PPA” bên dưới phản ánh thời điểm ban đầu.

## 1. Kết luận để chọn thứ tự làm

1. **Ưu tiên reducer theo profile và chia sẻ phần cộng cuối trước.** q3329/q12289
   cho phép tính chính xác phần cao của m·q bằng mạng nhỏ hơn việc dựng cả số rộng.
   Đây là thay đổi cục bộ, có thể so với reducer hiện tại mà giữ kiến trúc butterfly.
2. **Radix-4 factor là ứng viên tiếp theo, chưa mặc định tốt hơn.** Nó thay bốn tích
   twiddle bằng ba tích twiddle + một tích hằng có reduction. Mảng FFT vẫn cần bốn
   multiplier; bố trí ba tích đồng thời cũng không khớp pipeline hai+hai hiện tại.
3. Chia sẻ compressor có cơ sở, nhưng phải định cỡ theo số lane và số toán hạng.
   Một cây64 bit không phục vụ đồng thời bốn reducer32 bit. Reduction vẫn phải
   đợi m; một ngân hàng cộng không được tính capacity hai lần trong cùng cycle.

## 2. Hướng 1: factor radix-4, chính xác ở đâu và tiết kiệm gì

### 2.1 Từ hai tầng CT đang có

Trên nhóm [x0,x1,x2,x3], tầng đầu dùng chung w cho các cặp (0,2),(1,3);
tầng sau dùng u,v cho các cặp (0,1),(2,3). Tất cả phép toán trong Z_q.

Nếu w=u² và v=c·u, c²=−1, đặt:

~~~text
t1 = x1*u
t2 = x2*u²
t3 = x3*u³
A = x0+t2; B = x0−t2
C = t1+t3; D = c*(t1−t3)
out = [A+C, A−C, B+D, B−D] mod q
~~~

Đó là cùng ánh xạ với hai tầng CT. Biến đổi ba tích đầu sang nhân với các root
đã encode Montgomery vẫn giữ kết quả canonical. u³R phải chuẩn bị từ root canonical
hoặc Mont(uR,u²R), không lấy (uR)³ rồi coi là u³R. Precompute nằm ngoài hot path.

Cấu trúc ba twiddle u,u²,u³ và một root bậc bốn có tiền lệ trong
[AtCoder Library convolution.hpp, nhánh 4-base](https://github.com/atcoder/ac-library/blob/master/atcoder/convolution.hpp#L79).
Đây là nguồn tham khảo số học phần mềm, không phải bằng chứng PPA phần cứng hoặc novelty.
Các đẳng thức/bound/kiểm tra dưới đây được phân tích riêng cho prototype hiện tại.

### 2.2 INTT và vị trí của tích hằng

Với root inverse u và ci=c^−1:

~~~text
A = x0+x1; B = x0−x1
C = x2+x3; D = ci*(x2−x3)
out = [A+C, u*(B+D), u²*(A−C), u³*(B−D)] mod q
~~~

Kết quả bằng hai tầng GS chưa normalization. Forward rồi inverse của một cặp
tầng cho 4*x mod q; normalization toàn kernel giữ nguyên. NTT đầy đủ vẫn N^−1;
ML-KEM N256 bảy tầng vẫn 128^−1, không thay thành 256^−1. Ba cặp radix-4 và
một tầng radix-2 phủ bảy tầng; BASEMUL chưa thuộc ứng viên này.

### 2.3 Tích hằng c không miễn phí

Với root orientation của bộ sinh trace hiện có và R=65536:

| q | Chiều | c | K=cR mod q | CSD của K | Số hạng dịch |
|---:|---|---:|---:|---|---:|
| 12289 | forward | 1479 | 4401 | 2^12 + 2^8 + 2^6 − 2^4 + 1 | 5 |
| 12289 | inverse | 10810 | 7888 | 2^13 − 2^8 − 2^6 + 2^4 | 4 |
| 3329 | forward | 1729 | 2571 | 2^11 + 2^9 + 2^4 − 2^2 − 1 | 5 |
| 3329 | inverse | 1600 | 758 | 2^10 − 2^8 − 2^3 − 2^1 | 4 |

Một cách hiện thực giữ representation: tạo T=x*K bằng shift-add chính xác, rồi
Montgomery-reduce T. Nó vẫn cần mạng 4–5 hạng và một reduction; tổng số lần
modular multiplication còn bốn, trong đó một được chuyên biệt hóa.
Root orientation khác có thể đổi c với −c; phải pin đúng context/reference.
Không lấy c làm K trực tiếp nếu gọi Montgomery trên data canonical.

| Thuộc tính | Hai tầng radix-2 hiện có | Radix-4 factor |
|---|---|---|
| Tích với twiddle thay đổi theo nhóm | 4 | 3 |
| Tích với hằng root bậc4 | 0 | 1, vẫn có reduction |
| Butterfly add/sub, chưa tính reducer | 8 | 8 |
| Root word cần truyền mỗi nhóm | 3 sau broadcast | 3, dùng u/u²/u³ |
| Data word vào/ra mỗi nhóm | 4/4 | 4/4 |
| Multiplier vật lý cần cho mode FFT32 | 4 | vẫn 4 nếu giữ capacity cũ |

Tiết kiệm có thể là ít demand cho multiplier tổng quát, hoặc đường nhân hằng nhỏ
hơn/nhanh hơn. Chưa có cơ sở gọi là giảm25% area, tăng33% throughput hay giảm
data thêm so với mode paired hiện tại. Twiddle cũng chưa giảm từ ba word xuống hai.

### 2.4 Khó khăn về pipeline

~~~text
Hiện tại:       2 general Mont → register → 2 general Mont
Factor forward: 3 general Mont → register → fixed-c Mont + recombination
Factor inverse: fixed-ci Mont  → register → 3 general Mont + recombination
~~~

Sơ đồ là dependency graph, không phải layout đã chốt. Ba multiplier trong một
stage không lấy được bằng cách bật thêm mode trên hai multiplier đang có ở stage
đó. Cần đổi vị trí leaf/register, chia sẻ đường pre/post, hoặc dùng nhiều lượt.
Một leaf rảnh trong mode NTT chưa tạo thêm throughput nếu không bổ sung đường
root, reducer và ghép nhóm phù hợp. Nếu dùng ba leaf trong mode NTT và bốn leaf
trong FFT, area bốn multiplier vẫn nằm trong core.

Chỉ chấp nhận ứng viên khi tính cả đường nhân hằng, pre/post add, buffer, CT/GS,
mode chuyển đổi và ảnh hưởng clock. Hợp đồng FFT R8 không đổi sang radix-4 vì
phép biến đổi trên NTT: FFT vẫn giữ từng rounding của ba real products.

## 3. Hướng 2A: compressor/CPA chia lane dùng chung

### 3.1 Phép cộng nhiều toán hạng thực sự chung

FFT32 raw từ bốn leaf16:

~~~text
P = p00 + (p01<<16) + (p10<<16) + (p11<<32) mod 2^64
~~~

Trong NTT q12289:

~~~text
m = low16((Tlow<<14) − (Tlow<<12) − Tlow)
S = T + (m<<14) − (m<<12) + m
~~~

Trong NTT q3329:

~~~text
m = low16((Tlow<<12) − (Tlow<<10) + (Tlow<<8) − Tlow)
S = T + (m<<12) − (m<<10) + (m<<8) + m
~~~

Cả FFT P và NTT S là weighted sum của nhiều word. Mạng 3:2 compressor có thể
giữ tổng dưới dạng hai word sum/carry, chỉ propagate carry ở CPA cuối. Các lượng
dịch là dây nối cố định theo profile; selector chọn nguồn operand cho fabric.
Không thay bằng barrel shifter toàn cục nếu chỉ có ít vị trí dịch cố định.

Số âm phải có sign extension/complement và bias +1 đúng. Model chèn bias vào
các bit thấp biết chắc bằng0 của một hạng dịch dương, nên không giấu một adder.

### 3.2 Capacity và độ rộng

| Kernel | Toán hạng đầu vào, đã tính bias | Lane an toàn | 3:2 compressor/lane, kiểu trực tiếp |
|---|---:|---:|---:|
| FFT32 raw | 4 | 64 bit | 2 |
| S cho q12289 | 4 | 32 bit, S cần30 | 2 |
| S cho q3329 | 5 | 32 bit, S cần28 | 3 |

Một fabric64 bit có thể là một lane64 FFT hoặc hai lane32 NTT. q3329 cần thêm
compressor so với mạng bốn operand của FFT, hoặc thêm bước pre-add riêng. Không
tính fabric64 bit đó thành bốn lane32. Đây là budget theo cấu trúc, không phải
GE: các bit0/hạng thưa sẽ được công cụ tối ưu riêng.

Ở NTT, carry của mỗi lane không được tràn sang lane kế. Ở FFT, carry phải đi
qua ranh giới khi ghép word rộng. Cắt carry chỉ ở boundary lane đã chọn; không
bỏ carry thấp trước khi lấy phần cao Montgomery hoặc phần fixed-point FFT.

### 3.3 Phụ thuộc và phạm vi chia sẻ

T phải có low16 đúng trước khi sinh m; sau đó mới cộng các hạng của S. Một fabric
không phục vụ đồng thời sinh m và tạo S cho cùng transaction. Nếu dùng lại theo
thời gian phải tính issue rate; nếu giữ pipeline II=1 thì cần đủ stage/instance.

Trong prototype hiện tại, phần ghép FFT nằm ở compute stage sau; reducer NTT có
ở cả hai stage. Chia sẻ cây stage sau không tự xóa được reducer stage đầu.
Nối m phụ thuộc trở lại đầu vào mà không có register sẽ tạo đường tổ hợp dài.

Phần chung đáng thử: nguồn multiplier, compressor cục bộ, CPA chia lane và một
phần ALU. Phần vẫn chuyên biệt: sinh m, correction mod q, chọn bit/rounding FFT.
Butterfly A±T vẫn cần capacity riêng sau reduction; không tính lại cùng CPA vào
hai công việc đang diễn ra trong cùng cycle.

## 4. Hướng 2B: rút gọn Montgomery theo profile trước khi ép chia sẻ

Đây là ứng viên có mức thay đổi cục bộ nhỏ hơn full compressor fabric.
Hai q có dạng q=k*2^a+1, với (k,a)=(3,12) hoặc (13,8), 2a>=16.
Đặt R=2^16, lo=T mod R, hi=T>>16. Khi đó:

~~~text
qprime = −q^−1 mod R = k*2^a−1
s = 16−a
m = (((k*(lo mod 2^s))<<a) − lo) mod R
m = H*2^s + L
high_mq = k*H + (((k*L<<a)+m)>>16)
u = hi + high_mq + (lo != 0)
out = u−q nếu u>=q, ngược lại u
~~~

Chứng minh carry cuối: mq mod R = −lo mod R, nên lo+(mq mod R) bằng0 nếu lo=0,
bằngR nếu lo!=0. Vì vậy carry từ nửa thấp là **bit (lo!=0)**. Đây là tính carry
chính xác, không phải bỏ nửa thấp. Công thức high_mq xuất phát trực tiếp từ:

~~~text
m*q = k*H*R + (k*L<<a) + m
~~~

| q | H | L | Mạng tính carry từ (kL<<a)+m | high_mq | u trước correction |
|---:|---:|---:|---:|---:|---:|
| 12289 | 12 bit | 4 bit | 18 bit | 14 bit | <=14593, cần14 bit |
| 3329 | 8 bit | 8 bit | 20 bit | 12 bit | <=3498, cần12 bit |

Bound u dùng input canonical: hi<=floor((q−1)^2/R), high_mq<=q−1,
carry<=1. Cả hai cho u<2q, nên một correction là đủ. M vẫn16 bit; không gọi
toàn reducer là14/12 bit vì còn mạng carry18/20 bit và sinh m.

Cách này tránh dựng toàn bộ S30/28 rồi mới lấy upper16. Phần cộng u và correction
có thể đặt lên các lane16 của ALU dùng chung. Các mạng nhỏ kH/kL/carry vẫn cần
định cỡ và đo; không suy area giảm tỷ lệ30/14 hay28/12. Full compressor và compact
reducer là hai ứng viên cạnh tranh, không mặc định ghép cả hai sẽ tốt hơn.

Chỉ áp dụng hai profile trên và input canonical. Chưa mở rộng cho q8380417,
prime32 bit tùy ý hoặc lazy ranges. Cần fallback phù hợp nếu giữ các mục tiêu đó.

## 5. Kiểm tra đã chạy

[Model](../model/radix4_shared_accum.py), [JSON](../study/results/radix4_shared_accum.json).

- 5 160 nhóm từ các stage CT/GS thực tế của bộ sinh trace hiện tại: kiểm quan hệ
  root, factor canonical và factor Montgomery đều khớp hai tầng radix-2.
- Mỗi q duyệt **65 536 giá trị m** cho công thức high_mq, và **65 536 lo** cho
  công thức sinh m. Tất cả khớp phép nhân nguyên/định nghĩa Montgomery.
- Exhaust toàn bộ x trong [0,q) cho cả c và ci: 31 236 trường hợp shift-add +
  Montgomery, khớp x*c mod q. Bao gồm correction của các hạng âm.
- Mỗi q 5 016 cặp biên/random: reducer compact, cộng S bằng CSA, hai lane32 độc
  lập trong fabric64, forward/inverse factor và roundtrip đều khớp.
- 5 016 tích FFT32 signed qua compressor64 khớp tích đầy đủ; không thay rounding.
- Negative controls phát hiện: bỏ carry (lo!=0), dùng c chưa encode trong
  Montgomery, và để carry của compressor/CPA tràn sang lane kế.

Không có sai khác. Đây là kiểm model; chưa là RTL, timing hay full C differential.
Kết quả số đo GE của prototype cũ không được chuyển sang hai ứng viên mới.

## 6. Thí nghiệm RTL nên làm sau phân tích

Giữ nguyên mảng nhân và butterfly trước, so ba reducer: mạng hiện tại; weighted
sum CSA; compact high-mq. So cả q cố định và runtime hai profile, cùng contract,
pipeline/II, rồi đo mux/register/CPA chia lane khi dùng chung với FFT.

Sau khi có reducer phù hợp, so hai tầng radix-2 với radix-4 factor có đầy đủ
nhân hằng, CT/GS và đường FFT giữ capacity. Không dựng full transform scheduler
để trả lời câu hỏi số học này. Không thêm speedup từ các phần đã bị cùng một
băng thông hay stage chi phối.
