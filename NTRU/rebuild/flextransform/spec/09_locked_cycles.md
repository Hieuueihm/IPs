# 09 — Lịch từng clock và guard bit đã khóa (0.2)

Nguồn máy đọc: `microarchitecture/timing.json`; bảng đầy đủ mọi cạnh nằm trong `microarchitecture/cycles/`. Sinh lại bằng tools/render_timing_contract.py. Những con số này là **contract thiết kế**, chưa phải latency đo trên RTL mới.

## 1. Mốc cạnh duy nhất

C0 là cạnh request tile fire. Tín hiệu tạo **sau** cạnh Cn chỉ được consumer lấy ở Cn+1. “Launch sau Cn” là operand/mux đã ổn định sau Cn; leaf input FF chốt ở Cn+1. Raw product sau Cn+3, fused sau Cn+5. Không gọi launch là cạnh leaf capture.

Bank/root read chốt tại R0, route/request FF tại R0+1, tile fire tại R0+2. Tile rsp tạo sau E, bank commit tại E+1. Không thêm full-width write FF trong version0.2. Nếu thêm, đổi version, planner, gap và model; không tự bù bằng shift valid.

## 2. NTT scalar và từng nhóm packed

| Cạnh từ fire | Hoạt động |
|---:|---|
| C0 | Tile fire; giữ group/tag/pairing và reserve side slot |
| C1 | IN_REG align; GS pre-addsub capture (CT bypass) |
| C2 | Operand/side write; launch T sau cạnh |
| C3 | Leaf input T capture |
| C4 | Leaf T product FF1 |
| C5 | Raw T product FF2 |
| C6 | Cross/cat T hoặc packed alignment1 |
| C7 | Fused/packed-aligned T; launch m sau cạnh |
| C8 | T_hi/NZ history write; leaf input m capture |
| C9 | Leaf m product FF1 |
| C10 | Raw m product FF2 |
| C11 | Cross/cat m hoặc packed alignment1 |
| C12 | Fused/packed-aligned m; launch mq sau cạnh |
| C13 | Leaf input mq capture |
| C14 | Leaf mq product FF1 |
| C15 | Raw mq product FF2 |
| C16 | Cross/cat mq hoặc packed alignment1 |
| C17 | Fused/packed-aligned mq; T history stage cuối sẵn |
| C18 | Chốt U; consume old history stage9 |
| C19 | Chốt correction và side/tag; release side reservation |
| C20 | GS rsp; CT post-addsub stage1 |
| C21 | GS bank commit; CT rsp |
| C22 | CT bank commit |

History là10 register stage. T_hi ghi stage0 ở C8; stage9 chứa T sau C17, U lấy **giá trị cũ** của stage9 ở C18. Không dịch FIFO theo valid: shift mỗi clock, invalid có bubble. Side slot reserve C0, dữ liệu side ghi C2, đọc/chốt C19; outstanding chỉ retire tại rsp C20/C21.

Ở operand boundary C2: packet_valid và data/root/side/tag/group ổn định **trước cạnh**, side RAM và operand FF cùng chốt. Leaf nhận operand sau cạnh C2. ft_mont_pipe không tự thêm hai input FF nữa.

## 3. Pha packed

`phi_req=(edge-origin)%3`, origin là cạnh đầu sau tile CFG. Scalar nhận0, packed nhận0/1. `phi_launch=(edge-origin-2)%3` là pha của bảng sau. Cấm dùng phi_launch để điều khiển req_ready.

| phi_launch | leaf0/1 | leaf2/3 |
|---:|---|---|
| 0 | T | m |
| 1 | mq | T |
| 2 | m | mq |

T/m/mq trong cùng ô clock có thể thuộc các packet khác nhau. Xem packed_two_groups.csv cho P0,P1,P2… và cả hai quy ước pha.

## 4. FFT: offset chính xác

Mỗi butterfly có2L request beat liên tiếp. Với beat b, operand/side write tại2+b, index semantic `(b&1)*L+(b>>1)`. Native inverse cộng thêm2 clock. Sum re+im/root sum chốt tại4+2k (native inverse +2). Buffer reserve ở beat0; các beat còn lại không reserve thêm.

Program launch đầu H=7/9/13 cho W32/64/128; native inverse64 H=11. Với product p và step s, K=1/4/15: launch=H+p*K+s; early=launch−1; raw=launch+3; fused=launch+5; MAC=launch+6; combine=launch+7. Side FF và C5 T register chốt tại combine. p0 ghi partial; p1 dùng C4 tạo p0+p1; p2 đọc tổng này.

GS rsp=combine+1; CT post-addsub capture=combine+1 và rsp=combine+2. Free butterfly buffer ở combine cuối của p2, trước rsp cuối. `busy` vẫn1 nếu response chưa emit. Output order là real limbs rồi imaginary limbs.

| Profile | Period | Free buffer | Rsp offsets | Commit offsets |
|---|---:|---:|---|---|
| fft32_ct | 3 | 16 | 17, 18 | 18, 19 |
| fft32_gs | 3 | 16 | 16, 17 | 17, 18 |
| fft64_ct | 12 | 27 | 24, 25, 28, 29 | 25, 26, 29, 30 |
| fft64_ct_native | 12 | 27 | 24, 25, 28, 29 | 25, 26, 29, 30 |
| fft64_gs | 12 | 27 | 23, 24, 27, 28 | 24, 25, 28, 29 |
| fft64_gs_native | 12 | 29 | 25, 26, 29, 30 | 26, 27, 30, 31 |
| fft128_ct | 45 | 64 | 42, 46, 49, 51, 57, 61, 64, 66 | 43, 47, 50, 52, 58, 62, 65, 67 |
| fft128_gs | 45 | 64 | 41, 45, 48, 50, 56, 60, 63, 65 | 42, 46, 49, 51, 57, 61, 64, 66 |

CSV của mỗi profile có hàng cho **mọi clock**, kể cả bubble, và các cột early/launch/raw/fused/MAC/combine/side write/free/rsp/commit. L4 chỉ bỏ (3,3); giữ các cột thấp và seed rounding một lần.

## 5. C4: một adder36, port không còn width mơ hồ

u_bus34 = `{Uhi17,Ulo17}` khi packed, `{0,U33}` khi scalar. Define A36,B36,Cin; R36=(A36+B36+Cin) mod2^36:

```text
FFT: A36={4'b0,fft_a32}; B36={4'b0,fft_b32}; Cin=fft_ci
scalar: A36={3'b0,u_bus[32:0]}; B36=~{4'b0,q32}; Cin=1
packed: A36={1'b0,Uhi17,1'b1,Ulo17}
        B36={1'b0,~{1'b0,qhi16},1'b1,~{1'b0,qlo16}}; Cin=1
scalar borrow=R36[35]; result=borrow ? U33.low32 : R36.low32
packed borrow_hi=!R36[35]; borrow_lo=!R36[17]
packed result_hi=borrow_hi ? Uhi.low16 : R36[33:18]
packed result_lo=borrow_lo ? Ulo.low16 : R36[15:0]
FFT sum33=R36[32:0]; không dùng borrow.
```

Packed guard bit17 của tổng nhận carry-low; high lane luôn được +1 riêng để trừ. Scalar borrow dùng polarity khác packed vì encoding khác. C4 là tổ hợp; caller chốt U-correction C19 hoặc p0+p1 tại combine. Input mux ở trước một phép cộng36, không tạo ba bộ cộng rồi mux output.

C0 sum33, C1 difference34, C2 correction35, C3 correction34 theo bit slicing của ft_addsub tham chiếu. fs/ws33 là tổng từ các operand FFT sống; s/d là corrected/raw output của stage1 đã chốt, co_now/bo_now là carry/borrow input hiện tại. Không coi chúng cùng transaction/latency. Model addsub_bits kiểm từng slice so modulo oracle.

## 6. START, CFG và host

START ở X: X+1 local reset; X+2 local CFG; X+3 SETTLE/phase origin0; X+4 push context0; X+5 RUN. Tính theo epoch: START−3, CFG−1, ctx0 push1, first possible read2. FFT đọc từ2; NTT đầu tiên đọc4 để tile fire6 ở phi_req0. Các tầng sau push context tại first_read−1.

CFG decode capture E0, D1..D5 ở E1..E5; params/done sau E5; core capture+ack E6, frontend consume E7.

Host-map nhận line H0; PREP H1; service phase0 ở H2, phase p−1 ở H(p+1). LOAD request_done sau phase cuối, core ack cạnh kế. READ capture từng phase RAM ở cạnh kế khi có thể vẫn đang phát phase kế tiếp; G=H(p+2) là gather phase cuối. Không chờ đến G rồi chỉ lấy RAM output cuối.

READ: carry/addend G+1, sum G+2, shift/out_valid G+3, core line_rsp+ack G+4, frontend holding/read_complete G+5. Native/NTT bypass số học nhưng vẫn latency3 qua normalizer. Số phase p tính từ xung đột bank của4 word, 1..4; small-N có special case, không lấy fmt làm p một cách máy móc.

DONE chỉ sau commit cuối+1 khi queue, request/product/output và tile busy đều rỗng. Cycles32 tính từ START đến DONE cùng scope control; identity cycles0. Model numbers không thay bằng số baseline hoặc đổi mốc đếm để giấu overhead.

