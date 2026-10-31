# Kế hoạch: Lõi FFT/NTT độ rộng chuyển runtime cho FN-DSA (Falcon)

> **Giai đoạn 1** — nhắm hội nghị nhỏ (bài 4–6 trang), nền tảng **Zynq**.
> Thời lượng ước tính: **~15 tuần** (1 người, toàn thời gian).

## 1. Ý tưởng và đóng góp

Một lõi dùng chung **mảng nhân** và **bộ nhớ** cho cả FFT số phức lẫn NTT modulo. Độ rộng toán hạng
được chọn **runtime theo pha của FN-DSA**; độ rộng hẹp → nhiều butterfly song song hơn trên cùng phần cứng.

| Pha FN-DSA | Mode | Lý do |
|---|---|---|
| Keygen — kiểm tra Gram-Schmidt, Babai reduction | **FFT 32.32** (64 bit) + block exponent | Chỉ cần xấp xỉ: sai số không phá phương trình NTRU (giả thuyết, kiểm chứng ở Phase 2) |
| Keygen — tính h = g/f mod q | **NTT 12289** (16 bit) | Số học chính xác |
| Ký | **FFT 64.64** (128 bit) | An toàn so với yêu cầu 32.64 của ePrint 2026/1531, 2026/2431; độ rộng lũy thừa 2 → đóng gói gọn |
| Verify | **NTT 12289** (16 bit) | Số học chính xác |

**Đóng góp dự kiến:**
1. **Mảng PE tổ chức theo nhóm**, kích thước nhóm đổi theo mode (32 / 8 / 1 PE), với ba khối riêng:
   mạng phát toán hạng, **cây gom tích riêng chia đoạn được** (gộp luôn nhân phức), bộ cộng/làm tròn phân đoạn.
   NTT đi vòng qua cây gom, giảm mod q tại từng PE.
2. Tổ chức bộ nhớ word 512 bit + mạng hoán vị nội word để mode hẹp **thực sự** chạy song song.
3. So sánh hai cách hiện thực cây gom trên FPGA: **cây cộng LUT** và **chuỗi cascade DSP48E2 cắt/nối runtime bằng OPMODE**.
4. Kết quả mới về số học: keygen FN-DSA (phần FFT) chạy được ở fixed-point 32.32 (nếu Phase 2 xác nhận).
5. Số liệu trên Zynq: chi phí của tính linh hoạt (tài nguyên, Fmax) và tăng tốc keygen/ký/verify so với ARM.

**Để giai đoạn 2:** NTT 31-bit (RNS cho NTRUSolve), căn bậc hai + key expansion trong HW, SamplerZ trong HW,
masking/TVLA, lõi linh hoạt cho workload ngoài FN-DSA.

## 2. Kiến trúc

| Hạng mục | Lựa chọn |
|---|---|
| Kiểu | Memory-based, in-place, radix-2 (CT thuận, GS nghịch) |
| Mảng nhân | `K = 32` PE, mỗi PE một bộ nhân 32×32 (≈ 128 DSP48E2), tham số hóa; tổ chức theo nhóm (mục 2.1) |
| Bộ nhớ | Word **512 bit**, chia bank, ánh xạ XOR, cổng đôi |
| Mạng hoán vị | Cho các stage có cặp butterfly nằm trong cùng word (FFT 32.32, NTT) |
| Twiddle | ROM FFT: Q2.62 (64 bit) cho 64.64, Q2.30 (32 bit) cho 32.32; ROM NTT: ψ^k mod 12289 |
| Nghịch đảo | `RECIP` cho **số thực dương** (ff̄ + gḡ là thực trong miền FFT): bảng seed + Newton–Raphson, dùng lại mảng nhân |
| Block exponent | Một thanh ghi số mũ cho mỗi buffer (Babai: hệ số hàng nghìn bit) |
| Điều khiển | Sequencer + hàng đợi lệnh ngắn (giảm chi phí AXI ở kích thước nhỏ) |
| Hệ thống | Zynq: ARM chạy phần còn lại (SHAKE, SamplerZ, NTRUSolve số lớn, nén); lõi ở PL qua **AXI4-Lite** (thanh ghi) + AXI BRAM controller/DMA (dữ liệu) |

### 2.1 Tổ chức nhóm PE

| Mode | Kích thước nhóm | Số nhóm | Mỗi PE làm | Gom kết quả |
|---|---|---|---|---|
| FFT 64.64 | 32 PE = 1 butterfly | 1 | 1 tích riêng aᵢ·wⱼ của 4 phép nhân thực 128×64 | Cây gom toàn mảng → làm tròn **một lần** |
| FFT 32.32 | 8 PE = 1 butterfly | 4 (bộ nhớ cấp đủ cho 2) | 1 tích riêng của phép nhân 64×32 | Cây gom tách thành các cây con độc lập |
| NTT 12289 | 1 PE = 1 phép nhân mod | 32 (bộ nhớ cấp đủ cho 16) | Nhân 14×14 + giảm mod q tại chỗ | Đi vòng qua cây gom |

```
              bộ nhớ (512 bit)
                    │
        ┌───────────┴───────────┐
        │  Mạng phát toán hạng   │  mode chọn limb nào tới PE nào
        └───────────┬───────────┘
            PE0  PE1  …  PE31        nhân 32×32; đường modred riêng cho NTT
              │    │        │
        ┌─────┴────┴────────┴───┐
        │ Cây gom tích riêng     │  dịch 32·(i+j) + cộng có dấu;
        │ chia đoạn theo mode    │  chặn carry ở ranh giới đoạn; NTT: bypass
        └───────────┬───────────┘
        ┌───────────┴───────────┐
        │ Làm tròn + cộng/trừ    │  bộ cộng 128 bit tách thành 2×64 / nhiều mod q
        │ butterfly hoặc ±p      │
        └───────────────────────┘
```

**Các quyết định chi tiết:**
- **Mạng phát toán hạng:** mux trước mỗi PE (≈ 3 lựa chọn × 32 bit × 32 PE).
- **Gộp nhân phức vào cây gom:** Re = ac − bd, Im = ad + bc — tích riêng của bd vào cây với dấu âm → bỏ một tầng cộng.
- **Làm tròn một lần** sau khi cộng đủ, khớp quy tắc của golden model.
- **Cân bằng latency:** mode hẹp chèn thêm tầng trễ để mọi mode cùng latency L → chỉ một cơ chế stall ở ranh giới stage.
- **Cây gom, hai biến thể:**
  - **V1 — cây cộng LUT** (làm trước): PE là khối 32×32 trừu tượng, cây cộng tổng quát ngoài DSP.
  - **V2 — cascade DSP48E2** (Phase 7): dùng PCIN/PCOUT + bộ dịch 17 bit; cắt/nối chuỗi runtime bằng OPMODE/INMODE
    động; mảnh nhân theo DSP (26×17) thay cho 32×32.

### 2.2 Throughput theo mode (word 512 bit/chu kỳ)

| Mode | Word chứa | Butterfly / chu kỳ | PE dùng | Falcon-1024, 1 phép | ≈ thời gian @200 MHz |
|---|---|---|---|---|---|
| FFT 64.64 | 2 số phức | 1 | 32 / 32 | 2304 butterfly | ~12 µs |
| FFT 32.32 | 4 số phức | 2 | 16 / 32 | 2304 butterfly | ~6 µs |
| NTT 12289 | 32 hệ số | 16 | 16 / 32 | 5120 butterfly | ~1.6 µs |

(Chưa tính latency pipeline; số liệu thật đo ở Phase 7.)

### 2.3 ffSampling — phân chia HW/SW

ffSampling đệ quy tới kích thước 1 và gọi SamplerZ (trên ARM) ở mỗi lá → ~n lượt qua lại AXI nếu làm hết trên lõi.
- **C1 (làm trước):** lõi chỉ làm FFT/IFFT + phép từng điểm ở tầng trên; ffSampling trên ARM.
- **C2:** ngưỡng cắt m₀ — tầng có kích thước ≥ m₀ chạy trên lõi, cây con nhỏ chạy trên ARM; quét m₀ để tìm điểm tối ưu.

### 2.4 Register map (AXI4-Lite)

| Offset | Tên | Nội dung |
|---|---|---|
| 0x00 | `CTRL` | start, soft reset, xóa hàng đợi |
| 0x04 | `MODE` | FFT_64_64 / FFT_32_32 / NTT_12289 (dự trữ: NTT_RNS31) |
| 0x08 | `OP` | FFT, IFFT, PW_ADD, PW_SUB, PW_MUL, MUL_ADJ, SPLIT, MERGE, RECIP, SCALE, NTT, INTT, PW_MULMOD |
| 0x0C | `LOGN` | 1…10 |
| 0x10 | `SRC_A` / `SRC_B` / `DST` | ID buffer |
| 0x18 | `BEXP` | block exponent của buffer |
| 0x1C | `STATUS` | busy, done, error, số lệnh còn trong hàng đợi |
| 0x20 | `QUEUE` | đẩy lệnh (MODE, OP, LOGN, buffer) vào hàng đợi |
| 0x1000+ | Cửa sổ bộ nhớ | đọc/ghi hệ số |

Mode chỉ đổi giữa các lệnh và do pha thuật toán quyết định (công khai) → không rò rỉ qua timing.

## 3. Cấu trúc thư mục

```
NTRU/
├── ref/         # Falcon/FN-DSA reference (bạn tự tải, không sửa)
├── algorithm/   # Golden model C++ (Makefile, main.cpp, ...)
├── study/       # Đo sai số, kết quả .csv
├── hdl/         # RTL Verilog
├── sim/src/     # Testbench
├── sim/work/    # Output mô phỏng
├── sw/          # Driver + ứng dụng trên ARM (Zynq)
└── docs/        # Spec, kết quả, bản thảo bài báo
```

## 4. Các phase

### Phase 0 — Chuẩn bị (1 tuần)
- Tải Falcon reference vào `ref/`, build và chạy KAT.
- **Profiling trên ARM của Zynq** cho keygen / ký / verify: % thời gian của FFT, ffSampling, SamplerZ,
  NTRUSolve (số lớn), NTT → biết trước mức tăng tốc tối đa (Amdahl).
- Đọc kỹ: ePrint 2026/1531, 2026/2431, 2026/1915, arXiv 2504.11124, ZK-Flex (arXiv 2606.03046)
  → `docs/related_work.md`; kiểm tra chưa có ai làm HW fixed-point Falcon / keygen fixed-point.
- Chọn hội nghị, ghi deadline và giới hạn trang.
- **Xong khi:** reference chạy được trên ARM, có bảng profiling, chốt hội nghị.

### Phase 1 — Golden model C++ (3 tuần)
- `algorithm/fixed.hpp` — `Q<I,F>` cho 32.32 và 64.64, tính bằng limb 32-bit như HW; quy tắc làm tròn/bão hòa rõ ràng.
- `algorithm/fft_fx.cpp` — FFT/IFFT negacyclic, n/2 điểm phức, n = 2…1024, cả hai mode.
- `algorithm/fftalu_fx.cpp` — PW_ADD/SUB/MUL, MUL_ADJ, SPLIT, MERGE, RECIP (seed + Newton–Raphson), SCALE/block exponent.
- `algorithm/ntt.cpp` — NTT/INTT mod 12289, PW_MULMOD.
- `algorithm/falcon_glue.cpp` — thay FFT số thực của reference: ký dùng 64.64; keygen (Gram-Schmidt, Babai) dùng 32.32.
- `algorithm/vecgen.cpp` — sinh vector `.hex` cho testbench.
- **Xong khi:** NTT khớp bit với reference; chữ ký từ model verify được; khóa từ model hợp lệ.

### Phase 2 — Kiểm chứng precision (2 tuần) — **cổng quyết định**
- **Ký 64.64:** tỉ lệ verify 100%, sai số so với biên của 2026/1531, phân phối chuẩn chữ ký so với bản double (KS test).
- **Keygen 32.32:**
  - tỉ lệ sinh khóa thành công và số vòng Babai so với bản double;
  - fG − gF = q đúng tuyệt đối (kiểm tra bằng số nguyên);
  - số khóa mà kiểm tra Gram-Schmidt cho kết quả khác bản double;
  - chiến lược block exponent cho từng tầng NTRUSolve (không tràn 32 bit nguyên).
- **Cổng:**
  - 32.32 đạt cho keygen → giữ nguyên câu chuyện 3 mode.
  - Không đạt → keygen dùng 64.64; câu chuyện còn 2 độ rộng (128 bit FFT vs 16 bit NTT), nhấn mạnh tái sử dụng mảng nhân cho NTT.
- **Đầu ra:** `docs/precision.md`, `study/results/*.csv`.

### Phase 3 — Spec vi kiến trúc (1 tuần)
- **Nhóm PE:** bảng ánh xạ limb → PE cho từng mode; mạng phát toán hạng.
- **Cây gom:** lượng dịch theo mode, điểm cắt carry, gộp nhân phức (dấu của tích bd), vị trí làm tròn.
- **Bộ cộng phân đoạn:** 128 bit ↔ 2×64 bit ↔ nhiều bộ cộng/trừ mod q.
- **Latency:** chốt L chung, số tầng trễ chèn cho từng mode; chính sách stall ở ranh giới stage.
- Banking và mạng hoán vị nội word; kích thước ROM; khối RECIP; sequencer + hàng đợi; giao tiếp AXI.
- Chuẩn bị sẵn giao diện để thay V1 (cây LUT) bằng V2 (cascade DSP) mà không đổi phần còn lại.
- → `docs/arch.md`.

### Phase 4 — RTL FFT hai độ rộng (3 tuần)
- `hdl/`: `pe.v` (nhân 32×32 + đường modred), `pe_array.v`, `operand_bcast.v`,
  `pp_reduce.v` (cây gom V1, chia đoạn, gộp nhân phức), `round_unit.v`, `seg_addsub.v`,
  `addr_gen.v`, `mem_banks.v`, `word_shuffle.v`, `twiddle_rom_fft.v`, `ctrl_fsm.v`, `fft_core.v`.
- Unit test riêng cho `pp_reduce.v` và `seg_addsub.v` ở cả 3 mode trước khi ghép lõi.
- `sim/src/tb_fft_core.v` đọc vector từ `vecgen`.
- **Xong khi:** khớp bit với golden model ở 64.64 và 32.32 × n = 2…512 điểm phức × FFT/IFFT.

### Phase 5 — RTL NTT + ALU (2 tuần)
- `modred_12289.v` (chỉ cộng/dịch, gắn trong `pe.v`), hiệu chỉnh ±p trong `seg_addsub.v`,
  `twiddle_rom_ntt.v`, đường bypass cây gom.
- PW_*, MUL_ADJ, SPLIT, MERGE, RECIP, SCALE.
- **Xong khi:** NTT khớp bit với reference; các OP còn lại khớp bit với golden model.

### Phase 6 — Bus + sequencer + test hệ thống (1–2 tuần)
- `hdl/fftntt_axil_slave.v` (theo mẫu `AXI4lite_UART`), hàng đợi lệnh, đường dữ liệu AXI.
- Test mô phỏng: chạy chuỗi lệnh của keygen (phần FFT), ký, verify; so với golden model.
- **Xong khi:** mọi chuỗi lệnh khớp bit với golden model.

### Phase 7 — Zynq + đánh giá (2 tuần)
- `sw/`: driver bare-metal/PYNQ; Falcon reference trên ARM gọi lõi.
- Ký: C1 rồi C2 (quét m₀). Verify, keygen (phần FFT + tính h).
- Đo: LUT/FF/DSP/BRAM, Fmax, chu kỳ từng OP × mode, thời gian keygen/ký/verify end-to-end.
- **Baseline so sánh:**
  - Falcon reference trên ARM (phần mềm);
  - lõi cố định độ rộng (chỉ 64.64, chỉ 32.32, chỉ NTT) tổng hợp riêng → chi phí của tính linh hoạt;
  - **V1 (cây LUT) vs V2 (cascade DSP, `pp_reduce_dsp.v`)** trên cùng các mode: LUT/DSP, Fmax, latency;
  - arXiv 2504.11124; các bản Falcon HW đã công bố.

### Phase 8 — Viết bài (2 tuần, chồng với Phase 7)
- Intro → Background (FN-DSA, fixed-point Falcon) → Phân tích precision theo pha → Kiến trúc → Kết quả → Kết luận.

## 5. Kiểm chứng

| Đường | Tiêu chí |
|---|---|
| NTT (verify, tính h) | Khớp bit tuyệt đối + qua KAT verify chính thức |
| Ký (FFT 64.64) | RTL khớp bit golden model; chữ ký verify được 100%; thống kê giống bản double |
| Keygen (FFT 32.32) | RTL khớp bit golden model; fG − gF = q đúng tuyệt đối; khóa ký/verify được; thống kê giống bản double |
| Không đặt mục tiêu | KAT cho ký và keygen — fixed-point đổi làm tròn (SamplerZ, Babai) nên kết quả khác KAT dù đúng |

## 6. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| 32.32 không đủ cho keygen | Cổng Phase 2: chuyển keygen sang 64.64, giữ câu chuyện FFT 128 bit vs NTT 16 bit |
| Tăng tốc nhỏ vì SamplerZ / NTRUSolve số lớn trên ARM | Biết sớm nhờ profiling Phase 0; C2 cho ký; NTT31 + SamplerZ HW ở giai đoạn 2 |
| Nhóm khác công bố HW fixed-point Falcon trước | Làm nhanh; nhấn mạnh keygen 32.32 + độ rộng runtime (khác biệt) |
| Fmax giảm vì mux ghép mảng nhân 128 bit | Pipeline sâu cho mode rộng, đo từ Phase 4 |
| Mạng hoán vị nội word tốn LUT | Giới hạn số hệ số đóng gói là lũy thừa 2; đo chi phí riêng |
| Cây gom V1 thành đường tới hạn | Pipeline theo tầng cộng; V2 (cascade DSP) là phương án dự phòng |
| V2 không cắt/nối được linh hoạt như mong muốn | V2 chỉ là kết quả so sánh; lõi chính dùng V1 |
| Bị so với ZK-Flex (ghép PE thành bộ nhân rộng) | Nêu rõ khác biệt: nhân phức gộp vào cây gom, làm tròn fixed-point, bypass cho NTT, dải 14–128 bit |

## 7. Giai đoạn 2 (bài thứ hai)

- Mode **NTT 31-bit + Montgomery** cho RNS trong NTRUSolve → keygen tăng tốc thật sự.
- Căn bậc hai + key expansion (cây ffLDL) trong HW, mode 64.64; ký kiểu dynamic (không lưu cây).
- SamplerZ trong HW → ffSampling chạy trọn trên lõi.
- Mở rộng thành lõi linh hoạt cho workload khác (ML-KEM/ML-DSA NTT, FFT xử lý tín hiệu).
