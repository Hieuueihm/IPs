# P2 — OpenNTT: đổi tham số khác đổi phân bổ phần cứng thế nào?

Ngày phân tích: 21/10/2026. Đã đối chiếu paper với generator và RTL.
Commit được đọc: 86c07a5e77639f7f33292b31418f50c56c6aabd5.
Chưa chạy generator, simulation hoặc synthesis của OpenNTT.

## Bằng chứng từ paper

[A Flexible Hardware Design Tool for Fast Fourier and Number-Theoretic Transformation Architectures](https://flokrieger.github.io/papers/tcad25_opennttext.pdf),
[DOI](https://doi.org/10.1109/TCAD.2025.3595834), Section III-D, IV-A/B:
FFT hoặc NTT được chọn khi tạo lõi; hướng biến đổi và q có thể chọn runtime
trong cấu hình tương ứng. Datapath được định cỡ theo q lớn nhất.

Section III-B/C, Fig. 2–4: RoutOpt đặt seed ROM riêng theo PE;
MemOpt dùng seed ROM chung. TwGen sinh chuỗi twiddle từ seed.
Đây là đánh đổi ROM/routing, không phải cơ chế fusion.
[Nguồn toàn văn, pp. 2535–2538](https://flokrieger.github.io/papers/tcad25_opennttext.pdf).

## Đối chiếu trực tiếp với code

Các đường dẫn dưới đây đều ghim commit để tránh main thay đổi sau thời điểm đọc.

| Câu hỏi | Bằng chứng code | Kết luận trong cấu hình mặc định |
|---|---|---|
| Width lấy từ đâu? | Generator tính logq_max trên q_list, xuất localparam LOGQ | Chọn q nhỏ không tạo lại hardware |
| PE lấy từ đâu? | Xuất localparam PE = io_band//2 | PE là tham số tạo lõi |
| q có thật là input? | NTTCore có q; Q_VALUE khác 0 chọn q cố định | Có đường q runtime khi tạo lõi linh hoạt |
| FFT và NTT cùng bitstream? | Nhánh generate if(NTT) chọn butterfly | Hai loại datapath là lựa chọn elaboration |

[Generator, dòng 164–195 và 237–248](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/tool/openntt.py#L164);
[NTTCore, khai báo tham số và vòng generate](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/ntt_control/ntt_core.sv#L254).

Không diễn giải “unified” trong tên option forward/inverse thành FFT và NTT cùng chạy
trên một bitstream.

### Multiplier và reducer có tự nhỏ lại khi q nhỏ?

btf_modmul khai báo sản phẩm 2×LOGQ bit, gọi intmul với hai toán hạng LOGQ bit,
rồi gọi modred. Width không lấy từ giá trị q mỗi cycle.
[btf_modmul.sv, dòng 29–41](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/butterfly/btf_modmul.sv#L29).

wlmont có tham số L và vòng generate i<L, sau đó correction với q.
Số tầng được tạo tĩnh; đổi q không phải lệnh tạo thêm lane reducer.
[wlmont.sv, dòng 10–55](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/modred/modred_wl_mont/wlmont.sv#L10).

PolyRAM tạo hai bank cùng MEM_WIDTH cho một butterfly; không có selector runtime
để thay MEM_WIDTH của hai bank.
[polyRam.sv, dòng 7–58](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/memory/polyRam.sv#L7).

Suy luận cấu trúc: trong core đã tạo, q nhỏ hơn vẫn đi qua cùng tập tài nguyên này.
Có thể khác switching activity; không được từ đó suy ra LUT/DSP vật lý giảm hoặc
throughput tăng. Chưa đo điện năng để kết luận mức lãng phí.

## Sơ đồ phân tích

~~~text
HOST CONTEXT: q, direction, seed-base, polynomial IDs
                          |
                   stage/address control
                          |
bank pair 0 -> shuffle -> butterfly 0 <- TwGen 0 -> writeback
bank pair 1 -> shuffle -> butterfly 1 <- TwGen 1 -> writeback
   ...                         ...
bank pair P-1             butterfly P-1

RoutOpt: seed ROM gần từng TwGen
MemOpt:  seed ROM chung cấp dữ liệu khởi tạo
~~~

Đây là mô hình khái niệm để đọc Fig. 4, không mô tả đầy đủ wiring.
Điểm thiết kế cần khảo sát thêm cho FlexTransform: khi logical PE thay đổi theo
width, ai tạo chuỗi địa chỉ/twiddle mới tương ứng?

## Ví dụ phân biệt ba kiểu flex — tự phân tích

Giả sử chọn transform negacyclic N=1024. Xét hai prime ứng viên:

~~~text
q_a = 12289       -> 14 bit có nghĩa
q_b = 2013265921  -> 31 bit có nghĩa
(q_a - 1) / 2048 = 6
(q_b - 1) / 2048 = 983040
~~~

Điều kiện chia hết trên cho phép tồn tại root bậc 2048 trong trường prime.
Nó không thay việc chuẩn bị root, representation và constants đúng cho datapath.
Hai prime chỉ phục vụ ví dụ; chưa thêm chúng vào phạm vi bắt buộc của PLAN.

Giả sử P=4 và cùng bitstream chứa cả hai context:

| Cách flex | Khi chạy q_a | Khi chạy q_b | Điều phải bổ sung |
|---|---|---|---|
| Chỉ đổi q | 4 butterfly logic | 4 butterfly logic | Context và twiddle đúng |
| Chọn width, giữ P | 4 butterfly ở width hẹp | 4 butterfly ở width rộng | Bypass/clocking nếu muốn lợi ích energy |
| Đổi width và grouping | Nhiều lane hẹp | Ít lane rộng hợp tác | Routing, reducer, memory, scheduler |

Dòng đầu minh họa ý nghĩa configurability được xác nhận ở OpenNTT.
Hai dòng sau là phân loại để thiết kế thí nghiệm, không phải mô tả tính năng của repo.
Nếu cả hai width đều nằm trong một multiplier primitive 32×32, phân rã schoolbook
ở granularity này cho cùng một multiplication slot. Không có lợi ích tăng số
multiplier lane chỉ vì 14<31; muốn packing thêm phải chứng minh cơ chế khác.

## Tại sao không chỉ thay multiplier của OpenNTT?

Đây là các phụ thuộc mình suy ra cho kiến trúc mới:

1. **Reduction:** nhiều integer product độc lập đòi hỏi đủ reducer issue slots.
   Một reducer chung có thể làm throughput toàn nhóm vẫn bằng một lane.
2. **Twiddle:** nhóm có nhiều butterfly hơn cần đúng root cho từng butterfly.
   Không mặc định số lane tăng thì TwGen cũ tự cấp đủ.
3. **Memory:** cần đủ cổng hoặc packing hợp lệ, cùng địa chỉ writeback không xung đột.
4. **Hazard:** đổi số butterfly/cycle làm khoảng cách đọc/ghi giữa stage thay đổi.
5. **Representation:** đổi q phải đồng bộ cả constants, miền Montgomery và normalization.

RTL còn kiểm tra điều kiện:

~~~text
RAM_RD_LAT + BTF_LAT + DATA_SHUFFLER_LAT_OVERALL <= N/(4*PE)
~~~

[NTTCore, dòng 75–78](https://github.com/flokrieger/OpenNTT/blob/86c07a5e77639f7f33292b31418f50c56c6aabd5/hardware/ntt_control/ntt_core.sv#L75).
Đó là ràng buộc của lịch hiện tại. Ví dụ tự tính N=1024, PE=8 cho vế phải 32 cycle;
PE=16 cho 16 cycle. Không chuyển bất đẳng thức này thành định luật chung cho mọi
kiến trúc; một scheduler khác có thể dùng quy tắc khác.

## Đánh giá và kết luận phục vụ thiết kế

Không chọn một dòng benchmark rồi gọi đó là “hiệu năng OpenNTT” cho mọi cấu hình.
Cần lưu N, q_list, nPE, loại transform, MemOpt/RoutOpt, FPGA và phạm vi thời gian
cùng kết quả. Các tài liệu hiện tại chưa phải dữ liệu tái lập của mình.

OpenNTT là baseline tốt cho **runtime modulus trên datapath cố định** và cho
đồng thiết kế lịch truy cập–twiddle. Khác biệt dự kiến của FlexTransform là
đổi phân bổ tài nguyên số học theo width trên cùng lõi FFT/NTT. Đây mới là giả thuyết
cần đánh giá; không phải bằng chứng novelty so với toàn bộ related work.
