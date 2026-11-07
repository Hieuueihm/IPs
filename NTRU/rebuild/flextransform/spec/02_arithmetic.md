# 02 — Contract số học bắt buộc

Không đổi contract để làm PPA đẹp hơn. Các công thức sau là semantics; RTL có thể phân cột/pipeline nhưng phải cho đúng bit pattern.

## 1. Kiểu số và phép cơ sở

`wrapW(x)` lấy x mod 2^W rồi diễn giải signed two's-complement. FFT thường W=32/64/128, F=W/2. Cộng/trừ wrap W bit; không saturation.

```text
mulW(a,b) = wrapW(floor((a*b + 2^(F-1)) / 2^F))
div2eW(v,s) = v                           nếu s=0
              wrapW(v + 2^(s-1)) >>> s    nếu s>0
```

`>>>` là dịch phải số học trên kết quả **đã wrap**. Nhân làm tròn ties toward +infinity, không ties-to-even. Dữ liệu thấp là limb unsigned; chỉ limb cao nhất có dấu. Số âm chia làm tròn theo công thức, không dùng phép chia integer có convention khác.

## 2. FFT/IFFT thường

Một số phức có re/im W bit; host lưu re[0..N/2-1], rồi im[0..N/2-1]. Nhân phức:

```text
p0 = mulW(ar,wr)
p1 = mulW(ai,wi)
p2 = mulW(wrapW(ar+ai), wrapW(wr+wi))
t.re = wrapW(p0-p1)
t.im = wrapW(p2-wrapW(p0+p1))
```

CT thuận: `z0=A+t`, `z1=A−t`, t=B·w. GS nghịch: side=A+B, diff=A−B, t=diff·w_inv, output=(side,t). Mọi cộng/trừ thực/ảo theo wrapW.

IFFT thường chia cuối với s=max(logn−1,0). Đường host-read thực hiện div2e; RAM nội bộ giữ kết quả trước normalize. FFT logn0/1 không có tầng butterfly; s=0, identity theo layout phần mềm.

FFT128 phải khớp R8 commit `ad1e5bf7714d53230ad457364db8a46a1b459c94`, LP64, FALCON_FPR_MODE=2. FFT32/64 thường theo oracle fixed-point của project, không phải chứng nhận dùng được thay precision R8 trong signer.

## 3. Tích thực đa limb

| W | L | Tích32×32 / real product | Tích32×32 / complex multiply |
|---:|---:|---:|---:|
| 32 | 1 | 1 | 3 |
| 64 | 2 | 4 | 12 |
| 128 | 4 | 15 | 45 |

W128 chỉ bỏ hạng a3*b3 bắt đầu tại bit192, ngoài cửa sổ output [191:64]. Không bỏ cột thấp: chúng tạo carry và rounding. NTT phải lấy product đầy đủ, không dùng cách cắt này.

Accumulator signed68 cộng từng fused65 sign-extended; shift cố định32 khi kết thúc cột. Seed rounding một lần/product: 2^15, 2^31, 2^63 cho W32/64/128. Không seed lại mỗi limb output.

## 4. Native NTRUGen64

Đây là mode riêng, W64 F32:

```text
native_mul(a,b) = wrap64((signed64(a)*signed64(b)) >>> 32)
native_half(v)  = wrap64(v+1) >>> 1
```

3M vẫn wrap các tổng input và output. Native inverse thực hiện native_half trên **cả sum và difference của re/im trước nhân** tại từng tầng GS. Không có scale cuối trên host. Seed accumulator native bằng0; không dùng rounding seed FFT64 thường.

Root native lấy từ asset C đã khóa. Không sinh lại từ float sin/cos. Độ trễ qua half/native alignment phải có trong manifest pipeline.

## 5. Montgomery scalar và packed

Với w=32 hoặc16, R=2^w, q lẻ, qinv=−q⁻¹ mod R, 0≤a,b<q:

```text
T  = a*b                    // đủ 2w bit
m  = low_w(T)*qinv mod R
P  = m*q                    // đủ 2w bit
u  = high_w(T)+high_w(P)+(low_w(T)!=0) // w+1 bit
z  = u>=q ? u-q : u
```

q<2^(w−1) bảo đảm domain/range dùng trong datapath và correction. Scalar q<2³¹; packed q<2¹⁵. NZ(low T) là OR-reduction; không bỏ carry này. Với packed, hai lane cộng/correction riêng: không cho carry/borrow chạy qua biên16.

CT: `t=Mont(y,root); z0=(x+t) mod q; z1=(x−t) mod q`.

GS với convention INTT của project:

```text
s=(x+y) mod q
d=(x−y) mod q
z0=(s+(s odd ? q : 0)) >> 1
z1=Mont(d, inverse_root)
```

Inverse root **đã chứa hệ số 1/2 trong miền Montgomery**. Không half z1 thêm lần nữa; không normalize 1/N thêm ở host. Phép half modular là unsigned có bit mở rộng.

## 6. Root và miền dữ liệu

Đặt B=2^hmin, M=N/B. Với prime q hỗ trợ primitive root psi bậc2M:

```text
gm[bitrev(u)]  = psi^u * R mod q
igm[bitrev(u)] = (1/2)*psi^(-u)*R mod q
```

Scalar dùng R32. Packed root được đổi miền sang R16: root16=root32*2^(-16) mod q. Core nhận qinv32 tại register map; phần thấp16 chính là qinv16. Không nhân đôi/chuyển miền hệ số input theo phỏng đoán.

q nhỏ không tự bật packed. Producer chọn cfg_packed, packing và bảng root cùng nhau; vẫn có thể chạy q nhỏ trên scalar R32. Không đổi radix âm thầm chỉ vì số bit q giảm.

Dữ liệu input/output NTT là residue thường [0,q). Root Montgomery làm cho phép nhân root trả về cùng miền thường. hmin bỏ các tầng cuối theo convention của golden; hmin1 không bao gồm kernel basemul.

Root đúng giá trị nhưng sai thứ tự tile/k/chiều vẫn sai transform. Bảng logic được pack theo lịch ở spec03.

## 7. Packed pairing

Với request `{Y,X}`, mỗi word gồm low16/high16:

- pairing0: butterfly0=(X.lo,Y.lo), butterfly1=(X.hi,Y.hi).
- pairing1: butterfly0=(X.lo,X.hi), butterfly1=(Y.lo,Y.hi).

pairing1 dùng ở tầng internal của full packed NTT: tầng cuối thuận, tầng đầu nghịch. Root hai lane có thể khác nhau. Repack output phải khôi phục đúng word chứa cặp kết quả của từng butterfly; pairing đi cùng transaction, không lấy cờ hiện tại để sửa response cũ.

## 8. Negative controls bắt buộc

Đổi 3M thành4M, round sau tổng thay vì từng tích, quên wrap trước div2e, dùng root thuận cho IFFT, quên NZ(T_lo), carry xuyên lane, half nhánh inverse hai lần, hoặc dùng seed FFT thường cho native: bộ test phải phát hiện sai. Round-trip FFT không phải oracle bit-exact.

Nguồn đối chiếu: `docs/numeric_contract.md`, planner/RTL baseline trong reference_lock, các asset của spec1.0/2.0 và vector C. Nếu mô tả xung đột với source/vector đã khóa, mở issue trước khi viết datapath; không tự đổi expected output.
