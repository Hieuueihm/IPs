# Packed16 dùng cả bốn leaf — nguồn kiểm chứng của baseline 3.1

Baseline hiện hành là `a_cg_packed4_system160`, được người dùng nhận ngày 2026-11-04, contract 3.1. Thư mục này cung cấp planner, harness và bằng chứng chức năng chính thức; `rtl/` giống từng byte với nguồn P&R được nhận. Mốc trước `a_cg_z020_system160` giữ làm lịch sử. Chưa commit. Target `xc7z020clg400-2`.

**Đã kiểm xong:** RTL hiện tại dùng cả bốn leaf, synth 34.185 LUT,
32.855 FF, 64 DSP và 48 RAMB18. Baseline synth cùng flow là 31.137 LUT;
chi phí thêm 3.048 LUT. Gộp T-high history tiết kiệm 1.208 LUT so với
nguyên mẫu hai history riêng. Tổng gồm AXI host và toàn bộ data/root RAM.

1.026 ca qua AXI, 33.600 butterfly tại tile, 10 ca four-state và replay
74 transform C đều qua. 14 artifact trùng từng byte, 4 chữ ký được xác
minh độc lập. NTT q=12289/N1024 giảm 531→391 chu kỳ; batch hai job giảm
987→535 chu kỳ. FFT và NTT nonpacked giữ nguyên kết quả và chu kỳ.

Synth WNS **−0,531 ns**, bằng baseline khi synth lại cùng OOC flow; cùng
đường host `wstrb_reg[0] → cmd_cfg_reg/R`. [Báo cáo synth](../../study/results/a_cg_packed4.md).

**P&R tiếp theo đã đạt 160 MHz trên bản hệ thống riêng:** 34.277 LUT,
setup +0,178 ns, hold +0,032 ns; vẫn 64 DSP và 48 RAMB18. Xem
[báo cáo P&R toàn hệ thống](../../study/results/a_cg_packed4_system160.md)
và `../a_cg_packed4_system160/`. RTL bốn file giống ứng viên này từng byte;
người dùng đã nhận làm baseline mới, chưa chạy board.

## Tổ chức số học

Mỗi tile giữ bốn leaf nhân 16×16. FFT32/64/128 và NTT32 tiếp tục ghép chúng
thành bộ nhân 32×32. Packed16 tách thành hai nhóm:

- Luồng A: leaf0/1, một gói hai butterfly mới ở pha 0 mỗi ba chu kỳ enabled.
- Luồng B: leaf2/3, một gói hai butterfly mới ở pha 1.
- Từng luồng thực hiện `T`, `m`, `m*q` cách nhau năm chu kỳ, giữ nguyên số học
  Montgomery với R=2^16, q lẻ, 3≤q<2^15. Kết quả vẫn được hiệu chỉnh modulo q.
- Hai nhóm lấy tích thô trước bộ ghép 32×32; thêm hai thanh ghi căn độ trễ
  để phản hồi vẫn dài năm chu kỳ. Không thêm DSP.
- Hai luồng có chọn toán hạng và valid riêng. Dùng chung các thanh ghi cấu
  hình hai modulus slot, đường lưu T-high/NZ, tầng cộng U, hiệu chỉnh U−q,
  bộ cộng/trừ butterfly và FIFO side/tag 16 phần tử.

Lịch ổn định (mỗi ô có thể thuộc một gói khác nhau):

| Pha | Leaf0/1 | Leaf2/3 |
|---|---|---|
| 0 | T | m |
| 1 | m*q | T |
| 2 | m | m*q |

Các phép T→m→m*q của cùng một gói vẫn phụ thuộc nhau và cách năm chu kỳ.
Thông lượng bão hòa là bốn butterfly / ba chu kỳ / tile. Đây không phải
cam kết mọi transform nhanh gấp đôi: fill/drain, phụ thuộc giữa tầng và số
butterfly mỗi tile giới hạn tốc độ toàn lõi. Batch đồng cấu hình giúp cấp
thêm việc cho transform nhỏ.

## Giao tiếp và bộ nhớ

Giữ cổng request/response 64 bit, root 32 bit, tag 8 bit của tile. Mỗi gói
vẫn là hai butterfly; đổi nhịp nhận từ một thành hai gói mỗi ba chu kỳ.
Không thêm cổng RAM hoặc tăng độ rộng bus. Đầu vào lõi đọc ở pha 1/2;
qua pipeline tới tile ở pha 0/1. Mỗi lần đọc vẫn chỉ có bốn nguồn mỗi cổng.

`planner.py` dùng thứ tự phát gói `3*(seq//2)+seq%2` cho packed16, giữ
nguyên lịch scalar/FFT. Mô hình kiểm các phiên bản dữ liệu, cổng bank,
RAW và chồng lấp tầng trước khi đóng fixture. Root vẫn theo thứ tự k của
từng tile. Phải dùng descriptor gap do planner của ứng viên sinh để đo
tốc độ ứng viên.

## Các kiểm tra

- Oracle tile độc lập dùng nghịch đảo R modulo q, không dùng công thức
  T/m/mq của RTL: 16.800 gói, 33.600 butterfly, 7 modulus gồm các biên,
  hai slot, CT/GS, bật/tắt halving, hai cách pairing, bubbles và enable stall.
- Kiểm nhận 300 gói bão hòa trong tối đa 449 khoảng chu kỳ; đếm chu kỳ cả
  bốn leaf có phép toán hợp lệ; reset khi cả hai luồng còn phép đang xử lý.
- 1.026 ca qua AXI với golden vector hiện có; planner chỉ đổi lịch, không
  thay giá trị golden. So mọi chu kỳ nonpacked với baseline.
- Icarus four-state tập trung 10 ca packed thay đổi: full/incomplete NTT,
  N=2 và N=1024, CT/GS, hai kiểu packing và batch. Các FFT và scalar còn
  được kiểm trong suite AXI 1.026 ca và replay C.
- Replay C: 74 transform, so 14 artifact từng byte và xác minh độc lập 4
  chữ ký. Giữ các bước ngoài transform ở C như baseline.
- Reset và backpressure AXI, WSTRB, lỗi địa chỉ/lệnh.

Chạy lại: `./experiments/a_cg_packed4/run_sim.ps1`. Sinh `results.json`
bằng `python -X utf8 experiments/a_cg_packed4/report.py` sau khi các bài
kiểm và synth hoàn tất.

## Synth và giới hạn kết luận

`synth.tcl` so cả AXI host, core, data RAM và root RAM trên cùng part,
clock 6,25 ns và cùng uncertainty/jitter. Không buộc mode, q hoặc precision.
Các biến thể: `baseline`, `candidate` (v0 với T-high riêng),
`candidate_shared_t` (RTL hiện tại với T-high chung).

Lệnh: `vivado.bat -mode batch -source experiments/a_cg_packed4/synth.tcl
-tclargs candidate_shared_t`. Báo cáo trong `study/build/a_cg_packed4/`.

Đây là OOC synthesis cho AXI/core. Không bao gồm PS7/interconnect/clock/reset
của top board; không so trực tiếp số này với 31.242 LUT sau P&R toàn hệ
thống của baseline. Phép đo synth này đứng riêng; kết quả P&R và audit
160 MHz tiếp theo nằm ở `a_cg_packed4_system160`, dùng đúng RTL bốn file
của ứng viên. Chưa chạy board. Registry hiện hành là a_cg_packed4_system160; nguồn mốc trước giữ làm lịch sử.

`make_initial_fork.py` chỉ ghi lại cách tạo v0, không tái tạo RTL hiện tại.
Nguồn chuẩn của ứng viên là `rtl/`. Bằng chứng v0 giữ riêng trong
`study/build/a_cg_packed4/rtl_v0`, `sim_v0.log`, `application_v0` và
`synth_candidate`; four-state v0 dừng khi chuyển sang RTL T-high chung,
log đó có hậu tố `v0_partial`, không tính là bài kiểm đã qua.

## Sau khi nhận baseline

Nguồn và raw evidence ở thư mục này hiện được pin cùng baseline 3.1. Các script run_sim/application/build_fixtures có ghi output: chỉ full rerun trên bản sao/output riêng. Kiểm mốc hiện hành bằng scripts/check_baseline.py hoặc a_cg_packed4_system160/validate.py. Các manifest v0/OOC lưu lịch sử đo, không tự quyết định baseline hiện hành.
