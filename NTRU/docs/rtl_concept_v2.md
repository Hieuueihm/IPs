# Bản vẽ ý tưởng RTL v2

Đây là bản sửa sơ đồ kiến trúc để người thiết kế triển khai tiếp. Chỉ cập nhật
hình và đặc tả ý tưởng; không thay RTL, không tuyên bố buffer/batching mới đã
được mô phỏng. Các kết quả baseline trước đây giữ nguyên phạm vi của chúng.

| Hình | PNG | SVG chỉnh sửa được |
|---|---|---|
| Core tổng thể | [Xem](figures/shared-fft-ntt-rtl.png) | [SVG](figures/shared-fft-ntt-rtl.svg) |
| FFT pre-add, keep-data và 3M | [Xem](figures/fft-3m-rtl-detail.png) | [SVG](figures/fft-3m-rtl-detail.svg) |
| Tile và đường CT/GS | [Xem](figures/shared-tile-rtl-detail.png) | [SVG](figures/shared-tile-rtl-detail.svg) |
| Ghép limb, dấu và rounding | [Xem](figures/fft-fusion-sign-rtl-detail.png) | [SVG](figures/fft-fusion-sign-rtl-detail.svg) |

## 1. Giữ và chuyển tiếp toán hạng

FFT: bộ chọn butterfly tạo toán hạng phức X, Y và nhánh giữ K. Với FFT,
X=B, Y=w, K=A. Với iFFT, X=wrap(A−B), Y=conj(w), K=wrap(A+B).
Hai pre-adder tạo Sx=wrap(Xr+Xi), Sy=wrap(Yr+Yi). Bộ issue chọn ba phép
nhân Xr×Yr, Xi×Yi, Sx×Sy; mỗi product được rounding riêng trước khi collector
ghép complex result. K và địa chỉ ghi được giữ theo context/lane cho đến khi
đủ ba product. Chỉ scale iFFT ở cuối transform; scale phải wrap trước dịch.
Hình chi tiết này mô tả FFT/iFFT; SPLIT/MERGE có các phép chọn/scale riêng
theo contract, không được suy ra chỉ bằng đổi nhãn op.

NTT: CT giữ A để tạo (A+T,A−T), GS giữ S=A+B để tạo (S,T), với
T=Mont(B,w) ở CT và T=Mont(A−B,w) ở GS. w là root đã mã hóa Montgomery.
Side-data, root và context phải đi qua register/buffer có valid/ready tương ứng
với đường product, kể cả khi stall. Tile có hai cặp multiplier, một cặp mỗi
compute stage; dữ liệu giữa hai tầng nằm trong Rmid và qua permutation SW.
Đường một tầng bypass kết quả tầng hai nhưng phải khớp latency/handshake.

## 2. Tổ chức cấp dữ liệu được đề xuất

- Coefficient store vẫn lấy 64 bank ×16 bit làm baseline, mỗi bank 1R+1W.
  Bank service lập các lượt đọc theo row; gather chỉ đóng gói dữ liệu đã đọc,
  không tạo thêm cổng đọc. Write-back có scatter và bank mask.
- FFT twiddle store giữ một cổng đọc complex root/cycle. Prefetch thu đủ root
  cho batch trước khi phát; root giống nhau có thể broadcast/cache. Root buffer
  phục vụ tối đa 16/4/1 lane thực theo W32/64/128. Không giả định 16 root/cycle.
  Nếu dùng precision thấp, conjugation/quantization phải giữ đúng thứ tự contract.
- NTT giữ tổ chức 16 bank bundle ×48 bit. Một bundle chứa ba root dùng cho
  cụm hai tầng; khả năng cấp đồng thời vẫn phải thỏa các địa chỉ bank/row.
- Đề xuất hai context batch dạng ping-pong để tách fill và execute/retire.
  Batch chỉ ready khi đủ coefficient, root và context. Đây là baseline buffer
  ở mức ý tưởng, chưa phải chứng minh hai context đủ che mọi latency.
- NTT nhỏ gom job cùng N, q-profile và hướng CT/GS vào một batch. Cần gán vị
  trí bank/lane cho từng job, mang job_id và active mask; không trộn hệ số hay
  trạng thái tầng của các job. Packing job vào RAM chưa có ánh xạ cuối cùng.

## 3. Ghép/tách và số học

16 tile minh họa, mỗi tile bốn lá nhân 16×16. Một tile tạo raw product 32×32;
W32 dùng 16 nhóm một tile, W64 dùng bốn nhóm bốn tile, W128 dùng một nhóm
16 tile. Đây là số lane tích thực, không phải số butterfly phức/cycle.

Limb thấp unsigned, limb cao nhất của mỗi operand signed; tile nhận sign
độc lập cho hai operand. Ghép các raw product bằng dịch cố định và cộng modulo
độ rộng giữ: W32 giữ 48 bit, W64 giữ 96 bit, W128 giữ 192 bit. Thêm bias
2^(F−1), chọn W bit phía trên F bit phân số, với F=W/2. Product limb không được
round riêng. Việc bỏ các term có trọng số ngoài độ rộng giữ là exact theo
contract wrap, không phải xấp xỉ số học.

FFT128 Q64.64 giữ contract R8 đã pin. FFT32/64 là contract riêng; hình không
chứng minh precision thấp đủ chính xác cho FN-DSA. NTT hiện hướng đến profile
q12289/q3329; không ngụ ý hỗ trợ q tùy ý hoặc modulus rộng hơn 16 bit.

## 4. Giao diện context và điều kiện hoàn thành

Packet dữ liệu có tối thiểu: valid, ctx_id, job_id, stage_id, lane_mask,
product_sel (FFT), destination address và last. W, q-profile, hướng và mode
được latch cho batch; phiên bản ý tưởng này chỉ đổi cấu hình sau khi toàn
pipeline đã drain, tránh phải cho mỗi stage xử lý nhiều cấu hình đang xen kẽ.

Context chỉ được tái sử dụng khi toàn bộ kết quả của nó đã retire. Stage
barrier cho phép sang tầng kế tiếp sau khi mọi write của tầng hiện tại đã
commit; một tín hiệu last đến arithmetic output chưa đủ để mở barrier.
Các butterfly độc lập trong cùng tầng có thể chồng lấp, nhưng phải kiểm tra
hazard đọc/ghi và tránh hai writer cùng bank/row trong một beat.

## Những gì chưa chốt

Chưa chốt map bank cho FFT batch và NTT nhiều job, độ sâu pipeline/FIFO,
arbitration đọc/ghi, số context tối ưu, số tile tối ưu, timing/area hay speedup.
Prefetch/buffer thể hiện cơ chế xử lý giới hạn băng thông, không xóa giới hạn đó.
Không triển khai FPGA hoặc thay datapath trong lần sửa hình này.

Tạo lại bốn hình: `python scripts/draw_revised_rtl.py` (Pillow, font Arial).
