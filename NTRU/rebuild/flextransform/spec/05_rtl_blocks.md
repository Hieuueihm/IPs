# 05 — Kiến trúc RTL và cấu trúc cổng

Contract0.2: port/clock/FSM đã khóa ở spec08..11; nội dung dưới là giải thích cấu trúc. Chưa có RTL implementation. Tên module/file dưới đây là kế hoạch, chưa có implementation. Không thêm FF chỉ để khớp một ô trong sơ đồ; register boundary phải xuất hiện trong latency manifest và test.

## 1. Quy ước chung

SystemVerilog synthesizable, port vector tường minh, `default_nettype none`, always_ff cho state và always_comb cho next-state. Literal phải có độ rộng/dấu rõ. Không dùng initial để khởi tạo trạng thái hoạt động, không dựa vào X=0 của mô phỏng hai trạng thái.

Các công thức cổng tương đương:

```text
MUX2(s,A,B) = (A & {W{s}}) | (B & {W{!s}}) // s?A:B
EQ(A,B)    = !OR_reduce(A XOR B)
NZ(A)      = OR_reduce(A)
p=a XOR b; g=a AND b
sum=p XOR cin; cout=g OR (p AND cin)
a-b-bi = a + NOT(b) + NOT(bi)                // tăng độ rộng trước tính
Q_next = rst ? reset_value : update ? D : Q
```

Đây là mô tả chức năng. Viết `+/-/*` đúng width để Vivado map vào carry-chain/DSP; không bắt buộc tự dựng hàng nghìn full-adder RTL. Mux chọn operand nên nằm trước arithmetic dùng chung; dựng hai arithmetic rồi mux output không chắc đã share được resource.

## 2. Danh sách module và ownership

| Module/file | Số instance | Sở hữu / trách nhiệm |
|---|---:|---|
| ft_axil_top.sv | 1 | Port AXI, MMIO registers, output holding register |
| ft_cmd_frontend.sv | 1 | Snapshot160, reservation, pipeline token, ack |
| ft_core.sv | 1 | Context kernel và nối các khối |
| ft_cfg_decode.sv | 1 | Decode cấu hình nhiều stage, params đã kiểm range |
| ft_stage_ctrl.sv | 1 | Descriptor10, stage sub-FSM, context queue, tail mask; executor FSM thuộc ft_core |
| ft_issue_ctrl.sv | 1 | k/plane/beat/phase, issue mask, stage-gap timing |
| ft_fft_program.sv | 1 | Product0/1/2 +step, early program/local fanout |
| ft_cg_addr.sv | 1 | Row/bank embedding theo params đã register |
| ft_cg_route.sv | 1 | Mux read4:1 và route write hữu hạn |
| ft_data_mem.sv | 1 | 32 bank data, mỗi bank1R/1W |
| ft_root_mem.sv | 1 | 16 root RAM; destination mask và read đồng bộ |
| ft_host_map.sv | 1 | Map/gather128, phase bank, OOB |
| ft_read_normalize.sv | 1 | Round theo word +boundary-aware arithmetic shift |
| ft_writeback.sv | 1 | Validate response mask/tag, phát write, commit event |
| ft_tile.sv | 16 | Nối/shared-resource ownership, context cục bộ, response |
| ft_leaf_array.sv | 16 | Bốn leaf16×16 +raw/fused pipeline |
| ft_addsub.sv | 16 | C0/C1 sum/diff; C2/C3 correction hoặc FFT sums |
| ft_reduce_or_sum.sv | 16 | C4: U−q hoặc p0+p1, cùng một physical chain |
| ft_mont_pipe.sv | 16 | Valid feedback, history34×10, U/correction control |
| ft_tile_state.sv | 16 | RAM operand/root/sum/side; buffer/credit |
| ft_fft_accum.sv | 16 | MAC68 và column emit, metadata FUSE |
| ft_fft_combine.sv | 16 | Điều khiển partial_sum RAM và C5 subtract cho real/imag |
| ft_native_align.sv | 16 | Bias/half64, align low/high/root/tag native inverse |

`ft_mont_pipe` và `ft_fft_combine` **không tự instantiate bản riêng C4**. Chúng trình operand/control tới `ft_reduce_or_sum` do ft_tile sở hữu; chọn owner bằng context FFT/NTT. Tương tự C2/C3 của ft_addsub phục vụ cả correction và tổng FFT. Nếu tách file làm nhân đôi chain, implementation không đạt ý đồ sharing dù output đúng.

## 3. ft_leaf_array

Ports: clk; `a[63:0],b[63:0]`, signed-select `a_signed[3:0],b_signed[3:0]`; output `raw_p[131:0]`, `fused_p[64:0]`. Raw_p là bốn trường33 bit. Module free-running; valid ở control pipeline, không reset data FF.

Mỗi leaf sign-extends input16 thành signed17 theo sign-select, nhân signed17×17 rồi giữ33 bit. Cấu hình này đủ product signed/unsigned16; packed chỉ lấy low32 của tích unsigned đầy đủ.

Mapping fused32×32:

| Leaf | A | B |
|---:|---|---|
| 0 | A.lo16 | B.lo16 |
| 1 | A.hi16 | B.hi16 |
| 2 | A.lo16 | B.hi16 |
| 3 | A.hi16 | B.lo16 |

```text
F = {P1[32:0],P0[31:0]} + (signext65(P2)<<16) + (signext65(P3)<<16)
```

Input FF +2 product FF =raw latency3; cross/cat FF +fuse FF =fused latency5. Trong packed, group0={P1.low32,P0.low32}, group1={P3.low32,P2.low32}; thêm2 alignment FF để feedback cũng latency5. Không lấy fused F làm hai tích packed.

Đo unit synth phải thấy4 DSP/tile, không thêm DSP ở reducer hay accumulator. Bất cứ biểu thức `*` mới ngoài leaf array trong profile64DSP phải được review resource.

## 4. ft_addsub và ft_reduce_or_sum

ft_addsub inputs: clk, mode_plain, split16, a/b/q32, carry/borrow cho limb và hai cặp operand tạo tổng FFT. Outputs: sum/diff32, carry/borrow, fft_sum0/1 có bit carry.

- C0: a+b+carry; C1: a−b−borrow, hoạt động đồng thời.
- Register intermediate sum33, difference có bit guard, q/control tương ứng.
- C2: sum−q khi NTT, hoặc o.re+o.im khi FFT.
- C3: difference+q khi NTT, hoặc wr+wi khi FFT.
- Mux correction theo carry/borrow của đúng lane; không lấy bit31 của residue làm signed overflow.

Packed dùng guard để cắt carry/borrow tại biên16 ở **cả hai stage**, không chỉ input. Test signed FFT carry giữa limb tách khỏi packed lane carry. Các output tổng FFT có thể được caller chốt từ operand đã register; ghi rõ latency khác với a/b→sum/diff, không tự thêm delay cho đồng dạng tên port.

ft_reduce_or_sum inputs đã register gồm owner, split, x/y, carry và q/format cần thiết; một chain cộng/trừ có guard và mux input phục vụ:

```text
owner=NTT:  candidate=U-q, chọn U/candidate theo borrow mỗi lane
owner=FFT: sum=p0+p1+carry_limb, ghi wps
```

U bus34 chứa scalar33 hoặc hai U17; C4 dùng một chain36 theo equations đã khóa ở spec09. Giữ carry FFT qua limb riêng. Không để high bit lane0 lọt sang lane1 khi correction hoặc half modular.

## 5. ft_mont_pipe

Inputs gồm accepted NTT operand/side/root/tag/pairing, raw group products và fused product. Context q/qi cố định. Outputs gồm leaf operand select, chọn T_hi, U/correction operand, response-valid/tag và side read request.

Một request qua T→m→mq với FUSE5:

| Offset từ operand stage | Việc |
|---:|---|
| 0 | Product T |
| 5 | Product m=low(T)*qi |
| 10 | Product mq=m*q |
| 15 | mq product về |
| 16 | Chốt U=Thi+mqhi+NZ |
| 17 | Chốt correction |

History34×10 lưu `{T_hi32,NZ2}`. Scalar chỉ dùng NZ của scalar; packed giữ hai bit. `group_at_T=delay5(group)`, `group_at_mq=delay15(group)` là hai thời điểm riêng. Nhóm T chọn vào history chung; nhóm mq chọn vào U đúng transaction. Không giữ history riêng theo q hoặc theo group.

Hai feedback controller packed chỉ giữ valid/select cần cho nhóm đó. Select T/m/mq được register sớm một clock; không đặt decoder qua feedback dài vào leaf input. Lịch lookup0/5/10 phải do FUSE và phase manifest quyết định.

Mục tiêu latency ban đầu, với tile input register: nhận tại cạnh C0, output **sau cạnh C21 CT hoặc C20 GS**. Unit mới phải khớp bảng đã khóa; nếu muốn đổi pipeline, tăng version và chạy lại toàn model trước integration. Consumer ghi RAM ở cạnh sau khi output đã xuất hiện, không nhầm hai mốc này.

## 6. ft_tile_state và liveness

| RAM | Tổ chức ban đầu | Vai trò |
|---|---:|---|
| side | 16×42 | FFT side hoặc NTT side/tag/pairing |
| operand | 16×32 | B hoặc A−B |
| root | 16×32 | Root beats; không phải BRAM root toàn mảng |
| operand_sum | 8×32 | Re+im của operand |
| root_sum | 8×32 | Wr+wi |
| partial_sum | 4×32 | p0 rồi p0+p1 |

Các RAM độc lập, mỗi RAM1W/clock và một read tổ hợp theo address đã register, caller chốt read khi cần. Chuyển sang sync BRAM là một thay đổi latency lớn, không phải thay attribute đơn thuần.

FFT32/64/128 chia16 side entry thành8/4/2 butterfly buffer. `buffer,beat` map lần lượt bằng nối bit `{b[2:0],k[0]}`, `{b[1:0],k[1:0]}`, `{b[0],k[2:0]}`. Separate counters: buffer nhận input, buffer đang tính, buffer/output đang giải phóng.

Native alignment giữ low/high cùng tag/root; không gộp vào side FIFO dùng chung bằng một mux rộng chưa đo. Dùng interleaved real/imag để chốt prev_real/prev_wr, tính sums ở beat kế tiếp, giữ1R cho operand/root.

NTT side pointer vòng16, một write lúc nhận, một read đúng kết quả. In-flight packed tối đa theo cửa sổ latency; model phải chứng minh count≤16, không chỉ thấy pointer wrap có vẻ đúng.

Busy dùng counter gói NTT hoặc butterfly FFT +các valid pending. Counter free-buffer có thể giảm sớm khi T cuối xong; counter outstanding chỉ giảm khi response cuối xuất ra. Không dùng chung hai counter này. cfg_valid khi busy là lỗi contract.

Sau reset, req_ready phải0 đến khi đã nhận cấu hình hợp lệ; không nhận một packet với q/mode chưa được khởi tạo. Phase origin lúc reset/config phải được định nghĩa trong latency manifest để mọi tile cùng pha khi core bắt đầu cấp dữ liệu.

## 7. FFT product program và MAC

Một program toàn mảng, output `{valid,mask16,product2,step4}`. Local register ở tile dùng program sớm để chọn LUTRAM address và signedness cho clock kế. Không để global step đi xuyên address decode và LUTRAM vào multiplier trong cùng clock.

Với L2: `(0,0),(0,1),(1,0),(1,1)`; emit limb0 ở step2, limb1 ở step3. Với L4:

```text
step:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14
i:     0  0  1  0  1  2  0  1  2  3  1  2  3  2  3
j:     0  1  0  2  1  0  3  2  1  0  3  2  1  3  2
last:  1  0  1  0  0  1  0  0  0  1  0  0  1  0  1
emit:  -  -  -  -  -  0  -  -  -  1  -  -  2  -  3
```

ft_fft_accum nhận fused65 và metadata cùng FUSE5, accumulator signed68. Arithmetic shift32 chỉ sau last-column; seed theo spec02. Emit khi valid AND column_last AND output-column, không theo step counter sống đã vượt transaction.

ft_fft_combine dùng một subtract chain C5: p1 về thì p0−p1; p2 về thì p2−(p0+p1). Carry/borrow lưu riêng cho từng phép qua limb. C4 tạo p0+p1 và ghi partial_sum. CT post-adder dùng side RAM đã chốt; GS xuất side và T. Native alignment thêm offset program tương ứng.

## 8. ft_stage_ctrl / ft_issue_ctrl

Executor FSM của ft_core: IDLE→CFG_WAIT cho CFG; IDLE→HOST_WAIT→NORM_WAIT→IDLE cho READ, LOAD kết thúc tại HOST_WAIT; đường kernel IDLE→TILE_RESET→TILE_CONFIG→SETTLE→STAGE_SETUP→RUN→DRAIN→IDLE. ERROR_ABORT→RECOVER0→RECOVER1→IDLE. Host-map có FSM riêng; bảng guard/action đầy đủ ở spec10.

IDLE/RUN là các trạng thái điều khiển, không thay thế in-flight scoreboard. RUN có read_stage và head write_stage khác nhau. `cycles` đếm từ accepted START ở executor, gồm reset/config/settle/kernel/drain; không gồm MMIO/root/load/read. Identity cycles0 là special case có test riêng.

Stage push context trước request đầu; issue_ctrl đếm k/plane/beat, rd_issue theo phase/rate. writeback nhận data/tag/mask thực, kiểm so với head context, route bank write, trả commit mask. Tail seen chỉ cập nhật từ commit, không từ product done. DRAIN không phát read mới.

Queue context depth16 đủ theo bound stages≤10 và một context kernel; mỗi tầng chỉ push một lần. Assert overflow/underflow, output stage order và terminal tag từ model. Không sinh 16 FIFO context riêng.

## 9. ft_host_map và ft_read_normalize

Host map từ một line index10/data128 tạo4 bộ bank5/row8/phase/OOB. Capture một lần, tính basis theo config trước, delta word dùng XOR. Register select trước bank service, gather đúng latency sync RAM. Mỗi phase/bank one-hot-or-zero, OR-mux chỉ hợp lệ dưới invariant này.

Normalization pipeline cho IFFT thường:

1. Gather raw128 cùng fmt/s/valid.
2. Tính rounding addend và carry xuyên word trong **từng giá trị W**, chốt line/addend/carry.
3. Bốn adder32 độc lập tạo wrapW(v+bias), chốt sum/fmt/s/valid.
4. Mux shift nhỏ0..3 rồi0/4/8/12, arithmetic sign extension trong từng W; chốt response.

Không shift cả line128 rồi cho số bên cạnh lấp bit. fmt32 ngắt mọi word boundary; fmt64 nối0↔1 và2↔3; fmt128 nối toàn bộ. s=0 bypass đúng bit. Native/NTT bypass normalization nhưng valid/line ID vẫn đi cùng data.

## 10. Reset, fanout và timing

Chỉ reset FF quyết định validity, pointer/counter/context, mode điều khiển; data FF không reset nếu luôn bị valid che đúng. Tile local reset/config qua FF, payload context cũng qua boundary tương ứng. Không reset toàn RAM/SRL để che X trong test.

Đầu tiên viết RTL không phụ thuộc DONT_TOUCH/KEEP để hoạt động đúng. Nếu synthesis xóa một pipeline cần thiết cho timing, kiểm mô tả register và đường data/control, rồi ghi rõ bất kỳ attribute giữ cấu trúc nào trong manifest. Không thêm false/multicycle path cho đường vẫn truyền dữ liệu mỗi clock.

Chỉ target 16 tile ở bản này; không advertise tham số NTILES tùy ý khi bank map, mask, tag và root controller chưa có generator tổng quát.
