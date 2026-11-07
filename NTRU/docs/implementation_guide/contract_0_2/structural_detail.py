"""Pin-level detail sheets1.2; internal net names are reference implementation choices."""
from reportlab.graphics.shapes import String, Line, Polygon
from structural import Circuit, SHEETS, sheet, TEAL, NAVY, AMBER

class Pins(Circuit):
    def __init__(self,title,height=420):
        super().__init__(title,height); self.pinmap={}
    def port(self,node,name,side,fraction=.5):
        self.pinmap[(node,name)]=(side,fraction);return '@'+name
    def point(self,key,side):
        if not side.startswith('@'):return super().point(key,side)
        sd,f=self.pinmap[(key,side[1:])];n=self.nodes[key];x,y,w,h=(n[k] for k in ['x','y','w','h'])
        return {'L':(x,y+h*f),'R':(x+w,y+h*f),'T':(x+w*f,y),'B':(x+w*f,y+h)}[sd]
    def drawing(self):
        d=super().drawing()
        for (key,name),(side,f) in self.pinmap.items():
            x,y=self.point(key,'@'+name);yy=self.height-y
            if side=='L':xx=x+6;anchor='start';ty=yy+4
            elif side=='R':xx=x-6;anchor='end';ty=yy+4
            elif side=='T':xx=x;anchor='middle';ty=yy-14
            else:xx=x;anchor='middle';ty=yy+5
            d.add(String(xx,ty,name,fontName='VN',fontSize=10.5,fillColor=TEAL,textAnchor=anchor))
            if name=='CLK' and side=='L':
                d.add(Polygon([x,yy-5,x+7,yy,x,yy+5],fillColor=None,strokeColor=AMBER,strokeWidth=1.2))
        return d
    def ff(self,key,x,y,w,h,width):
        self.node(key,x,y,w,h,f'{key}\nFF[{width}]',kind='box')
        self.port(key,'D','L',.25);self.port(key,'Q','R',.25);self.port(key,'CLK','L',.85)
        return key

c=Pins('Leaf sign extension pins',420)
c.pin('word',10,35,'a[15:0]',w=135);c.pin('msb',10,165,'a[15]',w=135);c.pin('flag',10,275,'a_signed[k]',w=150)
c.gate('sg',230,195,'AND','sign17');c.node('concat',410,35,205,155,'CONCAT17','{sign17,a[15:0]}')
c.port('concat','word16','L',.23);c.port('concat','sign1','L',.78);c.port('concat','out17','R',.5)
c.ff('ax_q',735,35,195,155,17);c.pin('clk',470,300,'clk',w=95)
c.edge('word','concat',ds='@word16');c.edge('msb','sg',ds='I0');c.edge('flag','sg',ds='I1')
c.edge('sg','concat',ds='@sign1');c.edge('concat','ax_q',ss='@out17',ds='@D',label='17',pos=(675,77))
c.edge('clk','ax_q',ds='@CLK',via=[(680,317),(680,167)],control=True)
c.text(20,390,'D ax_q = {a_signed[k] & a[16*k+15], a[16*k+:16]}; không EN, không reset payload.',15)
sheet('D01','Leaf: từng chân sign, D, Q và CLK','ft_leaf_array',c,'a16 unsigned FFFF→0_FFFF=65535; signed FFFF→1_FFFF=-1.','Capture L1. Sign và word được chốt cùng cạnh, bx_q tương tự.',
 ['Lặp cho b và4 leaf. Q của ax_q/bx_q cấp signed multiplier; không dùng signed_select sống sau L1.',
  'Tên ax_q là gợi ý. D/Q/CLK là chân primitive nội bộ, không phải port mới của ft_leaf_array.'])

c=Pins('Leaf product register pins',420)
c.pin('ax',10,25,'ax_q[16:0]',w=150);c.pin('bx',10,145,'bx_q[16:0]',w=150)
c.node('dsp',250,25,220,180,'DSP48E1','signed17 × signed17','dsp')
c.port('dsp','A25','L',.2);c.port('dsp','B18','L',.7);c.port('dsp','P48','R',.5)
c.node('slice',535,70,140,90,'SLICE','full34[32:0]')
c.ff('pp1_q',725,25,120,180,33);c.ff('pp2_q',880,25,115,180,33)
c.edge('ax','dsp',ds='@A25');c.edge('bx','dsp',ds='@B18');c.edge('dsp','slice',ss='@P48');c.edge('slice','pp1_q',ds='@D');c.edge('pp1_q','pp2_q',ss='@Q',ds='@D')
c.pin('clk',470,310,'clk',w=100)
for reg,x in [('pp1_q',690),('pp2_q',855)]:c.edge('clk',reg,ds='@CLK',via=[(x,327),(x,178)],control=True)
c.text(20,375,'A25={{8{ax_q[16]}},ax_q}; B18={bx_q[16],bx_q}; phần product dư chỉ là sign-extension.',15)
sheet('D02','Leaf: sign-extend tới DSP và hai product FF','ft_leaf_array',c,'Multiplier25×18 cho43 bit, sign-extend trong P48; full34=low34(P48), raw33=full34[32:0].','pp1 capture L2, pp2 capture L3; raw_p lane lấy Q pp2_q trực tiếp.',
 ['DSP trên hình là mục tiêu inference, không khẳng định mọi input/product FF đều đã được mapper hấp thụ vào DSP.',
  'Không thêm output raw FF; pp2_q chính là register output. Q sau L3 chỉ được consumer FF lấy tại L4.'])

c=Pins('Fused explicit adds',420)
c.pin('cat',10,30,'cat_q[64:0]',w=180);c.pin('p2',10,150,'cross2_q[32:0]',w=180);c.pin('p3',10,285,'cross3_q[32:0]',w=180)
c.node('s2',260,130,170,65,'WIRE SEXT <<16','33→65');c.node('s3',260,285,170,65,'WIRE SEXT <<16','33→65')
c.node('a1',500,45,170,150,'ADD65 #A','cat + cross2_shift')
c.port('a1','A65','L',.2);c.port('a1','B65','L',.75)
c.node('a2',735,45,125,205,'ADD65 #B','tmp + cross3')
c.port('a2','A65','L',.25);c.port('a2','B65','L',.8);c.ff('F_q',900,45,95,205,65)
c.edge('cat','a1',ds='@A65');c.edge('p2','s2');c.edge('s2','a1',ds='@B65');c.edge('a1','a2',ds='@A65');c.edge('p3','s3');c.edge('s3','a2',ds='@B65',via=[(695,317),(695,209)])
c.edge('a2','F_q',ds='@D')
c.text(20,380,'Cross shifted65: [64:49]=16×sign, [48:16]=cross33, [15:0]=0. Không shift ở width33.',15)
sheet('D03','Fused65: mở ADD3 thành hai adder tổ hợp','ft_leaf_array',c,'tmp=low65(cat_q+cross2_shift); F=low65(tmp+cross3_shift).','Hai adder nằm giữa L4 và L5; F_q chốt L5, không FF trung gian.',
 ['Đây là một cách tổ chức tổ hợp tham chiếu chính xác modulo2^65. Mapper có thể dùng cấu trúc khác; không thay thế bằng số liệu timing chưa đo.',
  'CLK của F_q cùng clk leaf; không reset/enable. Carry ngoài bit64 không được đưa thành limb FFT bổ sung.'])

def correction(code,title,which):
    c=Pins(title,430);w=35 if which==2 else 34
    sources=([('NTT A35(S_q)', 'FFT A35(fa)'),('NTT B35(~Q_q)','FFT B35(fb)')]
             if which==2 else [('NTT A34(D_q)','FFT A34(wa)'),('NTT B34(Q_q)','FFT B34(wb)')])
    for n,(key,y) in enumerate([('am',30),('bm',205)]):
        c.pin(key+'0',20,y,sources[n][0],w=250);c.pin(key+'1',20,y+80,sources[n][1],w=250)
        c.node(key+'mux',340,y,190,110,'MUX plain_q','0=NTT;1=FFT','mux')
        c.port(key+'mux','D0','L',.25);c.port(key+'mux','D1','L',.75);c.port(key+'mux','SEL','B',.5)
        c.edge(key+'0',key+'mux',ds='@D0');c.edge(key+'1',key+'mux',ds='@D1')
    c.node('add',620,60,170,205,f'C{which} ADD{w}','A+B+Cin')
    c.port('add','A','L',.2);c.port('add','B','L',.65);c.port('add','Cin','B',.5)
    c.edge('ammux','add',ds='@A');c.edge('bmmux','add',ds='@B')
    c.node('ci',350,325,245,65,'MUX Cin','C2:PL?fci:1' if which==2 else 'C3:PL&wci','mux');c.edge('ci','add',ds='@Cin',via=[(705,357)],control=True)
    c.pin('PL',15,375,'plain_q',w=180)
    c.edge('PL','ammux',ds='@SEL',via=[(295,392.5),(295,160),(435,160)],control=True)
    c.edge('PL','bmmux',ds='@SEL',via=[(285,392.5),(285,330),(435,330)],control=True)
    c.port('ci','SEL','B',.5);c.edge('PL','ci',ds='@SEL',via=[(300,417),(472,417)],control=True)
    c.node('slice',850,95,140,150,'SLICE / FLAGS','fs33 / s32' if which==2 else 'ws33 / d32');c.edge('add','slice')
    sheet(code,title,'ft_addsub',c,'A/B/Cin theo công thức C'+str(which)+' của chương28; Q/PK/PL đã register cùng S/D.','Intermediate FF → mux + adder + output selection → consumer ở cạnh sau.',
     ['Mỗi mux có hai nguồn độc lập đúng width; guard/zero-extension của từng nguồn theo chương28. Không short D0 và D1 hoặc dùng một net thay cả hai.',
      'plain_q điều khiển cả A và B; Cin cũng chọn cùng owner. Không gate clock hoặc thêm FF giữa mux và adder.'])
correction('D04','C2: hai input mux35 và carry-in riêng',2)
correction('D05','C3: hai input mux34 và carry-in riêng',3)

c=Pins('C4 exact pin groups',430)
for key,y,t in [('ma',20,'A36: scalar/packed/FFT'),('mb',160,'B36: scalar/packed/FFT'),('mc',305,'Cin:1/1/fft_ci')]:
    c.node(key,20,y,310,85,t,'decode mode/split','mux')
    for j,f in enumerate([.2,.5,.8]):c.port(key,'D'+str(j),'L',f)
    c.port(key,'SEL','B',.5)
c.node('adder',475,50,220,255,'C4 ADD36','one shared chain')
c.port('adder','A36','L',.18);c.port('adder','B36','L',.55);c.port('adder','Cin','L',.9)
for a,b in [('ma','A36'),('mb','B36'),('mc','Cin')]:c.edge(a,'adder',ds='@'+b)
c.node('sel',780,50,210,115,'result MUX32','U gốc / candidate','mux');c.edge('adder','sel')
c.node('flags',780,240,210,105,'R bit decoder','scalar R35\npacked !R35,!R17');c.edge('adder','flags')
c.pin('mode',415,345,'fft_mode / split16',w=240)
for key,y in [('ma',125),('mb',260),('mc',405)]:c.edge('mode',key,ss='L',ds='@SEL',via=[(375,362.5),(375,y),(175,y)],control=True)
c.text(25,420,'A36/B36 là ba lựa chọn D0 scalar, D1 packed, D2 FFT; không có ba adder độc lập.',15)
sheet('D06','C4: chân A36, B36, Cin và decode flags','ft_reduce_or_sum',c,'R36=low36(A36+B36+Cin); result chọn raw U hoặc R slice theo đúng lane.','Tổ hợp trong C18..C19 hoặc MAC..combine; không clock nội bộ.',
 ['U gốc phải đi bypass tới result mux, tách khỏi candidate R. fft_sum lấy R[32:0] trực tiếp, không qua NTT select.',
  'D0/D1/D2 là ký hiệu nguồn logic; decoder ưu tiên fft_mode trước split16. B scalar phải NOT sau zero-extend36.'])

c=Pins('U17 adders',430)
for key,y,t in [('lo',30,'LOW ADD17'),('hi',215,'HIGH ADD17')]:
    c.node(key,330,y,235,115,t,'Thi16 + mqhi16 + carry')
    for name,f in [('Thi16',.2),('Phi16',.5),('Cin',.8)]:c.port(key,name,'L',f)
    c.node(key+'src',10,y-10,210,90,'Thi / Phi / NZ','field extract')
    for name,f in [('Thi',.2),('Phi',.5),('NZ',.8)]:c.port(key+'src',name,'R',f)
    c.edge(key+'src',key,ss='@Thi',ds='@Thi16');c.edge(key+'src',key,ss='@Phi',ds='@Phi16')
c.node('cinmux',30,315,215,60,'HIGH Cin MUX','packed?NZhi:Ulo[16]','mux');c.port('cinmux','D0','L',.25);c.port('cinmux','D1','L',.75)
c.edge('cinmux','hi',ds='@Cin')
c.edge('losrc','lo',ss='@NZ',ds='@Cin')
c.edge('lo','cinmux',ss='B',ds='@D0',via=[(447,175),(0,175),(0,330)])
c.edge('hisrc','cinmux',ss='@NZ',ds='@D1',via=[(270,277),(270,300),(15,300),(15,360)])
c.node('pack',650,75,150,205,'PACK U34','scalar:0|U33\npacked:Uhi17|Ulo17')
c.port('pack','lo17','L',.25);c.port('pack','hi17','L',.75)
c.edge('lo','pack',ds='@lo17');c.edge('hi','pack',ds='@hi17');c.ff('U_q',860,75,135,205,34);c.edge('pack','U_q',ds='@D')
c.text(20,390,'Scalar: U33={Uhi17,Ulo16}; packed: U34={Uhi17,Ulo17}. U_q chốt C18.',15)
sheet('D07','Mont U: hai adder17 dùng chung scalar/packed','ft_mont_pipe',c,'Ulo=Thi_lo+Phi_lo+NZlo; Uhi=Thi_hi+Phi_hi+(packed?NZhi:Ulo[16]).','Inputs mq/history sẵn sau C17 → U_q C18 → C4 → corr_q C19.',
 ['Một cách phân rã của U arithmetic không đổi độ chính xác. Scalar phải truyền carry thấp; packed phải dùng NZhi độc lập.',
  'Các pin src trong hình là bundle ba tín hiệu, được tách tới chân Thi/Phi/Cin; không nối ba bit khác nghĩa vào một net.'])

c=Pins('History physical stages',420)
c.node('select',15,25,350,65,'MUX T_hi / NZ theo group_at_T','sẵn sau C7; ghi stage0 tại C8','mux')
for i in range(10):
    c.node('h'+str(i),10+i*99,175,87,90,f'H{i}\nFF34','C'+str(8+i))
    if i:c.edge('h'+str(i-1),'h'+str(i))
c.edge('select','h0',ss='B',ds='T',via=[(190,130),(53,130)])
c.node('u',700,325,285,60,'U FF đọc OLD H9 tại C18')
c.edge('h9','u',ss='B',ds='T',via=[(944,295),(842,295)])
c.text(20,390,'T_hi/NZ là một word34. H0..H9 shift mọi cạnh; invalid vẫn tạo bubble theo cùng clock.',15)
sheet('D08','History10: vẽ đủ từng stage và cạnh chứa X','ft_mont_pipe',c,'H0(X) sau C8; H9(X) sau C17. H9 trước cạnh C18 và mq(X) tạo U(X).','Không gọi đây là trễ9; ghi H0→consumer C18 cách10 cạnh capture.',
 ['Không gating shift bằng T_valid. Nếu giữ stage trong bubble, mq vẫn về theo clock thật và sẽ ghép nhầm T.',
  'Reset valid pipeline để hủy ownership; payload history không cần reset0.'])

c=Pins('Token ages',430)
for i in range(17):
    row=0 if i<9 else 1;col=i if i<9 else 16-i
    c.node('v'+str(i),10+col*109,35+row*165,95,75,'v['+str(i)+']','FF1 reset0')
    if i==9:c.edge('v8','v9',ss='R',ds='R',via=[(998,72.5),(998,237.5)])
    elif i:c.edge('v'+str(i-1),'v'+str(i),ss='R' if i<9 else 'L',ds='L' if i<9 else 'R')
c.text(20,345,'X: v0 C2; v5 C7; v10 C12; v15 C17; v16 C18; corr_valid capture C19.',16)
c.text(20,385,'group delay: g5 chọn T, g15 chọn mq. Tag/side ở RAM, không cần17×side42 FF.',15)
sheet('D09','Mont token: từng valid FF và reset','ft_mont_pipe',c,'v[0]_next=packet_valid; v[i]_next=v[i-1]; reset mọi v về0.','Select m chốt từ old v4 tại C7; mq từ old v9 tại C12; U dùng old v15 C18.',
 ['Các FF cùng clock, shift cả khi invalid. Group chạy cùng tuổi nhưng chỉ consume khi token hợp lệ.',
  'Đường v8→v9 xuống hàng là một FF stage duy nhất, không là phép stall hay thêm boundary ẩn.'])

c=Pins('RAM pins and decode',430)
c.pin('we',10,30,'WE / WA[3:0]',w=190);c.pin('wd',10,150,'WD[N-1:0]',w=190);c.pin('ra',10,290,'RA[3:0]',w=190)
c.node('ram',330,30,290,190,'RAM16 × N','write decoder nội bộ','ram')
for name,f in [('WE',.15),('WA4',.35),('WDN',.7)]:c.port('ram',name,'L',f)
c.edge('we','ram',ds='@WE');c.edge('we','ram',ds='@WA4');c.edge('wd','ram',ds='@WDN')
c.node('rmux',720,95,260,170,'READ MUX16 ×N','RA tổ hợp → RD','mux');c.edge('ram','rmux')
c.port('rmux','RA4','B',.5);c.edge('ra','rmux',ds='@RA4',via=[(850,307)],control=True)
c.text(20,390,'N42 side, N32 operand/root. RAM8 và RAM4 giảm bit address, không thay read latency.',16)
sheet('D10','Tile RAM: tách rõ WE, WA, WD, RA, RD','ft_tile_state',c,'Word select là decoder địa chỉ; read RD=mem[RA] tổ hợp, write mem[WA]<=WD tại WE posedge.','Caller register RA theo lịch, consumer chốt RD ở cạnh kế; state không thêm RA/RD FF.',
 ['READ MUX là cấu trúc logic bên trong macro LUTRAM, không yêu cầu hiện thực array bằng hàng trăm FF.',
  'Nếu WE0, nội dung giữ. Reset không chạy vòng for clear RAM. Same-address partial dùng old-data capture trước cạnh rồi write mới.'])

c=Pins('Reserve counter exact D',430)
c.pin('events',10,25,'reserve / release',w=205);c.node('check',290,25,230,90,'LEGAL event gates','not full / old live ID')
c.edge('events','check');c.node('arith',610,25,180,90,'ADD/SUB count','+1 / -1 / hold')
c.port('arith','events','L',.25);c.port('arith','old_count','L',.75)
c.edge('check','arith',ds='@events');c.ff('count_q',840,25,155,160,'4/5');c.edge('arith','count_q',ds='@D')
c.edge('count_q','arith',ss='@Q',ds='@old_count',via=[(999,65),(999,175),(595,175),(595,92.5)])
c.node('eq',300,240,250,85,'EQ0 / EQdepth','empty / full')
c.edge('count_q','eq',ss='@Q',ds='R',via=[(997,105),(997,200),(600,200),(600,282)])
c.node('ready',650,240,330,85,'OR credit / AND guard','notfull OR valid_release')
c.edge('eq','ready');c.text(20,390,'EN state = có event hợp lệ; reset count0. Hai event11 giữ count nhưng vẫn kiểm legality.',15)
sheet('D11','Credit: D counter, comparator và event qualification','ft_tile_state',c,'count_next=count + reserve_ok - release_ok; tail/head tiến theo event tương ứng.','FFT reserve first beat; NTT reserve C0, release C19; outstanding vẫn còn đến response.',
 ['Count5 NTT có giá trị16; tail/head4 wrap là đúng. Không dùng cùng4 bit cho cả occupancy và pointer.',
  'Empty+reserve+release không hợp thức hóa release vật chưa sống. Full+release chỉ cho alloc lại ID đúng sau khi old data được capture.'])

c=Pins('MAC explicit D Q and emit',430)
c.pin('prod',10,30,'fused65 → SEXT68',w=225);c.node('add',330,30,195,130,'ADD68','acc_in + product')
c.port('add','prod68','L',.2);c.port('add','acc_in68','L',.8);c.edge('prod','add',ds='@prod68')
c.ff('acc_q',650,30,175,130,68);c.edge('add','acc_q',ds='@D');c.port('acc_q','EN','T',.7)
c.pin('PV',15,350,'product_valid',w=180)
c.edge('PV','acc_q',ds='@EN',via=[(315,367.5),(315,5),(772.5,5)],control=True)
c.node('mux',10,235,300,100,'MUX acc_in','first?seed:prev_last?carry:Q','mux');c.edge('mux','add',ds='@acc_in68',via=[(315,285),(315,134)])
c.node('shift',650,235,175,100,'ASR32(Q)','fixed wire')
c.edge('acc_q','shift',ss='@Q',ds='T',via=[(855,62),(855,190),(737,190)])
c.edge('shift','mux',ss='L',ds='R');c.edge('acc_q','mux',ss='@Q',ds='T',via=[(885,62),(885,200),(160,200)])
c.ff('limb_q',870,200,125,135,32);c.edge('add','limb_q',ss='B',ds='@D',via=[(427,180),(850,180),(850,234)])
c.text(20,410,'limb D lấy acc_next slice; limb EN=product_valid && column_last && emit. acc EN=product_valid.',15)
sheet('D12','MAC68: hai đích FF acc và limb từ cùng acc_next','ft_fft_accum',c,'acc_q.D=acc_next; limb_q.D=window(acc_next); acc_in chọn seed/carry/raw Q.','Chốt cả hai tại MAC launch+6; chỉ limb_valid khi column_last&&emit.',
 ['Q hồi tiếp cho product kế tiếp; ASR32 chỉ chọn khi cột trước đã last. first-product có ưu tiên cao nhất để bỏ trạng thái butterfly cũ.',
  'EN ở hình là update qualifier, không clock gate. Reset token/valid, không thay seed bằng reset accumulator mọi clock.'])

c=Pins('C5 exact mux and borrow',430)
for key,x,t in [('a',10,'MUX A32'),('b',310,'MUX B32')]:c.node(key,x,25,230,85,t,'p2?new:partial' if key=='a' else 'p2?partial:new','mux')
c.node('sub',640,25,210,180,'C5 SUB33','{0,A}+~{0,B}+!bi')
c.port('sub','A33','L',.2);c.port('sub','B33','L',.55);c.port('sub','Cin','L',.85)
c.edge('a','sub',ds='@A33',via=[(270,67),(270,5),(610,5),(610,61)])
c.edge('b','sub',ds='@B33');c.node('bi',310,260,270,80,'MUX borrow','limb0?0:(p2?b_im:b_re)','mux')
c.gate('not_bi',520,175,'NOT','!borrow_in')
c.edge('bi','not_bi',via=[(600,300),(600,250),(500,250),(500,197)],control=True)
c.edge('not_bi','sub',ds='@Cin',control=True)
c.ff('T_q',885,25,110,180,32);c.edge('sub','T_q',ds='@D')
c.text(20,380,'D33[31:0] → T; D33[32] → borrow_re khi p1 hoặc borrow_im khi p2. Carry C4 là FF riêng.',15)
sheet('D13','C5: đổi operand và chọn borrow đúng phép trừ','ft_fft_combine',c,'p1: A=partial_p0,B=p1; p2: A=p2,B=partial_sum; low32(A-B-bi).','C5 và side cùng capture tại combine; output post-stage tiêu thụ ở cạnh sau.',
 ['B33 đảo sau mở rộng33, Cin=!borrow_in. Bit32 của hiệu33 là borrow vì miền A/B32 và bi0/1.',
  'Không dùng borrow_real làm carry_sum của C4 hoặc làm borrow_imag. Mỗi phép khởi đầu ở limb0 bằng0.'])

c=Pins('Native half exact wiring',410)
for row,y,name in [(0,30,'sum64'),(1,210,'diff64')]:
    c.node('src'+str(row),15,y,230,100,name+' sau wrap','{high32,low32}')
    c.node('lo'+str(row),350,y,255,100,'LOW out32','{high[0],low[31:1]}')
    c.node('hi'+str(row),700,y,285,100,'HIGH out32','{high[31],high[31:1]}')
    c.edge('src'+str(row),'lo'+str(row));c.edge('src'+str(row),'hi'+str(row),via=[(285,y+50),(285,y-12),(655,y-12),(655,y+50)])
c.text(20,380,'Root/tag/buffer/beat giữ cùng low/high. high[31] là sign của giá trị64 đó, không của số khác.',15)
sheet('D14','Native half: ghi rõ từng lát bit low/high','ft_native_align',c,'Cả sum và diff đã chứa bias+1 và wrap64 trước wiring ASR1.','Giữ low để đợi high; tổng alignment +2 clock của native inverse64.',
 ['Đường HIGH không phụ thuộc low; đường LOW bắt buộc lấy high[0]. Không shift low độc lập khi high chưa có.',
  'Đây là signed half native, không dùng cho NTT modular half hoặc IFFT host normalization.'])

c=Pins('Normalizer carry chain before stage1',430)
for i in range(4):c.node('w'+str(i),10+i*250,25,220,85,f'word{i}[31:0]','ROUND bias tại value-start')
for i in range(3):
    c.node('ci'+str(i),40+i*310,230,270,90,f'carry_{i}_to_{i+1}','AND overflow & same_value')
    c.edge('w'+str(i),'ci'+str(i),ss='B',ds='T')
c.text(20,365,'same_value01=(fmt!=0), 12=(fmt==2), 23=(fmt!=0). Carry được tính/chốt tại stage1.',15)
c.text(20,400,'Với bias=2^j, carry thấp = AND(word_start[31:j]); carry tiếp cần word trung gian toàn1.',15)
sheet('D15','Host rounding: carry bị cắt đúng biên giá trị','ft_read_normalize',c,'G+1 chốt bias/carry; G+2 bốn adder32 dùng carry đã chuẩn bị; không nối sang số kế tiếp.','Stage1 carry/addend, stage2 wrap sum, stage3 shifter; không tăng số stage.',
 ['Bias nằm trong low word của mỗi giá trị W vì s0..9. Khi s0, bias0 và không tạo s-1.',
  'Công thức AND prefix mô tả overflow của cộng power-of-two; producer phải qualify normalize và ranh giới fmt.'])

c=Pins('Valid and metadata paired',430)
for key,y,detail,width in [('v',30,'reset0',1),('m',210,'payload không reset',10)]:
    for i in range(5):
        c.node(key+str(i),10+i*200,y,170,95,f'{key}[{i}] FF{width}',detail)
        if i:c.edge(key+str(i-1),key+str(i))
c.text(20,370,'Cùng clock và cùng số stage: V0/meta0 của X không được ghép V1/meta1 của Y.',16)
sheet('D16','Token và metadata: FF song song, reset khác payload','ft_fft_accum',c,'Delay valid/meta5 từ operand launch để căn fused; MAC/output thêm boundary đã khóa.','Mọi valid reset0; payload có thể giữ X nhưng không được consume khi valid0.',
 ['Không delay valid5 nhưng delay metadata4, hoặc chỉ shift khi valid1. Bubble phải chiếm vị trí clock thực.',
  'Side42 được lưu RAM, không nhân bản toàn pipeline nếu không cần. Chỉ metadata phục vụ product đi cùng product.'])

c=Pins('Owner mux pins',430)
c.node('mont',10,25,250,100,'NTT candidates','leaf_a64, leaf_b64')
c.node('fft',10,220,250,100,'FFT candidates','map limbs; signed flags')
c.node('mux',390,60,230,230,'OWNER MUX','cfg_mode fixed','mux')
c.port('mux','NTT64','L',.2);c.port('mux','FFT64','L',.75)
c.edge('mont','mux',ds='@NTT64');c.edge('fft','mux',ds='@FFT64')
c.node('leaf',750,60,230,230,'LEAF ARRAY','a64 / b64 / flags4','dsp');c.edge('mux','leaf')
c.text(20,390,'a_signed/b_signed = NTT?4b0:FFT top-limb flags. Mask valid cũng chọn cùng context.',15)
sheet('D17','Tile owner: dữ liệu, dấu và valid phải chọn cùng mode','ft_tile',c,'Mỗi bus a/b có một owner mux tương ứng; không chọn a từ NTT và b/flags từ FFT.','Context giữ trong BUSY; owner không đổi chỉ vì một controller đang có bubble.',
 ['Đầu ra leaf có thể fanout tới mont/accum nhưng token qualify chỉ consumer hợp lệ. C4 có owner mux riêng theo cùng context.',
  'Không xem owner mux như arbiter nhiều job đồng thời. Profile0.2 chỉ một kernel/context.'])

c=Pins('AXI hold equations',430)
c.node('slots',10,25,250,95,'AW_full / W_full','FF độc lập; chỉ clear bus reset')
c.gate('commit',370,50,'AND','wr_commit')
c.node('bv',600,25,170,170,'BVALID FF','D=(Q&!ready)|commit')
c.port('bv','D','L',.2);c.port('bv','Q','R',.2)
c.edge('slots','commit',ds='I0');c.pin('free',10,215,'!BVALID',w=155);c.edge('free','commit',ds='I1',via=[(310,232),(310,82)])
c.edge('commit','bv',ds='@D');c.node('r',600,265,370,80,'R holding FF32 +resp+valid','Q giữ nguyên khi RVALID&&!RREADY')
c.text(20,385,'Commit logic thực = AW_full & W_full & !BVALID. Không commit lặp khi B đang stall.',15)
sheet('D18','AXI: phương trình giữ response và sự kiện commit','ft_axil_top',c,'Bvalid_next=(Bvalid&&!Bready)|wr_commit, reset bus ưu tiên; Rdata hold khi !Rready.','B/R bus reset khác soft core reset. Command enqueue một lần tại wr_commit hợp lệ.',
 ['Pin slots ở AND là bundle AW_full&W_full đã qualify; AND còn nhận !BVALID. Có thể tách thành hai AND nếu viết structural thuần.',
  'Dữ liệu Bresp/Rdata cũng phải giữ, không chỉ valid. Khi lỗi địa chỉ/command vẫn tạo một response hợp lệ với SLVERR.'])

