# Model ghép liên tile cho FFT64/128

> PLAN mục 16, bước 4. Model: `model/intertile_model.py` (chạy: `python model/intertile_model.py`).
> Kết quả: `study/results/intertile.md`, `intertile_summary.csv`, `intertile_map_k32.csv`.
> Mô hình giải tích + kiểm tra bit-exact; chưa có RTL cây gom, chưa có pipeline/latency.

## 1. Tóm tắt

- Mọi mode FFT (32/64/128, kèm twiddle hẹp) ánh xạ được lên **một cây gom nhị phân có lượng dịch
  cố định** [0, 32, 32, 64, 64] bit theo chỉ số tile. Mode chỉ chọn **điểm lấy kết quả (tap)**
  và phép cộng/trừ ở cấp 1. Không cần cắt carry, không cần bộ dịch thay đổi theo mode.
- Kiểm tra bit-exact: **48 720 đầu ra** nhân phức (Re/Im) ở K = 16/32/64, gồm giá trị biên
  (−2^(W−1), ±1.0 của twiddle, 0) và ngẫu nhiên, khớp tích chính xác và làm tròn ties-to-even.
- Với K = 32: FFT64 đạt 2 butterfly/chu kỳ, FFT128 đạt 0,5 (2 lượt: Re rồi Im, **không cần
  accumulator**). Cây gom cần 31 bộ cộng, tổng 2 427 bit cộng; fan-in toán hạng mỗi tile ≤ 4 (dữ liệu)
  và ≤ 6 (twiddle) lane 32 bit.

## 2. Cách ánh xạ

Tile L32 tính một tích limb a_i·b_j (limb cao nhất mang dấu). Mỗi đầu ra là một thành phần của
tích phức: Re = br·wr − bi·wi, Im = br·wi + bi·wr. Chỉ số tile t (5 bit) được gán:

| Bit tile | Cấp cây | Dịch | FFT32 | FFT64 | FFT128 | FFT64 tw32 | FFT128 tw64 |
|---|---:|---:|---|---|---|---|---|
| t0 | 1 | 0, cộng/trừ | thành viên cặp | thành viên cặp | thành viên cặp | thành viên cặp | thành viên cặp |
| t1 | 2 | 32 | slot đầu ra | i0 | i0 | i0 | i0 |
| t2 | 3 | 32 | slot | j0 | j0 | slot | j0 |
| t3 | 4 | 64 | slot | slot | i1 | slot | i1 |
| t4 | 5 | 64 | slot | slot | j1 | slot | slot (Re/Im) |

- “Thành viên cặp”: Re ghép (br_i·wr_j, bi_i·wi_j) bằng phép trừ; Im ghép (br_i·wi_j, bi_i·wr_j) bằng phép cộng.
  Hai tích trong cặp có cùng trọng số nên cấp 1 không cần dịch.
- Các bit chỉ số limb được xếp theo trọng số (32 rồi 64), nên mỗi cấp có một lượng dịch duy nhất
  dùng chung cho mọi mode. Model kiểm tra điều này cho từng mode và báo lỗi nếu không ánh xạ được.
- FFT128 cần 32 tích cho một đầu ra; với K = 32 lượt 0 tính Re, lượt 1 tính Im của cùng butterfly
  (toán hạng giữ trong operand buffer 2 chu kỳ).

## 3. Throughput (bộ nhớ 512 bit/chu kỳ)

| K | Mode | Tile/đầu ra | Tap | Accumulator | BF/chu kỳ tính toán | Bộ nhớ | Đạt được | Tile bận |
|---|---|---:|---:|---|---:|---:|---:|---:|
| 16 | FFT64 | 8 | 3 | không | 1 | 2 | 1 | 100% |
| 16 | FFT128 | 32 | 5 | **có** (2 lượt/đầu ra) | 0,25 | 1 | 0,25 | 100% |
| 32 | FFT32 | 2 | 1 | không | 8 | 4 | 4 | 50% |
| 32 | FFT64 | 8 | 3 | không | 2 | 2 | 2 | 100% |
| 32 | FFT128 | 32 | 5 | không | 0,5 | 1 | 0,5 | 100% |
| 32 | FFT128 tw64 | 16 | 4 | không | 1 | 1 | 1 | 100% |
| 64 | FFT64 | 8 | 3 | không | 4 | 2 | 2 | 50% |
| 64 | FFT128 | 32 | 5 | không | 1 | 1 | 1 | 100% |

- K = 16 buộc FFT128 phải cộng dồn qua 2 lượt (thêm accumulator 257 bit và dịch 64): K ≥ 32 tránh được.
- K = 32 cân bằng với bộ nhớ 512 bit cho FFT64; FFT128 là mode duy nhất bị giới hạn bởi tính toán.
  Hai cách đưa FFT128 lên 1 butterfly/chu kỳ: K = 64 (gấp đôi bộ nhân) hoặc twiddle 64 bit (cần phân tích sai số).

## 4. Phần cứng cây gom (K = 32)

| Cấp | Số nút | Độ rộng nút | Độ rộng bộ cộng | Phép |
|---:|---:|---:|---:|---|
| 1 | 16 | 66 | 66 | cộng/trừ |
| 2 | 8 | 98 | 66 | cộng, dịch 32 |
| 3 | 4 | 130 | 98 | cộng, dịch 32 |
| 4 | 2 | 193 | 129 | cộng, dịch 64 |
| 5 | 1 | 257 | 193 | cộng, dịch 64 |

Tổng 2 427 bit cộng (bit thấp của nút con dưới đi thẳng, không qua bộ cộng).
Độ rộng là chặn trên giải tích từ miền limb; giá trị biên trong kiểm tra bit-exact nằm trong các độ rộng này.

**Bộ làm tròn:** mỗi điểm tap cần bộ làm tròn riêng nếu làm tròn tại chỗ: 31 bộ (2 975 bit vào)
khi hỗ trợ cả twiddle hẹp; 21 bộ nếu chỉ FFT32/64/128. Vì FFT32 chỉ được bộ nhớ cấp 4 butterfly/chu kỳ,
số bộ làm tròn ở cấp 1 có thể giảm từ 16 xuống 8 → **19 bộ** (có twiddle hẹp) hoặc **13 bộ** (không có).

## 5. Fan-in toán hạng

Với cách đóng gói tự nhiên (br|bi mỗi butterfly, wr|wi), qua mọi mode FFT, ngõ vào dữ liệu của
một tile nhận tối đa 4 lane 32 bit khác nhau (trung bình 3,1), ngõ twiddle tối đa 6 (trung bình 4,2).
Mạng phát toán hạng vì vậy là các mux nhỏ, không phải crossbar. NTT chưa được tính vào fan-in.

## 6. Kết luận và quyết định đề xuất

1. **Cây gom = cây nhị phân dịch cố định + điểm tap theo mode.** Thay cho ý tưởng adder phân đoạn
   cắt carry ở PLAN 5.6: không cần cắt carry vì mỗi nút có bộ cộng riêng; mode chỉ chọn tap.
2. **K = 32**, lịch FFT128 **theo đầu ra** (lượt Re, lượt Im), không accumulator.
3. Số bộ làm tròn định cỡ theo **trần bộ nhớ**, không theo trần tính toán.
4. FFT32 và twiddle hẹp FFT64 để một nửa tile rảnh ở 512 bit: đây là chỗ để chạy NTT song song
   trong tương lai, hoặc để tắt clock (clock-gating); ghi nhận như giới hạn.

## 7. Giới hạn và bước tiếp theo

- Chưa có: thanh ghi pipeline và latency từng cấp, cộng/trừ butterfly và scale theo stage,
  đường NTT (bypass cây, reducer), lịch bank bộ nhớ, phát twiddle, chi phí tag/metadata.
- Độ rộng cộng tính bằng bit; chưa có diện tích/timing thật của cây.
- Bước tiếp:
  1. RTL `pp_reduce.v` (cây 5 cấp, tap theo mode) + testbench từ `intertile_map_k32.csv`,
     tổng hợp Yosys để có diện tích cây so với 32 tile.
  2. Model latency/pipeline cho lịch 2 lượt FFT128 và chuyển mode.
  3. Ghép đường NTT: bypass cây, số lane reducer theo trần bộ nhớ.
