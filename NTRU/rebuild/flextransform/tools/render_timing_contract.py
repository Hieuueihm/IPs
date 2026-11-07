"""Generate every-clock CSVs and the normative edge ledger from timing.json."""
import csv
import json
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]

def main():
    t=json.loads((HERE/'microarchitecture/timing.json').read_text());out=HERE/'microarchitecture/cycles';out.mkdir(exist_ok=True)
    fields=['edge','request_beat','operand_write','sum_write','early_program','launch','raw','fused','mac','combine','buffer_free','rsp','bank_commit']
    for name,p in t['fft'].items():
        rows=[{k:'' for k in fields} for _ in range(p['outputs'][-1]['commit']+1)]
        for c,r in enumerate(rows):r['edge']=c
        for c in p['input_edges']:rows[c]['request_beat']=str(c)
        for j,c in enumerate(p['operand_write_edges']):rows[c]['operand_write']=str(j)
        for j,c in enumerate(p['sum_write_edges']):rows[c]['sum_write']=str(j)
        for e in p['steps']:
            for f,key in [('early','early_program'),('launch','launch'),('raw','raw'),('fused','fused'),('mac','mac'),('combine','combine')]:
                # Every product reaches MAC, but non-emitting columns do not write combine state.
                if f=='combine' and not e['emit']:continue
                rows[e[f]][key]=f'p{e["product"]}:s{e["step"]}'+(f':limb{e["limb"]}' if f=='combine' else '')
        rows[p['release_edge']]['buffer_free']='1'
        for e in p['outputs']:
            value=('re' if e['product']==1 else 'im')+str(e['limb'])
            rows[e['rsp']]['rsp']=value;rows[e['commit']]['bank_commit']=value
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
    ntt_actions={0:'Tile fire; giữ group/tag/pairing và reserve side slot',1:'IN_REG align; GS pre-addsub capture (CT bypass)',2:'Operand/side write; launch T sau cạnh',3:'Leaf input T capture',4:'Leaf T product FF1',5:'Raw T product FF2',6:'Cross/cat T hoặc packed alignment1',7:'Fused/packed-aligned T; launch m sau cạnh',8:'T_hi/NZ history write; leaf input m capture',9:'Leaf m product FF1',10:'Raw m product FF2',11:'Cross/cat m hoặc packed alignment1',12:'Fused/packed-aligned m; launch mq sau cạnh',13:'Leaf input mq capture',14:'Leaf mq product FF1',15:'Raw mq product FF2',16:'Cross/cat mq hoặc packed alignment1',17:'Fused/packed-aligned mq; T history stage cuối sẵn',18:'Chốt U; consume old history stage9',19:'Chốt correction và side/tag; release side reservation',20:'GS rsp; CT post-addsub stage1',21:'GS bank commit; CT rsp',22:'CT bank commit'}
    for inv in (0,1):
        with (out/('ntt_gs.csv' if inv else 'ntt_ct.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['edge','action'])
            for c in range(22 if inv else 23):w.writerow([c,ntt_actions[c]])
    # A filled/bubbling two-group stream; both phase conventions are explicit.
    with (out/'packed_two_groups.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['edge','phi_req','phi_launch','accept','group0_launch','group1_launch','U','side_read','rsp_ct','commit_ct'])
        accepts=[3*(i//2)+i%2 for i in range(8)]
        for c in range(accepts[-1]+23):
            launch=['','']
            for i,A in enumerate(accepts):
                for off,op in [(2,'T'),(7,'m'),(12,'mq')]:
                    if c==A+off:assert not launch[A%3];launch[A%3]=f'P{i}:{op}'
            labels=lambda off:','.join(f'P{i}' for i,A in enumerate(accepts) if c==A+off)
            w.writerow([c,c%3,(c-2)%3,labels(0),*launch,labels(18),labels(19),labels(21),labels(22)])
    md=['# 09 — Lịch từng clock và guard bit đã khóa (0.2)','','Nguồn máy đọc: `microarchitecture/timing.json`; bảng đầy đủ mọi cạnh nằm trong `microarchitecture/cycles/`. Sinh lại bằng tools/render_timing_contract.py. Những con số này là **contract thiết kế**, chưa phải latency đo trên RTL mới.','',
      '## 1. Mốc cạnh duy nhất','','C0 là cạnh request tile fire. Tín hiệu tạo **sau** cạnh Cn chỉ được consumer lấy ở Cn+1. “Launch sau Cn” là operand/mux đã ổn định sau Cn; leaf input FF chốt ở Cn+1. Raw product sau Cn+3, fused sau Cn+5. Không gọi launch là cạnh leaf capture.','',
      'Bank/root read chốt tại R0, route/request FF tại R0+1, tile fire tại R0+2. Tile rsp tạo sau E, bank commit tại E+1. Không thêm full-width write FF trong version0.2. Nếu thêm, đổi version, planner, gap và model; không tự bù bằng shift valid.','',
      '## 2. NTT scalar và từng nhóm packed','','| Cạnh từ fire | Hoạt động |','|---:|---|']
    md += [f'| C{c} | {a} |' for c,a in ntt_actions.items()]
    md += ['', 'History là10 register stage. T_hi ghi stage0 ở C8; stage9 chứa T sau C17, U lấy **giá trị cũ** của stage9 ở C18. Không dịch FIFO theo valid: shift mỗi clock, invalid có bubble. Side slot reserve C0, dữ liệu side ghi C2, đọc/chốt C19; outstanding chỉ retire tại rsp C20/C21.', '',
      'Ở operand boundary C2: packet_valid và data/root/side/tag/group ổn định **trước cạnh**, side RAM và operand FF cùng chốt. Leaf nhận operand sau cạnh C2. ft_mont_pipe không tự thêm hai input FF nữa.', '',
      '## 3. Pha packed','','`phi_req=(edge-origin)%3`, origin là cạnh đầu sau tile CFG. Scalar nhận0, packed nhận0/1. `phi_launch=(edge-origin-2)%3` là pha của bảng sau. Cấm dùng phi_launch để điều khiển req_ready.', '',
      '| phi_launch | leaf0/1 | leaf2/3 |','|---:|---|---|','| 0 | T | m |','| 1 | mq | T |','| 2 | m | mq |','',
      'T/m/mq trong cùng ô clock có thể thuộc các packet khác nhau. Xem packed_two_groups.csv cho P0,P1,P2… và cả hai quy ước pha.', '',
      '## 4. FFT: offset chính xác','','Mỗi butterfly có2L request beat liên tiếp. Với beat b, operand/side write tại2+b, index semantic `(b&1)*L+(b>>1)`. Native inverse cộng thêm2 clock. Sum re+im/root sum chốt tại4+2k (native inverse +2). Buffer reserve ở beat0; các beat còn lại không reserve thêm.', '',
      'Program launch đầu H=7/9/13 cho W32/64/128; native inverse64 H=11. Với product p và step s, K=1/4/15: launch=H+p*K+s; early=launch−1; raw=launch+3; fused=launch+5; MAC=launch+6; combine=launch+7. Side FF và C5 T register chốt tại combine. p0 ghi partial; p1 dùng C4 tạo p0+p1; p2 đọc tổng này.', '',
      'GS rsp=combine+1; CT post-addsub capture=combine+1 và rsp=combine+2. Free butterfly buffer ở combine cuối của p2, trước rsp cuối. `busy` vẫn1 nếu response chưa emit. Output order là real limbs rồi imaginary limbs.', '',
      '| Profile | Period | Free buffer | Rsp offsets | Commit offsets |','|---|---:|---:|---|---|']
    for name,p in t['fft'].items():md.append(f'| {name} | {p["period"]} | {p["release_edge"]} | '+', '.join(str(x['rsp']) for x in p['outputs'])+' | '+', '.join(str(x['commit']) for x in p['outputs'])+' |')
    md += ['', 'CSV của mỗi profile có hàng cho **mọi clock**, kể cả bubble, và các cột early/launch/raw/fused/MAC/combine/side write/free/rsp/commit. L4 chỉ bỏ (3,3); giữ các cột thấp và seed rounding một lần.', '',
      '## 5. C4: một adder36, port không còn width mơ hồ','','u_bus34 = `{Uhi17,Ulo17}` khi packed, `{0,U33}` khi scalar. Define A36,B36,Cin; R36=(A36+B36+Cin) mod2^36:', '',
      '```text','FFT: A36={4\'b0,fft_a32}; B36={4\'b0,fft_b32}; Cin=fft_ci',
      'scalar: A36={3\'b0,u_bus[32:0]}; B36=~{4\'b0,q32}; Cin=1',
      'packed: A36={1\'b0,Uhi17,1\'b1,Ulo17}',
      '        B36={1\'b0,~{1\'b0,qhi16},1\'b1,~{1\'b0,qlo16}}; Cin=1',
      'scalar borrow=R36[35]; result=borrow ? U33.low32 : R36.low32',
      'packed borrow_hi=!R36[35]; borrow_lo=!R36[17]',
      'packed result_hi=borrow_hi ? Uhi.low16 : R36[33:18]',
      'packed result_lo=borrow_lo ? Ulo.low16 : R36[15:0]',
      'FFT sum33=R36[32:0]; không dùng borrow.', '```','',
      'Packed guard bit17 của tổng nhận carry-low; high lane luôn được +1 riêng để trừ. Scalar borrow dùng polarity khác packed vì encoding khác. C4 là tổ hợp; caller chốt U-correction C19 hoặc p0+p1 tại combine. Input mux ở trước một phép cộng36, không tạo ba bộ cộng rồi mux output.', '',
      'C0 sum33, C1 difference34, C2 correction35, C3 correction34 theo bit slicing của ft_addsub tham chiếu. fs/ws33 là tổng từ các operand FFT sống; s/d là corrected/raw output của stage1 đã chốt, co_now/bo_now là carry/borrow input hiện tại. Không coi chúng cùng transaction/latency. Model addsub_bits kiểm từng slice so modulo oracle.', '',
      '## 6. START, CFG và host','','START ở X: X+1 local reset; X+2 local CFG; X+3 SETTLE/phase origin0; X+4 push context0; X+5 RUN. Tính theo epoch: START−3, CFG−1, ctx0 push1, first possible read2. FFT đọc từ2; NTT đầu tiên đọc4 để tile fire6 ở phi_req0. Các tầng sau push context tại first_read−1.', '',
      'CFG decode capture E0, D1..D5 ở E1..E5; params/done sau E5; core capture+ack E6, frontend consume E7.','',
      'Host-map nhận line H0; PREP H1; service phase0 ở H2, phase p−1 ở H(p+1). LOAD request_done sau phase cuối, core ack cạnh kế. READ capture từng phase RAM ở cạnh kế khi có thể vẫn đang phát phase kế tiếp; G=H(p+2) là gather phase cuối. Không chờ đến G rồi chỉ lấy RAM output cuối.', '',
      'READ: carry/addend G+1, sum G+2, shift/out_valid G+3, core line_rsp+ack G+4, frontend holding/read_complete G+5. Native/NTT bypass số học nhưng vẫn latency3 qua normalizer. Số phase p tính từ xung đột bank của4 word, 1..4; small-N có special case, không lấy fmt làm p một cách máy móc.', '',
      'DONE chỉ sau commit cuối+1 khi queue, request/product/output và tile busy đều rỗng. Cycles32 tính từ START đến DONE cùng scope control; identity cycles0. Model numbers không thay bằng số baseline hoặc đổi mốc đếm để giấu overhead.','']
    (HERE/'spec/09_locked_cycles.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('CLOCK_TABLES_EMITTED',len(t['fft'])+3)
if __name__=='__main__':main()
