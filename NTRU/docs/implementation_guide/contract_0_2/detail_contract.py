"""Implementation cards1.2. Internal register names are suggestions, not port changes."""
CARDS={}
def card(name,bindings,regs,rules):
    d={}
    for names,meaning in bindings:
        for n in names.split():
            assert n not in d,(name,n)
            d[n]=meaning
    CARDS[name]=dict(bindings=bindings,port_semantics=d,regs=regs,rules=rules)

card('ft_leaf_array',[
 ('clk','Clock duy nhất; input FF, product FF và fused FF đều lấy posedge, không clock-enable.'),
 ('a b','Bốn word16: leaf k nhận bus[16*k+:16]. Fused mapping do caller chuẩn bị, không tự hoán vị.'),
 ('a_signed b_signed','Bit k chọn signed16 cho word k; chốt đồng thời với word, hoặc chốt signed17 đã mở rộng.'),
 ('raw_p','raw_p[33*k+:33]=pp2_q[k]. Bốn product của cùng lượt launch, sau launch+3.'),
 ('fused_p','65 bit sau launch+5. Chỉ được dùng khi bốn leaf tạo đúng một tích32×32; packed dùng raw.')],
 [('ax_q[4],bx_q[4]','17 signed mỗi word','D={flag&word15,word}; mỗi clock','Không reset; L1'),('pp1_q[4]','33 mỗi leaf','D=full34[32:0]','Không reset; L2'),('pp2_q[4]','33 mỗi leaf','D=pp1_q','Không reset; L3'),('cat_q,c2_q,c3_q','65,33,33','D={P1,P0.low32},P2,P3','Không reset; L4'),('fused_q','65','D=cat+(sext65(c2)<<16)+(sext65(c3)<<16)','Không reset; L5')],
 ['Không có valid/rst/en trong interface: tile giữ token riêng. Sau reset của tile, data cũ vẫn chạy nhưng không được consume.',
  'Các bit sign-extension/zero-padding sau FF là dây. Không suy ra thêm33→65 FF cho cross products.',
  'consumer FF tại cạnh L5 chỉ nhìn fused của lượt trước; fused mới sau L5 được consumer lấy tại L6.'])

card('ft_addsub',[
 ('clk rst','Clock và reset synchronous active-high; reset out_valid, không cần reset S/D/Q payload.'),
 ('in_valid','Chốt cùng a/b/q/ci/bi/plain/split ở intermediate boundary; không là ready hoặc pause.'),
 ('a b','Operand32 sống cho C0/C1, có thể là limb FFT hoặc hai residue16 packed.'),
 ('q','Modulus32 hoặc {q_hi16,q_lo16}; register Q cùng intermediate, không đọc q sống ở correction.'),
 ('ci bi','C0 carry-in và C1 borrow-in. NTT dùng0; FFT lấy carry/borrow đúng limb trước.'),
 ('split16 plain','split16 tách lane NTT; plain=1 chọn FFT. Cả hai phải register cùng S/D.'),
 ('fa fb fci','Operand/carry phụ sống cho C2 khi plain_q1; fs=fa+fb+fci, không qua input FF ở đây.'),
 ('wa wb wci','Operand/carry phụ sống cho C3 khi plain_q1; ws=wa+wb+wci.'),
 ('s d out_valid','s/d combinational từ intermediate FF; out_valid là valid FF một tầng, consumer lấy ở cạnh sau.'),
 ('co_now bo_now','Combinational từ input hiện tại; caller chốt cùng cạnh capture limb hiện tại để dùng limb kế.'),
 ('fs ws','Tổng33 sống từ C2/C3 ở FFT; caller dùng sum-write enable riêng. out_valid không xác nhận fs/ws.')],
 [('S_q,D_q,Q_q','33,34,32','Mỗi clock lấy sum/difference/q hiện tại','Payload không reset'),('PK_q,PL_q','1+1','D=split16,plain cùng S_q/D_q','Chỉ consume khi token/config hợp lệ'),('V_q','1','rst?0:in_valid','out_valid=V_q')],
 ['Mã hóa guard và slices là bắt buộc: xem chương28. C2/C3 dùng PL_q, không dùng plain hiện tại.',
  'Không viết always_ff cho s/d thêm một tầng. Không giữ S_q khi in_valid0 nhưng vẫn chạy valid sai lịch; free-running payload là lựa chọn đơn giản.',
  'Q_q của NTT giao dịch X không được lấy từ CFG của giao dịch Y.'])

card('ft_reduce_or_sum',[
 ('fft_mode split16','fft_mode có ưu tiên chọn nhánh FFT; split16 chỉ có nghĩa khi fft_mode0.'),
 ('u_bus','Scalar {0,U33}; packed {Uhi17,Ulo17}. Không lấy high lane bằng slice31:16.'),
 ('q_word','Scalar q32, packed hai q16; mở rộng trước NOT để đủ bù hai36.'),
 ('fft_a fft_b fft_ci','Hai limb của p0/p1 và carry của tổng đó, lấy từ combine và partial RAM.'),
 ('result','Correction NTT chuẩn hóa32 hoặc low32 của tổng FFT; module không tự register.'),
 ('fft_sum','R36[32:0], chỉ có ý nghĩa FFT. Bit32 trở thành carry_sum ở caller.'),
 ('underflow','Scalar {borrow,borrow}; packed {borrow_hi,borrow_lo}; FFT00. Không báo kernel fault.')],
 [('Không có FF','0','Tạo A36/B36/CI → R36 → slice/mux','Không clk/rst/valid')],
 ['Một biểu thức cộng36 sau input mux. Không instantiate multiplier, divider hoặc ba bộ trừ theo mode.',
  'Scalar borrow R35; packed borrow !R35/!R17. Các cờ khác polarity do mã hóa khác nhau.',
  'Đường U_q→C4→corr_q nằm trong C18..C19; thêm FF tại C4 sẽ đổi contract.'])

card('ft_mont_pipe',[
 ('clk rst','Reset mọi token/valid/select cần thiết; payload alignment/history không bắt buộc reset.'),
 ('cfg_mode q_word qi_word','Context ổn định khi chạy. q/qi packed đã nhân bản low16 bởi tile.'),
 ('packet_valid group','Packet/token ở boundary C2. group chọn leaf0/1 hoặc2/3; chỉ packed mới dùng.'),
 ('operand root','Dữ liệu cho T: scalar32 hoặc hai lane16, chốt C2 để launch sau cạnh.'),
 ('side tag pairing','Dữ liệu phụ được đóng gói42 bit và ghi side RAM tại C2; không delay toàn bộ19 clock bằng FF.'),
 ('alloc_addr','Slot đã reserve tại C0 và căn theo packet tới C2. Không đọc ntt_tail mới nhất thay slot cũ.'),
 ('head_addr side_rd','Địa chỉ head do state sở hữu; side_rd42 là async read phục vụ capture C19.'),
 ('fused_p raw_p','Product từ leaf array: scalar dùng fused, packed dùng raw.low32 qua hai align FF.'),
 ('corrected','Nối từ C4.result; giá trị tổ hợp từ U_q trong C18..C19.'),
 ('leaf_a leaf_b leaf_valid','Operand candidate NTT và mask4 leaf cho owner mux ở tile. Flags signed của NTT buộc0 ở tile.'),
 ('u_bus u_valid','U_q34 và valid sau C18; tile nối tới C4, fft_mode0, split theo packed.'),
 ('side_we side_wa side_wd','WE/WA/WD tới side RAM, phải ổn định trước C2 để RAM ghi tại C2.'),
 ('side_re side_ra','Cửa sổ đọc/release trước C19; side_ra=head_addr. side_re nối state.ntt_release, không dùng corr_valid thay nó.'),
 ('corr_valid corr_data corr_side corr_tag corr_pairing','Cùng bộ FF sau C19: corrected + side_rd cũ; tile tiêu thụ C20 để GS response hoặc CT post-stage.'),
 ('fault','Vi phạm điều phối local như collision. Phase/credit ở tầng tile, không giả định mont có các input kiểm chưa tồn tại.')],
 [('operand_q,root_q','32+32','D=input tại packet C2','Không thêm input latency'),('v_age[0:16],g_age[0:15]','17+16','Shift mỗi clock; age0 chốt C2','Valid reset0; group chỉ dùng khi valid'),('pp_align1/2[2]','2×2×64','Raw packed chốt hai cạnh sau raw','Không reset payload'),('hist_q[0:9]','10×34','C8 ghi {Thi32,NZ2}, mỗi clock shift','Dữ liệu kèm bubble, không compress'),('U_q,VU_q','34+1','C18 lấy old hist9 + mq; VU age16','VU reset0'),('corr_q,side/tag/pair_q,VC_q','32+32+8+1+1','C19 lấy C4/side_rd và VU cũ','VC reset0')],
 ['Sau C2 v_age0 của X; sau C7 v_age5; sau C12 age10; sau C17 age15; sau C18 age16. C18 U FF đọc old age15, C19 correction đọc old age16.',
  'Select feedback có thể chốt tại C7 từ old age4 và C12 từ old age9; leaf input nhận lượt mới tại C8/C13. Không chốt thêm feedback data FF.',
  'group_at_T sau C7 lấy delay5 từ launch C2; mq sau C17 lấy delay15. Dùng cùng một select group cho cả hai là sai.',
  'Mỗi packet hai lane nhưng chỉ một side slot. Hai group không nhân đôi history; tối đa một T packet về mỗi clock.'])

card('ft_tile_state',[
 ('clk rst','Reset count/pointer/ownership, không clear nội dung sáu RAM.'),
 ('fmt','L=1/2/4, số buffer8/4/2; giữ ổn định khi còn state sống.'),
 ('alloc alloc_ready alloc_buf','alloc là reserve FFT thực tế; alloc_buf là ID trước cạnh, caller giữ cho toàn bộ butterfly. Không dùng alloc_ready làm global ready NTT.'),
 ('free_buf free_buf_id fft_count','Release ID tại combine p2 cuối; count4 giữ occupancy, không là outstanding đến response.'),
 ('ntt_reserve ntt_release side_count','Reserve tại request C0, release C19; side_count5 có thể bằng16. Cả hai là event tại cạnh, không mức giữ nhiều clock.'),
 ('ntt_alloc_addr ntt_head_addr','Tail/head4 bit trước cạnh, state sở hữu pointer vòng; mont/tile chỉ dùng địa chỉ đó.'),
 ('side_we side_wa side_wd side_ra side_rd','Side16×42, WE/WA/WD sync; RA→RD async. Packed/FFT dùng cùng RAM theo context.'),
 ('operand_we operand_wa operand_wd operand_ra operand_rd','Operand16×32, independent1W1R. Caller tính semantic index và địa chỉ buffer.'),
 ('root_we root_wa root_wd root_ra root_rd','Root16×32 trong tile, không phải bảng root512 của toàn core.'),
 ('operand_sum_we operand_sum_wa operand_sum_wd operand_sum_ra operand_sum_rd','Sum operand8×32, địa chỉ buffer·L+limb; write tại sum-write của caller.'),
 ('root_sum_we root_sum_wa root_sum_wd root_sum_ra root_sum_rd','Sum root8×32, cùng lifetime với operand_sum nhưng RAM/cổng riêng.'),
 ('partial_we partial_wa partial_wd partial_ra partial_rd','Partial4×32, địa chỉ limb không có buffer; p0→p0+p1→read bởi p2 theo program.'),
 ('fault','Overflow/underflow/free ID sai hoặc ownership violation được cài; lỗi phải được tile đưa lên core để abort.')],
 [('RAM payload','2336 bit logic','Sáu write-enable độc lập; async read','Không reset array'),('tail_q,head_q','4+4','+1 khi ntt reserve/release hợp lệ','Reset0'),('side_count_q','5','count+reserve-release','Reset0'),('next_fft_id_q,fft_count_q','3+4','Pointer modulo8/4/2 và count','Reset0'),('ownership state','implementation choice','Bitmap8 hoặc ID-order check theo lịch','Reset empty; không đổi port')],
 ['Các cổng địa chỉ đã là địa chỉ vật lý của RAM nhỏ; không register RA lần nữa trong module.',
  'C2 side write là sau reserve2 clock. Full+release tại C19 chỉ cho reserve mới; write mới C21 nên không overwrite dữ liệu đang capture.',
  'RAM partial đọc cũ trước cạnh và ghi mới sau NBA. Hành vi này không được thay bằng synchronous read không bù latency.'])

card('ft_fft_accum',[
 ('clk rst','MAC payload và token; reset valid/first-state để không emit dữ liệu cũ.'),
 ('launch_valid launch_meta','Token tại operand launch; meta10={buffer3,product2,limb2,emit,column_last,first}; delay đúng5 tới fused.'),
 ('fused_p','Signed65 bit pattern; sign-extend lên68 trước cộng, không zero-extend khi product âm.'),
 ('native fmt','Chọn seed0 cho native64, seed2^15/31/63 cho FFT thường; F/window theo fmt.'),
 ('limb_valid limb_data limb_meta','Output sau MAC launch+6 khi emit&&column_last; data32 và meta7={buffer3,product2,limb2}.')],
 [('meta_q/valid_q','5×(10+1)','Delay theo launch, không lấy prog sống','Valid reset0'),('acc_q,lastcol_q','68 signed+1','D=acc_in+sext(fused); giữ trạng thái column_last','Chỉ update product-valid'),('limb_q,meta_out_q,V_q','32+7+1','Lấy slice của acc_next tại MAC event','Valid reset0')],
 ['acc_in chọn first→seed, lastcol_old→ASR32(acc_q), còn lại→acc_q. first có ưu tiên hơn carry cột cũ.',
  'Ở cùng cạnh MAC chốt acc_next và limb từ acc_next; không dùng acc_q cũ làm limb nếu token yêu cầu emit.',
  'Shift32 cố định là wiring có sign extension; barrel shifter host là phần khác. W128 emit5/9/12/14.'])

card('ft_fft_combine',[
 ('clk rst','Reset token/carry/borrow theo frame; reset payload không bắt buộc.'),
 ('limb_valid limb_data limb_meta','Từ accum, meta chỉ đúng butterfly/product/limb. Không suy buffer từ counter alloc hiện tại.'),
 ('side_rd partial_rd','Async read từ state; side42 của đúng real/imag và partial32 của đúng limb.'),
 ('c4_sum','Nối C4.fft_sum; low32 ghi partial khi p1, bit32 chốt carry_sum.'),
 ('fmt','L=1/2/4 để xác định cuối limb và địa chỉ side; không đổi giữa frame.'),
 ('c4_valid c4_a c4_b c4_ci','Candidate/valid tới owner C4: p0_limb + p1_limb + carry_sum (limb0=0).'),
 ('side_ra partial_ra','Side address theo buffer + (real/imag offset) + limb; partial address chỉ limb2.'),
 ('partial_we partial_wa partial_wd','p0 ghi data, p1 ghi c4_sum.low32; p2 không ghi partial.'),
 ('t_valid t_data t_side t_tag t_last','Combine FF sau launch+7, t_data từ C5; metadata/side lấy cùng cạnh.'),
 ('release_buf release_id','Release tại capture p2 limb cuối, ID lấy từ token; khác response retire ở tile.')],
 [('carry_sum_q','1','D=C4.bit32 khi p1 limb valid','Limb0 dùng0'),('borrow_re_q,borrow_im_q','1+1','D=borrow C5 đúng product1/2','Mỗi phép reset tại limb0'),('T_q,side_q,tag_q,V_q','32+32+8+1','Capture C5 và side_rd tại combine','V reset0'),('buffer/product/limb token','3+2+2','Theo limb_meta, không thêm data stage','Metadata đúng event')],
 ['C5 A=p0,B=p1 ở product1; A=p2,B=partial_sum ở product2. borrow flag theo phép trừ33 bù hai hoặc phép trừ mở rộng nhất quán.',
  'C4 là ngoài combine, không tạo bản sao. partial read-modify-write tại p1 cần đọc giá trị trước cạnh.',
  'release_buf không làm clear T/side/tag FF; các output này còn được tile dùng sau free.'])

card('ft_native_align',[
 ('clk rst','Reset valid và trạng thái căn beat/native increment; không tiêu thụ low cũ sau reset.'),
 ('native inverse fmt','Half chỉ native&&inverse&&fmt64; bypass vẫn theo boundary đã khóa.'),
 ('raw_valid raw_xy raw_root raw_tag raw_buf raw_beat raw_first','Bundle trước pre-addsub. biased_xy cấp A+1 đúng carry theo real/imag, giữ Y và metadata của frame.'),
 ('post_valid post_sum post_diff post_root post_tag post_buf post_beat post_first','Bundle sau pre-addsub; low có thể phải giữ chờ high để shift64 đúng.'),
 ('biased_xy','Dữ liệu vào addsub sau bias; không là kết quả half.'),
 ('aligned_valid aligned_side aligned_operand aligned_root aligned_tag aligned_buf aligned_beat aligned_first','Bundle sau alignment: side=sum_half, operand=diff_half; native inverse64 thêm2 clock input.')],
 [('inc_carry_re/im','1+1','Carry increment A+1 theo limb/plane','Reset theo frame/reset'),('low_sum/low_diff + metadata','implementation split','Giữ low chờ high[0]','Valid reset0'),('aligned payload + valid','bundle theo ports','Half và root/tag cùng transaction','Không tạo normalize cuối')],
 ['Native half wrap64(v+1) trước ASR1, khác modular_half_unsigned của NTT.',
  'Low output cần high[0]; high output cần high[31] sign. Không shift từng beat độc lập.',
  'Các thanh ghi giữ low/high phải xuất hiện trong latency +2 đã khóa; không cộng thêm2 rồi vẫn giữ H11.'])

card('ft_tile',[
 ('clk rst','Reset synchronous local; core tạo thứ tự reset→config→settle, không cùng cạnh.'),
 ('cfg_valid cfg_mode cfg_inverse cfg_native cfg_fmt cfg_q cfg_qinv','Context chốt khi READY/COLD, không đổi khi BUSY; mode0 scalar,1 FFT,2 packed,3 invalid.'),
 ('req_valid req_ready','Fire tại cạnh khi cả hai1; ready kiểm configured/phase/credit, không dùng để sửa một lịch sai sau khi đã phát.'),
 ('req_data req_root req_tag req_pairing req_first','req_data={Y32,X32}; FFT beat interleaved, req_first chỉ reserve1 buffer; NTT pairing theo packet.'),
 ('prog_valid prog_product prog_step','Program early chung từ core, decode local địa chỉ/sign của lần launch kế.'),
 ('rsp_valid rsp_data rsp_tag rsp_bf_last','Output không ready. rsp_data64 là cặp kết quả32, tag8; last mỗi NTT packet hoặc imaginary limb cuối FFT.'),
 ('busy fault','busy thật gồm outstanding và pipeline pending. fault phải chặn hành vi không hợp lệ và lên core.')],
 [('cfg_q/context','width theo fields','CFG hợp lệ, không trong BUSY','Reset configured0'),('phase_q','2','Modulo3 từ origin sau CFG','Không dùng phase để suy return group'),('outstanding_q','5 hoặc đủ bound','+nhận packet/butterfly; -rsp cuối','Không dùng buffer count thay nó'),('input/side/response tokens','theo manifest','C0→C1→C2 và C19→C20/21','Reset tất cả valid')],
 ['Không có instantiated arithmetic riêng cho mode chỉ vì dễ nối. Leaf/C4/addsub owner mux nằm ở tile.',
  'CT response lấy addsub A±T; GS response lấy side_half/T. INTT root đã chứa half của nhánh T.',
  'Khi buffer đã free nhưng response còn pending, busy vẫn1 và không cho CFG mới.'])

card('ft_cfg_decode',[
 ('clk rst','FSM decode6 state và valid reset; không reset toàn bộ payload context nếu valid0.'),
 ('cfg_valid cfg_ready','fire khi cả hai1; chỉ một decode pending.'),
 ('cfg_word q qi','Full-width snapshot E0. Kiểm reserved/range trước pack/narrow; qinv là producer-supplied.'),
 ('params_valid cfg_ctx cfg_done cfg_error','Context128/done sau D5 nếu hợp lệ; lỗi báo done/error, không phát compute; core capture E6.')],
 [('snapshot_q','cfg32+q32+qi32','D=input tại E0 fire','Hold qua decode'),('derived logs','widened temporaries','D1..D4 tách n/base/bj/rj/rows','Không truncate trước range check'),('ctx_q,done_q,error_q','128+1+1','D5 kết luận hợp lệ','Pulse done, valid qualify')],
 ['cfg_error không chứng minh root sai/đúng; primality và order thuộc generator.',
  'Điều kiện hmin<logn được kiểm trước unsigned subtract. rows_per_buffer≤128 gồm cả plane/job capacity.'])

card('ft_data_mem',[
 ('clk rst','Reset rvalid; không clear array. Gating write khi abort/reset nằm ở owner/core.'),
 ('ren raddr','ren[b] chọn read bank b; raddr[8*b+:8] là row.'),
 ('wen waddr wdata','wen[b], waddr[8*b+:8], wdata[32*b+:32] tạo write commit của bank b.'),
 ('rdata rvalid','Sau cạnh read R: rdata[32*b+:32] cùng rvalid[b]; core căn metadata R+1.')],
 [('mem[32][256]','32 bit/word','1 sync read +1 write/bank','Không reset'),('rd_q,rv_q','32×32 +32','Read tại R, output sau R','rv reset0; không thêm rd FF thứ hai')],
 ['Không phụ thuộc read-first/write-first vì data BRAM same-bank/same-row RAW cùng cạnh bị cấm.',
  'Host/compute dùng owner mux trước RAM; không cho hai writer đồng thời.'])

card('ft_root_mem',[
 ('clk rst','Reset root_valid; không clear bảng root.'),
 ('compute_ren compute_addr','Enable16 riêng mỗi tile, address9 chung cho lượt read đồng bộ.'),
 ('host_we dest addr data','we[t]=host_we&&dest[t], row=addr9, wd=data32 chung; host chỉ ghi idle.'),
 ('root_data root_valid','root_data[32*t+:32] và valid[t] sau R, căn với data read cùng R.')],
 [('root_mem[16][512]','32 bit/word','Host write-mask và compute read','Không reset'),('root_rdata/root_rvalid','512+16','Sau R đồng bộ','Valid reset0')],
 ['Packed q/root đã chuyển đúng R16 ở producer; RAM không tự chuyển miền.',
  'ROOT write làm invalidate committed ở core; COMMIT không phải kiểm checksum/toán học của root.'])

card('ft_cg_addr',[
 ('cfg_ctx','Geometry128 đã range-check, không đi qua decoder lần nữa.'),
 ('read_stage read_k read_plane read_beat read_buf read_internal','Context read hiện tại để tạo row và route selects; counters thuộc issue.'),
 ('write_ctx out_tag','Context36 của output đang về và tag8 chọn word write; không lấy read_stage.'),
 ('rd_row0 rd_row1 wr_row0 wr_row1','Row8 cho hai half-bank của read/write, combinational theo geometry.'),
 ('route_near route_swap route_far route_dummy','Các select1 bit tới route, phải được core register cùng RAM latency.'),
 ('root_addr','Địa chỉ9 theo root packing của generator, root_base/mask và beat hợp lệ.')],
 [('Không có FF','0','Slice/rotate/XOR/concat tổ hợp','Không clk/rst')],
 ['Giữ n0 và width rotate đúng n/5 bit. Không cho shift âm hoặc field row chồng nhau.',
  'Không thêm FF địa chỉ trong module chỉ để giảm timing; phải dùng boundary core đã khóa.'])

card('ft_cg_route',[
 ('bank_data read_meta read_valid','Data32 bank từ RAM, meta30 của đúng lượt read, valid của cohort; không lấy mask/stage sống.'),
 ('tile_data write_ctx out_tag cfg_ctx','Response16×64 và context write để hoán vị về32 bank.'),
 ('tile_x tile_y req_meta req_valid','Hai bus16×32 và bundle meta30 đi tới route/request FF của core.'),
 ('routed_wdata','32×32 data theo write route; writeback tạo mask/address/commit tương ứng.')],
 [('Không có FF','0','Mux4 cố định theo tile, dummy0','Request FF thuộc core')],
 ['Mỗi mux chỉ có bốn nguồn đã biết. Không thay bằng variable bank index tạo crossbar32 nguồn.',
  'Valid/mask dùng cùng select như data; route write không dùng read_meta của tầng khác.'])

card('ft_fft_program',[
 ('clk rst cfg_ctx','Giữ H/K/L và state program; reset token/counter.'),
 ('accepted_first accepted_mask','Event cohort đã nhận first beat; mask16 giữ cho toàn program của butterfly.'),
 ('prog_valid prog_product prog_step prog_mask','Output early cho tile: product0/1/2 và step0..K-1; mask thuộc đúng butterfly.')],
 [('product_q,step_q','2+4','Increment step; wrap sang product','Reset state, không emit khi invalid'),('mask_q,program_valid','16+1','Latch accepted_first cohort','Hold trong frame')],
 ['L4 table emit5/9/12/14, không theo bảng ASCII draft sai vị trí.',
  'Local return metadata đi theo token ở tile, không dùng prog_step hiện tại sau5 clock.'])

card('ft_issue_ctrl',[
 ('clk rst cfg_ctx','FSM issue và counters reset; cfg cố định trong kernel.'),
 ('stage_valid stage_ready stage_id stage_desc stage_due','Handshake context tầng với deadline first-read20; snapshot khi fire.'),
 ('epoch epoch_run write_context_credit','Thời gian từ stage_ctrl, enable kernel issue và credit queue cho output tương lai.'),
 ('rd_issue active_mask k plane beat src_buf internal first','Cùng một read event: enable, index5/3/3, source buffer, special internal và first FFT beat.'),
 ('stage_issue_done done_stage','Pulse tại last read tầng cũ, dù cùng cạnh nhận tầng mới.')],
 [('stage snapshot','id4+desc46+due20','Load khi stage_valid&&stage_ready','Hold đến hết tầng'),('k/plane/beat counters','5+3+3','Tiến đúng read event','Reset khi nhận tầng'),('state_q','encoding choice','EMPTY/WAIT_DUE/ISSUE','Reset EMPTY')],
 ['Scheduled stage_ready chỉ EMPTY hoặc last-read-lookahead. Không tự dời deadline để tránh fault.',
  'Phi_req và phi_launch khác2 clock; read được đặt trước tile accept2 clock.'])

card('ft_stage_ctrl',[
 ('clk rst cfg_ctx','Stage FSM/epoch/queue; cfg đã decode giữ trong kernel.'),
 ('kernel_begin epoch_reset activate_first','Bắt đầu lifecycle, origin epoch và activation đầu theo executor; không đồng nhất ba pulse.'),
 ('desc_we desc_stage desc_data','Ghi descriptor10×46 khi idle; stage index4 phải0..9 trước narrow.'),
 ('issue_stage_ready issue_stage_done done_stage','Handshake/last-read của issue, xác định đúng context cũ khi đổi tầng.'),
 ('tail_commit fault','Mask16 các terminal write vừa commit, và abort/fault qualification từ core.'),
 ('stage_valid stage_id stage_desc stage_due','Context tầng phát đúng first_read-1, không là queue tùy ý có thể stall vô hạn.'),
 ('epoch','Counter20 mốc0 sau tile CFG, tách cycle32 ở core.'),
 ('write_context_credit write_ctx_valid write_ctx','Queue16×36; head/next lookahead cấp writeback không thêm bubble.'),
 ('all_reads_issued contexts_empty stage_fault','Hết read khác hết output. stage_fault khi deadline/queue/lifecycle vi phạm.')],
 [('desc_ram','10×46','Host write/prefetch','Data không reset'),('ctx_ram,head_q,next_q','16×36 +2×36','Push/pop/lookahead/bypass','Valid/count reset0'),('ctx_count/headptr/tailptr','5+4+4','Update từ event hợp lệ','Không wrap full count'),('epoch_q,tail_seen_q','20+16','Epoch run; accumulate terminal commit','Reset kernel/state')],
 ['all_tail xét (old_seen|tail_commit)&active_mask trước pop. Pop không chờ tile0 nếu tile0 không active.',
  'Count2 pop+push cần bypass incoming vào next; đọc backing RAM có thể đang là vị trí vừa overwrite.'])

card('ft_writeback',[
 ('clk rst cfg_ctx','Clock/control state theo tích hợp, không tự thêm full-width write pipeline.'),
 ('write_ctx_valid write_ctx','Head36 của tầng output; owner chọn tag tham chiếu, active mask kiểm mọi tile.'),
 ('tile_valid tile_data tile_tag tile_bf_last','16 response bundle: data64/tile, tag8/tile và terminal flag/tile.'),
 ('wr_row0 wr_row1 routed_wdata','Row của write context và data đã route; không chọn từ read stage hiện tại.'),
 ('abort_req','Chặn write ngay theo priority abort trước fault/normal, không đợi response drain.'),
 ('wen waddr wdata','Bank commit bus32 enable,8 bit row/bank,32 bit data/bank.'),
 ('tail_commit','Mask terminal của write sẽ commit ở cạnh hiện tại, cùng gating với wen.'),
 ('fault out_tag','fault khi cohort/context/tag sai; out_tag chung từ owner hợp lệ để cg_addr/route tạo write mapping.')],
 [('Control diagnostics','implementation choice','Không cần payload write FF mới','Reset fault/valid theo core'),('tail tracking','state ở stage_ctrl','tail_commit là event sang stage','Không duplicate queue ở writeback')],
 ['Không instantiate FF wdata1024 thêm; tile response sau E phải đến bank commit E+1.',
  'out_tag lấy từ owner đã lưu trong context; không chọn từ tile0 bất kể mask.'])

card('ft_host_map',[
 ('clk rst','Reset phase/gather valid, không cần clear payload cũ khi không valid.'),
 ('req_valid req_ready is_read line data cfg_ctx','Snapshot H0: read/write, line10 và payload128; giữ không phụ thuộc live pins.'),
 ('bank_rdata bank_rvalid','Read result của phase cũ, bank word32 và valid từng bank; capture bằng selector pipeline.'),
 ('ren raddr wen waddr wdata','Bốn word được phân phase1..4, mỗi bank tối đa1 access/phase.'),
 ('gather_valid gather_data','Line128 đủ mọi phase sau G; chỉ có ý nghĩa cho READ.'),
 ('request_done fault','LOAD xong tại write phase cuối; READ xong gather; fault OOB/mapping/valid sai.')],
 [('line/data/is_read snapshot','10+128+1','H0 fire','Hold đến transaction xong'),('phase map/selector','bounded arrays4 word','H1 prep; latch selector từng read','Valid reset0'),('gather_q','128','Chỉ ghi word thuộc phase trả về','Không overwrite word phase trước'),('FSM/phase_q','4 states +phase2','H2..H(p+1), GATHER cuối','Reset IDLE')],
 ['G=H(p+2). Chốt phase j-1 khi issue phase j, không đợi cuối rồi đọc output RAM cuối cho mọi word.',
  'p phụ thuộc bank conflicts thực, không đơn giản bằng L hoặc fmt.'])

card('ft_read_normalize',[
 ('clk rst in_valid','Pipeline3 stage, reset mọi valid; không clear toàn line payload.'),
 ('line_data fmt shift normalize','Bundle đầu vào G: format32/64/128, s0..9, enable normalize. Native/NTT normalize0 nhưng cùng latency.'),
 ('out_valid data','Line chuẩn hóa sau3 clock; core chốt G+4. Không ghi ngược vào data RAM.')],
 [('bias/carry/fmt/s/v1','bundle stage1','G+1 từ gather và config','V1 reset0'),('sum_wrap/fmt/s/v2','128 +metadata','G+2 cộng trong biên từng W','V2 reset0'),('data_q,v3','128+1','G+3 arithmetic shift hoặc bypass','V3 reset0')],
 ['Wrap xảy ra trước ASR. s0 không được tạo biểu thức dịch với s-1 âm.',
  'Trong một line có4 dấu độc lập ở fmt32 hoặc2 dấu ở fmt64. Không lấy sign bit127 cho mọi số.'])

card('ft_core',[
 ('clk rst','Executor/reset toàn core, clear context valid; array giữ nguyên.'),
 ('cmd_valid cmd_ready cmd_op cmd_payload','Command160 snapshot từ frontend; fire một lần, không đọc MMIO sống.'),
 ('abort_req abort_ack','Soft reset bypass; flush/suppress write, RECOVER0/1 rồi ack, không là normal queued command.'),
 ('ack_valid ack_error','Pulse đã apply hoặc từ chối command; START ack không chờ kernel_done.'),
 ('line_rsp_valid line_rsp_data','Line128 READ đã gather/normalize, đi cùng ack để frontend latch output nguyên tử.'),
 ('kernel_busy kernel_done kernel_error kernel_cycles','Trạng thái kernel thật và cycle32; host/CFG không giả làm busy kernel.'),
 ('cfg_available load_available read_available','Availability đã qualify theo lifecycle/config và quyền command; frontend còn xét pending reservation.')],
 [('state_q','13 states, encoding choice','Priority abort/fault/command theo fsm.json','Reset RECOVER0'),('configured,roots_committed,desc_valid','1+1+10','CFG invalidate, root write invalidate commit','Reset0'),('kernel_active,cycles_q','1+32','START set; count old active gồm DONE edge','Identity0'),('local cfg/reset/route FF','theo boundary','X+1 reset, X+2 cfg; route R+1','Reset mọi token')],
 ['drained gồm last commit đã xảy ra, queue empty, tile busy0 và các pipeline rỗng. all_reads_issued không đủ.',
  'Core không giữ FSM host phase hoặc stage FSM thứ hai; chỉ executor ownership.'])

card('ft_cmd_frontend',[
 ('clk rst','Reset reservation/status/token; bus B/R reset ở axil_top, soft reset không clear bus response.'),
 ('mmio_valid mmio_ready mmio_op mmio_payload','Enqueue normal command khi FREE và availability hợp lệ; snapshot160 tại nhận.'),
 ('soft_reset clear_status','RESET bypass sang abort; ACK clear done/read_complete ở bridge, không normal command.'),
 ('core_cmd_ready core_ack_valid core_ack_error','Core handshake và ack-qualified error, chờ đúng token cũ.'),
 ('core_abort_ack','Kết thúc ABORT_WAIT, release reservation và context status theo priority reset.'),
 ('core_line_valid core_line_data','READ output128 được capture cùng core ack, không phụ thuộc AXI AR/R handshake.'),
 ('core_busy core_done core_error core_cycles','Trạng thái kernel từ core. Lỗi chỉ lấy khi core_done&&core_error hoặc core_ack&&ack_error.'),
 ('core_cfg_available core_load_available core_read_available','Đầu vào availability từ core, còn phải kết hợp state/pending để tạo ready ra MMIO.'),
 ('cmd_valid cmd_op cmd_payload','Token P1 giữ nguyên op/payload đến fire, không trôi dữ liệu trong stall.'),
 ('abort_req','Pulse1 clock trong ABORT_SEND, không giữ cao toàn ABORT_WAIT.'),
 ('pending done_sticky error_sticky read_complete','Status FF với ưu tiên clear/set riêng; pending giữ tới ack hoặc abort_ack.'),
 ('output_line cycles cfg_ready load_ready read_ready','Holding line128/cycle32 và availability đã qualify để MMIO đọc/nhận lệnh.')],
 [('snapshot/op/token','160+4+valid','Enqueue→P0→P1 hold→WAIT_ACK','Reset pending0'),('sticky status','done/error/read_complete','Ưu tiên theo spec10','Reset/accepted CFG/START clear theo cờ'),('output_line_q','128','READ line+ack nguyên tử','Giữ khi chưa READ mới'),('abort state','2 states trong FSM6','ABORT_SEND pulse→WAIT','Không reset bus slots')],
 ['core_error mức cao cũ không được liên tục set lại error sau clear; qualify theo completion/ack.',
  'Accepted CFG/START clear thắng old completion; nếu chỉ ACK clear cùng new completion thì new completion thắng.'])

card('ft_axil_top',[
 ('aclk aresetn','AXI clock và reset ngoài active-low; chuyển reset nội bộ theo policy synchronous một clock.'),
 ('s_axi_awaddr s_axi_awprot s_axi_awvalid s_axi_awready','AW slot độc lập W: giữ address12 khi handshake; prot không tự tạo tính năng security.'),
 ('s_axi_wdata s_axi_wstrb s_axi_wvalid s_axi_wready','W slot giữ data32/strb4 khi handshake, không đòi AW đã đến.'),
 ('s_axi_bresp s_axi_bvalid s_axi_bready','B response giữ đến ready. B xác nhận write/enqueue, không kernel done.'),
 ('s_axi_araddr s_axi_arprot s_axi_arvalid s_axi_arready','Read-address handshake snapshot giá trị register đọc, kể cả status thay đổi sau đó.'),
 ('s_axi_rdata s_axi_rresp s_axi_rvalid s_axi_rready','R holding32/resp, giữ nguyên khi stall; soft RESET không hạ response đã phát.')],
 [('AW slot','12+valid','AW fire→full, commit→empty','Chỉ bus reset clear'),('W slot','32+4+valid','W fire→full, commit→empty','Chỉ bus reset clear'),('B/R holding','resp2+valid; data32+resp2+valid','Commit/read capture; hold đến ready','Soft reset giữ'),('MMIO register file','map3.1','Byte-mask merge mỗi accepted write','Theo register reset policy')],
 ['Write commit chỉ một lần khi đủ AW/W và B có chỗ; không lặp command trong lúc B stall.',
  'Một outstanding write và read. Không ghép AW cũ với W mới sau bus reset; invalid/unaligned/multiple command trả lỗi.'])

# Explicit inter-module wire groups. Paths are instance roles inside one tile/core.
TILE_WIRES=[
 ('leaves.raw_p','mont.raw_p','132','Direct; packed alignment2 ở mont, không ở leaf'),
 ('leaves.fused_p','mont.fused_p / accum.fused_p','65','Fanout dữ liệu; valid riêng theo mode'),
 ('mont.leaf_a/b','owner mux → leaves.a/b','64 mỗi bus','NTT scalar/packed candidate; không signed'),
 ('FFT operand/root RAM read','owner mux → leaves.a/b','4×16 mỗi bus','Fused map low/high; signed-select theo top limb'),
 ('mont.u_bus','C4.u_bus','34','C18 U register tới C4 tổ hợp'),
 ('combine.c4_a/b/ci','C4.fft_a/b/ci','32/32/1','C4.fft_mode=FFT context; C4.split16=packed context'),
 ('C4.result','mont.corrected','32','Không thêm FF; mont chốt C19'),
 ('C4.fft_sum','combine.c4_sum','33','Không thêm FF; combine chốt partial/carry tại p1'),
 ('mont.side_we/wa/wd','state.side_we/wa/wd (owner mux)','1/4/42','NTT write C2; FFT producer là owner khác'),
 ('mont.side_ra / combine.side_ra','owner mux → state.side_ra','4','Chọn theo context, không cả hai reader cùng lúc'),
 ('state.side_rd','mont.side_rd / combine.side_rd','42','Async read; consumer register đúng event'),
 ('mont.side_re','state.ntt_release','1','Trước cạnh C19, không dùng corr_valid sau cạnh thay thế'),
 ('state.ntt_head_addr','mont.head_addr','4','Head cũ trước release'),
 ('state.ntt_alloc_addr','reserve slot FF ở tile → mont.alloc_addr','4','C0 giữ slot, căn đến packet boundary C2'),
 ('combine.partial_ra/we/wa/wd','state.partial_*','2/1/2/32','RAM của state, không tạo RAM thứ hai'),
 ('state.partial_rd','combine.partial_rd','32','Old p0 tại p1; old sum tại p2'),
 ('combine.release_buf/id','state.free_buf/free_buf_id','1/3','Combine p2 limb cuối, không ở rsp cuối'),
 ('accum.limb_valid/data/meta','combine.limb_valid/data/meta','1/32/7','MAC launch+6 → combine launch+7'),
 ('mont.corr_* / combine.t_*','tile post-stage → rsp_*','data/tag/valid','CT qua addsub; GS qua side/T; rsp không backpressure')]

CORE_WIRES=[
 ('axil MMIO enqueue','frontend.mmio_*','4/160/valid-ready','Snapshot giữ trước khi core nhận'),
 ('frontend.cmd_*','core.cmd_*','4/160/valid-ready','Normal command P1 hold đến fire'),
 ('frontend.abort_req','core.abort_req','1','Bypass queue; pulse1 clock'),
 ('core.ack/line/kernel/status','frontend.core_*','theo ports','ACK command khác DONE kernel'),
 ('cfg_decode.cfg_ctx','core snapshot → stage/issue/program/address','128','Không broadcast tất cả128 bit tới FF arithmetic'),
 ('stage.stage_*','issue.stage_*','id4/desc46/due20','Stage activation first_read-1'),
 ('issue.stage_done/done_stage','stage.issue_stage_done/done_stage','1/4','Done read tầng cũ, không compute complete'),
 ('issue read indices','cg_addr.read_*','4/5/3/3/buf/internal','Read context'),
 ('cg_addr root/rows/select','RAM request + metadata FF','9/8/select','R read; metadata căn RAM output'),
 ('data.rdata/rvalid + root.root_data/valid','cg_route → request FF trong core','1024/32 +512/16','Route R+1, tile fire R+2'),
 ('program.prog_*','local program FF ở tile active','product2/step4/mask16','Early decode trước launch'),
 ('tile.rsp_*','writeback.tile_* / route.tile_data','16×64/8/valid/last','Output reserve trước, không có rsp_ready'),
 ('stage.write_ctx','cg_addr/cg_route/writeback.write_ctx','36+valid','Write context tách read context'),
 ('writeback.out_tag','cg_addr/cg_route.out_tag','8','Từ owner của head, không tile0 cứng'),
 ('route.routed_wdata','writeback.routed_wdata','1024','Data mux; writeback qualify mask/address'),
 ('writeback.wen/waddr/wdata','owner mux → data memory write','32/256/1024','Commit sau rsp1 clock'),
 ('writeback.tail_commit','stage.tail_commit','16','Cùng cạnh bank commit thật'),
 ('host_map ren/wen/addr/data','owner mux → data memory','theo ports','Chỉ host khi compute idle'),
 ('host_map.gather_*','normalizer.line_data/in_valid','128/1','Gather đủ phase; không normalize trong RAM'),
 ('normalizer.out_valid/data','core READ ack/line_rsp','1/128','Core G+4; frontend G+5')]
