"""Vector structural schematics for guide1.1, not a mapped synthesis netlist.

Every figure is a real Drawing (paths, wires, gates, registers), exported to SVG
and embedded vectorially in the PDF. No RTL/baseline/locked-contract edits.
"""
from pathlib import Path
import math, html, json, hashlib
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon, Path as GPath, Circle
from reportlab.graphics import renderPDF, renderSVG
from reportlab.platypus import Flowable, Paragraph, Spacer, PageBreak, NextPageTemplate, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

NAVY=colors.HexColor('#142D45'); TEAL=colors.HexColor('#167D86')
PURPLE=colors.HexColor('#79508B'); LIGHT=colors.HexColor('#EDF3F7')
LINE=colors.HexColor('#A9BBC8'); AMBER=colors.HexColor('#A76616')
WHITE=colors.white
SHEETS=[]

class Circuit:
    def __init__(self,title,height=390):
        self.title=title; self.height=height;self.nodes={};self.edges=[];self.extras=[]
    def node(self,key,x,y,w,h,title,detail='',kind='box'):
        self.nodes[key]=dict(x=x,y=y,w=w,h=h,title=title,detail=detail,kind=kind);return key
    def gate(self,key,x,y,kind,label=''):
        return self.node(key,x,y,62,44,label or kind,'',kind)
    def edge(self,a,b,label='',ss='R',ds='L',via=None,control=False,pos=None):
        self.edges.append(dict(a=a,b=b,label=label,ss=ss,ds=ds,via=via,control=control,pos=pos))
    def text(self,x,y,s,size=15,color=NAVY):self.extras.append(('text',x,y,s,size,color))
    def line(self,pts,control=False):self.extras.append(('line',pts,control))
    def frame(self,x,y,w,h,label):self.extras.append(('frame',x,y,w,h,label))
    def pin(self,key,x,y,label,out=False,w=100):return self.node(key,x,y,w,35,label,'','out' if out else 'in')
    def point(self,key,side):
        n=self.nodes[key];x,y,w,h=(n[k] for k in ['x','y','w','h'])
        return {'L':(x,y+h/2),'R':(x+w,y+h/2),'T':(x+w/2,y),'B':(x+w/2,y+h),
                'I0':(x,y+h*.28),'I1':(x,y+h*.72),
                'L0':(x,y+h*.2),'L1':(x,y+h*.5),'L2':(x,y+h*.8)}[side]
    def drawing(self):
        d=Drawing(1000,self.height)
        Y=lambda y:self.height-y
        def text(x,y,s,size=14,color=NAVY,anchor='start',bold=False):
            d.add(String(x,Y(y),s,fontName='VN-Bold' if bold else 'VN',fontSize=size,fillColor=color,textAnchor=anchor))
        def pathline(pts,color,width=1.8,dash=None,arrow=False):
            p=GPath(strokeColor=color,strokeWidth=width,fillColor=None)
            p.moveTo(pts[0][0],Y(pts[0][1]))
            for x,y in pts[1:]:p.lineTo(x,Y(y))
            if dash:p.strokeDashArray=dash
            d.add(p)
            if arrow:
                x,y=pts[-1];xp,yp=pts[-2];ang=math.atan2(y-yp,x-xp)
                vv=[x,Y(y),x-7*math.cos(ang-.45),Y(y-7*math.sin(ang-.45)),x-7*math.cos(ang+.45),Y(y-7*math.sin(ang+.45))]
                d.add(Polygon(vv,fillColor=color,strokeColor=color))
        for edge in self.edges:
            a=self.point(edge['a'],edge['ss']);b=self.point(edge['b'],edge['ds'])
            via=edge['via']
            if via is None:
                if a[1]==b[1] or a[0]==b[0]:pts=[a,b]
                elif edge['ss'] in 'TB' and edge['ds'] in 'TB':
                    my=(a[1]+b[1])/2;pts=[a,(a[0],my),(b[0],my),b]
                else:
                    mx=(a[0]+b[0])/2;pts=[a,(mx,a[1]),(mx,b[1]),b]
            else:
                given=[a]+via+[b];pts=[a]
                for i,pt in enumerate(given[1:]):
                    prev=pts[-1]
                    if prev[0]!=pt[0] and prev[1]!=pt[1]:
                        vertical_first=(i==0 and edge['ss'] in 'TB') or (i==len(given)-2 and edge['ds'] not in 'TB')
                        pts.append((prev[0],pt[1]) if vertical_first else (pt[0],prev[1]))
                    pts.append(pt)
            color=PURPLE if edge['control'] else TEAL
            pathline(pts,color,1.6 if edge['control'] else 2.2,[5,3] if edge['control'] else None,True)
            if edge['label']:
                px,py=edge['pos'] or ((pts[0][0]+pts[1][0])/2,min(pts[0][1],pts[1][1])-8)
                # White backing prevents a text label from being crossed by a wire.
                tw=max(len(edge['label'])*6.6,18)
                d.add(Rect(px-tw/2-3,Y(py)-3,tw+6,17,fillColor=WHITE,strokeColor=None))
                text(px,py,edge['label'],12,color,'middle')
        for key,n in self.nodes.items():
            x,y,w,h,t,detail,kind=(n[k] for k in ['x','y','w','h','title','detail','kind'])
            yy=Y(y+h);fill=WHITE if kind in ['AND','OR','XOR','NOT'] else LIGHT
            if kind in ['AND','OR','XOR','NOT']:
                p=GPath(strokeColor=NAVY,strokeWidth=1.9,fillColor=WHITE)
                if kind=='AND':
                    p.moveTo(x,yy);p.lineTo(x+w*.48,yy)
                    p.curveTo(x+w*1.17,yy,x+w*1.17,yy+h,x+w*.48,yy+h)
                    p.lineTo(x,yy+h);p.closePath()
                elif kind in ['OR','XOR']:
                    p.moveTo(x,yy);p.curveTo(x+w*.55,yy,x+w*.8,yy+h*.18,x+w,yy+h*.5)
                    p.curveTo(x+w*.8,yy+h*.82,x+w*.55,yy+h,x,yy+h)
                    p.curveTo(x+w*.28,yy+h*.52,x+w*.28,yy+h*.48,x,yy);p.closePath()
                    if kind=='XOR':
                        q=GPath(strokeColor=NAVY,strokeWidth=1.8,fillColor=None)
                        q.moveTo(x-7,yy);q.curveTo(x+w*.17,yy+h*.5,x+w*.17,yy+h*.5,x-7,yy+h);d.add(q)
                else:
                    p.moveTo(x,yy);p.lineTo(x+w-10,yy+h/2);p.lineTo(x,yy+h);p.closePath()
                    d.add(Circle(x+w-5,yy+h/2,5,fillColor=WHITE,strokeColor=NAVY,strokeWidth=1.7))
                d.add(p)
                # Pins meet the named net stubs; labels are outside conventional symbols.
                text(x+w/2,y+h+18,t,13,NAVY,'middle')
            elif kind in ['mux','mux4']:
                d.add(Polygon([x,yy,x,yy+h,x+w,yy+h*.78,x+w,yy+h*.22],fillColor=LIGHT,strokeColor=NAVY,strokeWidth=1.7))
            elif kind=='ff':
                d.add(Rect(x,yy,w,h,fillColor=colors.HexColor('#E8EFF8'),strokeColor=NAVY,strokeWidth=1.7))
                d.add(Polygon([x,yy+8,x+8,yy+14,x,yy+20],fillColor=WHITE,strokeColor=NAVY))
                text(x+11,y+h-5,'clk',10,AMBER)
            elif kind=='ram':
                d.add(Rect(x,yy,w,h,fillColor=colors.HexColor('#E5F3EF'),strokeColor=TEAL,strokeWidth=1.8))
                d.add(Line(x+7,yy,x+7,yy+h,strokeColor=TEAL,strokeWidth=1))
            elif kind=='dsp':
                d.add(Rect(x,yy,w,h,fillColor=colors.HexColor('#FFF0DB'),strokeColor=AMBER,strokeWidth=1.9))
            elif kind in ['in','out']:
                d.add(Rect(x,yy,w,h,rx=4,ry=4,fillColor=WHITE,strokeColor=LINE,strokeWidth=1.2))
            else:d.add(Rect(x,yy,w,h,rx=4,ry=4,fillColor=fill,strokeColor=NAVY,strokeWidth=1.5))
            if kind not in ['AND','OR','XOR','NOT']:
                rows=t.split('\n'); base=y+(h/2 if not detail else h*.35)-(len(rows)-1)*8+5
                for j,row in enumerate(rows):
                    fs=min(16,max(11,(w-12)/max(1,len(row))/.54))
                    text(x+w/2,base+j*17,row,fs,NAVY,'middle',True)
                if detail:
                    for j,row in enumerate(detail.split('\n')):
                        fs=min(13,max(10,(w-12)/max(1,len(row))/.52))
                        inset=22 if kind in ['mux','mux4'] else 12
                        text(x+w/2,y+h-inset-(len(detail.split('\n'))-1-j)*14,row,fs,TEAL,'middle')
        for e in self.extras:
            if e[0]=='text':_,x,y,s,size,color=e;text(x,y,s,size,color)
            elif e[0]=='line':pathline(e[1],PURPLE if e[2] else TEAL,1.5,[5,3] if e[2] else None)
            else:
                _,x,y,w,h,t=e
                r=Rect(x,Y(y+h),w,h,fillColor=None,strokeColor=LINE,strokeWidth=1,strokeDashArray=[6,4]);d.add(r)
                text(x+6,y-7,t,13,GRAY)
        return d

GRAY=colors.HexColor('#526574')
def sheet(code,title,module,circuit,formula,clock,notes):
    SHEETS.append(dict(code=code,title=title,module=module,circuit=circuit,formula=formula,clock=clock,notes=notes))
def row(c,y,labels,kinds=None,details=None):
    """Place four concrete cells, including arithmetic/mux/register boundaries."""
    ids=[]
    for i,label in enumerate(labels):
        key=f'r{y}_{i}';ids.append(key)
        c.node(key,20+i*250,y,210,64,label,(details or ['']*len(labels))[i],(kinds or ['box']*len(labels))[i])
    for a,b in zip(ids,ids[1:]):c.edge(a,b)
    return ids

# S01: actual standard logic symbols and full-adder decomposition.
c=Circuit('Cổng cơ sở và full-adder',400)
c.pin('a',10,15,'a',w=80);c.pin('b',10,105,'b',w=80);c.gate('xor1',170,20,'XOR','p=a XOR b')
c.gate('and1',170,110,'AND','g=a AND b');c.pin('cin',15,235,'cin',w=90)
c.gate('xor2',430,20,'XOR','sum=p XOR cin');c.gate('and2',430,160,'AND','h=p AND cin')
c.gate('or',700,110,'OR','cout=g OR h');c.pin('sum',850,25,'sum',True);c.pin('cout',850,115,'cout',True)
c.edge('a','xor1',ds='I0');c.edge('b','xor1',ds='I1',via=[(115,122),(115,52)])
c.edge('a','and1',ds='I0',via=[(145,32),(145,122)]);c.edge('b','and1',ds='I1')
c.edge('xor1','xor2',label='p',pos=(340,32),ds='I0');c.edge('xor1','and2',ds='I0',via=[(300,42),(300,172)])
c.edge('cin','xor2',ds='I1',via=[(350,252),(350,52)],pos=(300,242),label='cin')
c.edge('cin','and2',ds='I1',via=[(380,252),(380,192)])
c.edge('and1','or',ds='I0',via=[(645,132),(645,122)]);c.edge('and2','or',ds='I1',via=[(665,182),(665,142)])
c.edge('xor2','sum');c.edge('or','cout');c.text(20,335,'1 bit: p=a XOR b; sum=p XOR cin; cout=(a AND b) OR (p AND cin)',17)
sheet('S01','Cổng logic thật: full-adder 1 bit','primitive',c,'sum=a XOR b XOR cin; cout=majority(a,b,cin).','Tổ hợp; không chứa clock.',
 ['Hai nhánh tạo sum và cout dùng chung p. Vector adderN là N bit-slice tương đương, không phải thêm N pipeline stage.',
  'Ký hiệu AND/OR/XOR trong hình là cổng logic; mapper có thể gộp chúng vào LUT và carry primitive. Hai chân vào của mỗi cổng đã tách; dây giao nhau không có dấu nối không biểu thị short.'])

c=Circuit('Mux, comparator và register',400)
row(c,30,['d0 / d1','MUX2 bit-slice','FF payload[N]','Q[N]'],['in','mux','ff','out'],['','(~s & d0)|(s & d1)','enable=1; no reset',''])
c.pin('sel',270,140,'s[0]',w=95);c.edge('sel','r30_1',ss='T',ds='B',control=True)
row(c,225,['A[N] / B[N]','XOR bank[N]','OR reduction + NOT','EQ'],['in','box','box','out'],['','x[i]=A[i] XOR B[i]','EQ=!OR(x)','1 bit'])
c.text(20,375,'Enable FF: Dnext = rst ? 0 : en ? D : Q; reset payload chỉ khi contract yêu cầu.',16)
sheet('S02','MUX2, EQ/NZ và flip-flop','primitive',c,'MUX2=(~s & d0)|(s & d1); EQ=~OR(A XOR B); NZ=OR(A).','MUX/EQ tổ hợp; FF chỉ đổi ở posedge.',
 ['Một mux busN là N mux bit dùng chung select; không phải chọn từng bit bằng select khác nhau.',
  'FF enable dùng mux hồi tiếp Q ở D; synchronous reset của valid có ưu tiên hơn enable. RAM/payload không tự thêm reset hàng loạt.'])

c=Circuit('Carry chain',390)
row(c,35,['a[35:0], b[35:0]','XOR / AND [36]','9 × CARRY4','R[35:0]'],['in','box','box','out'],['','p=a XOR b; g=a AND b','4 bit carry / cell','Cin ở bit0'])
for i in range(9):c.node(f'carry{i}',20+i*108,215,96,62,f'CARRY4 #{i}','CI → CO[3]')
for i in range(8):c.edge(f'carry{i}',f'carry{i+1}')
c.text(20,330,'a-b-bi = a + ~b + (1-bi); đảo b bằng XOR khi sub=1.',17)
sheet('S03','Cộng/trừ N bit và đường carry','primitive',c,'R=lowN(A+B+Cin); subtraction dùng B=NOT(b), Cin=NOT(bi).','Không thêm FF giữa CARRY4 trong cùng một toán tử tổ hợp.',
 ['9 CARRY4 là cấu trúc tham chiếu cho adder36 trên7-series; không phải số primitive đã xác nhận sau synth của thiết kế mới.',
  'Khi vẽ N bit-slice phải mở rộng đầu vào đủ width trước NOT/cộng. Tên C0..C5 là ID adder, không phải số clock.'])

c=Circuit('Leaf riêng',400)
row(c,40,['a16 / b16','AND sign + concat','FF ax17 / bx17','DSP48E1 ×'],['in','box','ff','dsp'],['','s=flag AND bit15','capture L1','signed17 × signed17'])
row(c,220,['full34[32:0]','FF pp1[33]','FF pp2[33]','raw lane[33]'],['box','ff','ff','out'],['full34[33]=bit32','L2','L3','p[33*k+:33]'])
c.edge('r40_3','r220_0',ss='B',ds='T',via=[(875,170),(125,170)])
c.text(20,365,'DSP A: sign-extend17 lên25; DSP B: sign-extend17 lên18. Flags đi qua input FF.',16)
sheet('S04','Một leaf16×16: AND dấu → FF → DSP → FF','ft_leaf_array',c,"ax=signed({a_signed & a[15],a}); bx tương tự; raw=low33(ax*bx).",'Launch L0; input FF L1; pp1 L2; raw L3.',
 ['Lặp cấu trúc này4 lần. Không nối sign-select sống của transaction mới vào toán hạng đã chốt của transaction cũ.',
  'Giữ33 bit là chính xác với miền input signed/unsigned16; bỏ bit34 theo quan hệ sign extension, không phải approximate arithmetic.'])

c=Circuit('Ghép fused65',440)
for k,y in enumerate([25,110,210,315]):c.pin(f'p{k}',10,y,f'P{k}[32:0]',w=135)
c.node('cat',185,25,190,65,'CONCAT65','P1<<32 | P0.low32')
c.node('catff',420,25,180,65,'FF cat65','L4','ff')
c.node('c2ff',190,200,180,65,'FF cross2[33]','L4','ff')
c.node('c3ff',190,305,180,65,'FF cross3[33]','L4','ff')
c.node('c2',425,200,180,65,'SIGN-EXT + <<16','33 → 65 bit')
c.node('c3',425,305,180,65,'SIGN-EXT + <<16','33 → 65 bit')
c.node('sum',700,150,130,150,'ADD3[65]','mod2^65')
c.node('out',870,150,120,150,'FF fused65','L5','ff')
c.edge('p0','cat',ds='L0');c.edge('p1','cat',ds='L2',via=[(165,127),(165,77)])
c.edge('cat','catff');c.edge('catff','sum',ds='L0',via=[(650,57),(650,180)])
c.edge('p2','c2ff');c.edge('p3','c3ff');c.edge('c2ff','c2');c.edge('c3ff','c3')
c.edge('c2','sum',ds='L1');c.edge('c3','sum',ds='L2',via=[(660,337),(660,270)])
c.edge('sum','out')
c.text(20,418,'L4 lưu cat65 và cross33/33; sign-extension sau FF chỉ là dây. ADD3 không thêm FF.',16)
sheet('S05','Bốn raw product → cat/cross FF → fused65','ft_leaf_array',c,'F=P0+(P2<<16)+(P3<<16)+(P1<<32).','Raw L3 → cat/cross L4 → fused L5; không thêm data FF giữa hai phép cộng.',
 ['cat là dây nối, P0 low32 hợp lệ khi lo×lo unsigned. Cross phải sign-extend trước khi dịch.',
  'Sơ đồ có ADD3 để không ép một CSA chưa đo. Nếu triển khai CSA tổ hợp, vẫn phải giữ modulo65, cùng boundary L4/L5 và equivalence từng bit.'])

c=Circuit('Addsub dùng chung',430)
for y,prefix,width,op in [(25,'S',33,'C0 a+b+ci'),(235,'D',34,'C1 a+~b+!bi')]:
    ids=row(c,y,[op,f'FF {prefix}[{width}]',f'MUX → C{2 if prefix=="S" else 3}',f's/d[31:0]'],['box','ff','mux','out'],['', 'q/split/plain cùng FF','NTT correction / FFT sum','raw hoặc corrected'])
    c.text(530,y+118,'FFT aux → fs33' if prefix=='S' else 'FFT aux → ws33',15,PURPLE)
c.text(20,405,'C2=adder35, C3=adder34; fs/ws là live combinational; co_now/bo_now ở input hiện tại.',16)
sheet('S06','ft_addsub: hai raw chain và hai correction chain','ft_addsub',c,'NTT s=a+b hoặc a+b-q; d=a-b hoặc a-b+q. FFT s/d wrap, C2/C3 tạo fs/ws.','Input → FF trung gian → correction/mux tổ hợp → FF của caller.',
 ['Không đặt FF ở s/d nội bộ. Out_valid là valid của FF intermediate; fs/ws không tự theo out_valid.',
  'Các nhánh raw bypass và candidate gặp nhau tại mux output. C2/C3 input mux nằm trước adder để dùng chung arithmetic, không dựng hai adder theo mode.'])

c=Circuit('Guard difference34',390)
c.node('lo',25,50,250,90,'FA ×16 LOW','a_lo + ~b_lo + !bi')
c.node('guard',365,50,200,90,'FA guard bit16','A=1; B=split16')
c.node('hi',665,50,290,90,'FA ×17 HIGH','{0,a_hi}+{0,~b_hi}')
c.edge('lo','guard','carry_low',pos=(320,88));c.edge('guard','hi','carry_hi',pos=(615,88))
c.node('flags',340,220,350,70,'D[16] / D[33]','packed: !D[16] / !D[33] là borrow')
c.edge('guard','flags',ss='B',ds='T',control=True);c.edge('hi','flags',ss='B',ds='R',via=[(810,255)],control=True)
c.text(25,335,'split0: guard1+carry_low → carry_hi=carry_low. split1: 1+1+carry_low → carry_hi=1.',16)
sheet('S07','ft_addsub: mở bit guard để cắt borrow packed','ft_addsub',c,'D34={0,a_hi,1,a_lo}+{0,~b_hi,split,~b_lo}+!bi.','C1 tổ hợp trước intermediate FF; correction dùng flags đã chốt.',
 ['split0 truyền quan hệ carry/borrow giữa hai nửa để tạo phép trừ32. split1 tách hai phép trừ16.',
  'Packed carry-low được giữ ở guard; lấy d={D[32:17],D[15:0]}, không lấy D[31:0]. Các width/slice C2/C3 vẫn theo chương28.'])

c=Circuit('C4 adder dùng chung',390)
row(c,85,['U34 / q32\nFFT a32 / b32','MUX A36 / B36','C4 ADD36','SELECT result32'],['in','mux','box','mux'],['','mode/split; Cin','R=A+B+Cin','U hay candidate'])
c.node('decode',520,235,220,65,'BIT DECODE','borrow / lane slice')
c.edge('r85_2','decode',ss='B',ds='T');c.edge('decode','r85_3',ss='R',ds='B',control=True)
c.text(20,350,'FFT: fft_sum=R[32:0], result=R[31:0], underflow=00. Không clk/rst/valid.',17)
sheet('S08','ft_reduce_or_sum: một adder36 cho ba chế độ','ft_reduce_or_sum',c,'R36=A36+B36+Cin. Scalar B=NOT(zeroextend36(q)); FFT B=zeroextend36(fft_b).','NTT U FF C18 → C4 tổ hợp → corrected FF C19 ở mont.',
 ['Scalar underflow=R[35]. Packed underflow={~R[35],~R[17]}; không dùng cùng polarity.',
  'Một phép cộng36 được chia sẻ theo operand mux. Không thêm comparator U>=q riêng nếu carry/borrow đã cung cấp điều kiện chọn chính xác.'])

c=Circuit('C4 packed guard17',400)
for y,title,vals in [(30,'A36',['0','Uhi17','1','Ulo17']),(105,'B36',['0','~{0,qhi16}','1','~{0,qlo16}']),(235,'R36',['carry35','candidate[34:18]','carry17','candidate[16:0]'])]:
    c.text(10,y+27,title,15)
    for x,w,t in [(90,100,vals[0]),(190,325,vals[1]),(515,110,vals[2]),(625,350,vals[3])]:c.node(f'{y}_{x}',x,y,w,55,t)
c.node('guard',300,335,620,45,'Guard: 1+1+carry_low → bit17=carry_low, carry18=1')
c.text(95,195,'Cin=1 ở lane thấp; guard bảo đảm lane cao nhận +1 riêng, không phụ thuộc lane thấp.',16)
sheet('S09','C4 packed: sơ đồ bit17 và polarity borrow','ft_reduce_or_sum',c,'Candidate low=R[15:0]; high=R[33:18]. Borrow low=!R[17], high=!R[35].','Cả hai lane xử lý cùng khoảng tổ hợp C18..C19.',
 ['u_bus={Uhi17,Ulo17}; cổng vào chưa có guard. Guard17 chỉ được chèn khi tạo A36/B36.',
  'Không cho Ulo carry vào phép hiệu chỉnh Uhi. Chọn U gốc hay candidate riêng từng lane, underflow là điều kiện chọn chứ không là fault.'])

c=Circuit('Mont feedback',430)
c.node('t',15,40,190,75,'T operand FF','operand32 / root32','ff')
c.node('mux',265,40,195,75,'MUX feedback','T / low(T) / m','mux')
c.node('leaf',535,40,210,75,'LEAF ARRAY ×1','unsigned; FUSE5','dsp')
c.node('product',810,40,175,75,'fused_p65','T / m / mq')
c.edge('t','mux');c.edge('mux','leaf');c.edge('leaf','product')
c.edge('product','mux','low32',ss='B',ds='B',via=[(897,170),(362,170)],pos=(640,160))
c.node('qsel',275,255,220,65,'MUX B32','root / qi / q','mux')
c.node('token',15,255,190,65,'TOKEN + select FF','age0/5/10/15','ff')
c.edge('token','qsel',control=True);c.edge('qsel','leaf',ss='R',ds='B',via=[(640,287)])
c.text(20,385,'Chỉ một leaf array vật lý; ba phép nhân được chia lượt. Không dùng ba khối multiplier riêng.',17)
sheet('S10','ft_mont_pipe scalar: feedback T → m → mq','ft_mont_pipe',c,'T=a·root; m=low32(T)·qi mod2^32; mq=m·q.','Launch C2/C7/C12; product sau C7/C12/C17.',
 ['Chốt select từ token nhìn trước; product mới đi qua mux vào input FF của leaf ở cạnh tiếp theo. Không chèn full-width feedback FF.',
  'B32 lấy root đã giữ của T hoặc q/qi context cố định. Ba lượt của các packet khác nhau có thể xen kẽ trong cùng khoảng pipeline.'])

c=Circuit('Packed hai group',410)
for y,g in [(25,0),(200,1)]:
    ids=row(c,y,[f'MUX group{g}',f'LEAF {2*g}/{2*g+1}','ALIGN64 ×2 FF',f'pp[{g}][63:0]'],['mux','dsp','ff','out'],['T / m / mq','2 product16×16','raw3 → FUSE5','hai lane32'])
    c.edge(ids[3],ids[0],ss='B',ds='B',via=[(875,y+110),(125,y+110)],label='low16 mỗi lane',pos=(500,y+100))
c.text(20,385,'Hai group có select/token riêng. Một packet=2 lane; group0 và group1 có thể làm lượt khác nhau.',16)
sheet('S11','ft_mont_pipe packed: dùng cả bốn leaf','ft_mont_pipe',c,'pp[g]={raw_product_lane1[31:0],raw_product_lane0[31:0]}; lấy low16/high16 từng product.','Raw C5/C10/C15 → align1 → align2 C7/C12/C17.',
 ['Group0 leaf0/1, group1 leaf2/3. Lịch launch modulo3 lần lượt (T,m),(mq,T),(m,mq).',
  'Không lấy fused_p cho packed. leaf_valid[1:0]/[3:2] chỉ mask lượt hợp lệ, không dừng FF của leaf.'])

c=Circuit('History và correction',430)
row(c,20,['MUX T group','HISTORY34 ×10 FF','U ADD + FF34','C4 bên ngoài'],['mux','ff','ff','box'],['group_at_T=delay5','Thi32 + NZ2 / bubble','Thi+mqhi+NZ; C18','U-q / result32'])
c.node('mq',290,190,210,60,'MUX mq group','group_at_mq=delay15','mux')
c.edge('mq','r20_2',ss='R',ds='B',via=[(625,220)])
c.node('side',530,280,180,60,'SIDE RAM ngoài','head_addr / async','ram')
c.node('corr',775,280,205,60,'FF corrected + side','corr_valid C19','ff')
c.edge('r20_3','corr',ss='B',ds='T');c.edge('side','corr')
c.text(20,385,'History ghi stage0 C8; stage9 sẵn sau C17; U FF C18 lấy OLD history9.',17)
sheet('S12','Mont history chung, chọn group và chốt correction','ft_mont_pipe',c,'history34={T_hi_word32,NZ2}; packed U={Uhi17,Ulo17}, scalar U={0,U33}.','C18 U → C19 correction + side read/release. Không shift history theo valid.',
 ['History data shift mỗi clock; valid/bubble và group đi đúng tuổi. Không dùng delay15(group) để chọn T ở C7.',
  'Side pointer thuộc state; mont chỉ phát side_ra=head_addr và side_re đúng cạnh C19. Correction FF lấy dữ liệu cũ trước khi head tăng.'])

c=Circuit('Sáu RAM tile',430)
names=[('side',42,16),('operand',32,16),('root',32,16),('operand_sum',32,8),('root_sum',32,8),('partial',32,4)]
for i,(name,bits,depth) in enumerate(names):
    x=20+(i%3)*335;y=25+(i//3)*205
    c.node(name,x,y,285,105,name+f'_mem\n{depth} × {bits}','1W sync / 1R async','ram')
    c.text(x,y+133,f'we, wa → D[{bits}] @posedge',14)
    c.text(x,y+156,f'ra → rd[{bits}] tổ hợp',14)
sheet('S13','ft_tile_state: RAM thực và sáu cặp cổng riêng','ft_tile_state',c,'FFT address=buffer·2L+semantic_word; sum address=buffer·L+limb; partial address=limb.','Write tại cạnh we; read tổ hợp giữa hai cạnh, FF consumer nằm ngoài state.',
 ['Các đường đọc/ghi là cổng độc lập của từng RAM, không phải một RAM6R/6W tập trung. Không thêm FF output RAM trong module.',
  'Side42={0,pairing,tag8,data32}; array không reset. Partial read-modify-write lấy p0 trước cạnh và ghi tổng sau cạnh.'])

c=Circuit('Credit counters',420)
row(c,30,['reserve / release','ADD ±1 + HOLD mux','FF count / pointers','EQ full / empty'],['in','mux','ff','box'],['hai event hợp lệ','case10/01/00/11','FFT4; side5; ptr4','credit + fault'])
c.node('own',280,240,220,60,'ID / ownership check','range; live; double free')
c.node('ready',770,240,205,60,'AND / OR credit','notfull OR valid_release')
c.edge('r30_2','own',ss='B',ds='T',control=True);c.edge('r30_3','ready',ss='B',ds='T',control=True)
c.text(20,370,'FFT depth8/4/2 theo fmt; NTT depth16. Reserve ≠ write ≠ release ≠ retire.',17)
sheet('S14','State: incrementer, comparator và reserve/release','ft_tile_state',c,'count_next=count+reserve_valid-release_valid; pointer tăng modulo depth.','NTT reserve C0, write C2, release C19; FFT reserve first beat, free combine cuối.',
 ['Không đánh đồng count buffer với outstanding. alloc_buf/tail được caller chốt khi reserve, không lấy pointer sống ở beat sau.',
  'Full+release có thể nhận mới nếu release hợp lệ và reuse đúng ID/lịch. Empty+reserve không cho phép free một vật chưa tồn tại.'])

c=Circuit('MAC68',420)
row(c,30,['fused_p65','SIGN EXT68','ADD68','FF acc68'],['in','box','box','ff'],['return token FUSE5','{{3{sign}},F}','acc + product','launch+6'])
c.node('seed',30,220,190,65,'CONST seed / zero','2^15 / 2^31 / 2^63')
c.node('amux',285,220,205,65,'MUX accumulator','first / carry / acc','mux')
c.node('shift',780,220,200,65,'ASR32 / SLICE','column_last; emit')
c.edge('seed','amux');c.edge('r30_3','amux',ss='B',ds='T',via=[(875,170),(387,170)])
c.edge('amux','r30_2',ss='R',ds='B',via=[(625,252)])
c.edge('r30_3','shift',ss='B',ds='T')
c.edge('shift','amux',ss='L',ds='B',via=[(740,252),(740,325),(387,325)])
c.text(20,380,'Metadata10 và valid delay5 riêng. Shift cột chỉ ở column_last; emit không đồng nghĩa mỗi product.',16)
sheet('S15','ft_fft_accum: mux seed, adder68 và carry cột','ft_fft_accum',c,'acc_next=acc_in+signextend68(fused65); carry_next=signed(acc_next)>>>32 khi last cột.','Fused launch+5 → MAC/limb launch+6 → combine launch+7.',
 ['W128 emit step5/9/12/14 theo timing.json. Emit lấy slice của acc_next tại MAC; carry cho cột sau lấy acc_q đã chốt rồi ASR32 vào mux. Low columns vẫn góp carry dù không emit.',
  'ASR là nối dây/slice sign extension cho shift32; không tạo barrel shifter tổng quát. Native64 seed0.'])

c=Circuit('Combine và C5',430)
c.node('partial',25,30,210,75,'PARTIAL RAM ngoài','p0 rồi p0+p1','ram')
c.node('c4',310,30,210,75,'C4 ngoài','p0+p1+carry')
c.node('mux',310,225,210,75,'MUX C5 operands','p0,p1 hoặc p2,sum','mux')
c.node('c5',590,225,170,75,'C5 SUB33','A+~B+!borrow')
c.node('out',815,225,175,75,'FF T / side','t_valid + meta','ff')
c.edge('partial','c4');c.edge('c4','partial',ss='B',ds='B',via=[(415,155),(130,155)])
c.edge('partial','mux',ss='B',ds='L',via=[(130,262)])
c.edge('mux','c5');c.edge('c5','out');c.text(555,75,'p1 limb → C4 / C5',16)
c.text(25,370,'Carry_sum, borrow_real, borrow_imag là state riêng; limb0 bắt đầu0.',17)
sheet('S16','ft_fft_combine: RAM, C4 và một subtract C5','ft_fft_combine',c,'real=p0-p1; partial=p0+p1; imag=p2-partial, wrap theo W.','p0/p1 write partial và C5 capture tại combine; free ở p2 limb cuối.',
 ['C4 không nằm bên trong combine; hình C4 là kết nối tới instance chung của tile.',
  'MUX C5 đổi thứ tự operand theo product; không giữ một borrow dùng chung cho cả hai phép trừ. Side được chốt cùng T trước khi buffer free.'])

c=Circuit('Native alignment',400)
row(c,30,['A64 + 1 bias','C0/C1 có sẵn','FF low / high align','SIGN WIRING >>1'],['box','box','ff','box'],['carry riêng re/im','(A+1)±B wrap64','giữ root/tag/buffer','2 branch sum/diff'])
c.node('lower',245,235,250,62,'LOW out = {hi[0],lo[31:1]}')
c.node('upper',600,235,330,62,'HIGH out = {hi[31],hi[31:1]}')
c.text(20,355,'Hai box LOW/HIGH là dây nối, không phải hai phép shift độc lập trên dữ liệu chưa ghép.',16)
sheet('S17','ft_native_align: increment carry và half64 bằng dây','ft_native_align',c,'half(v)=signed(wrap64(v+1))>>>1; bias A dùng lại cho cả (A+1)+B và (A+1)-B.','Native inverse64 thêm2 clock input alignment; H11, free29.',
 ['C0/C1 ở hình thuộc addsub dùng chung, không instantiate thêm hai adder64 trong native_align.',
  'Phải chờ đúng high beat trước khi tạo low output có hi[0]. Root/tag/first đi cùng data; không lấy context/buffer hiện tại thay token cũ.'])

c=Circuit('Tile integration',440)
for key,x,y,w,h,t in [('as',20,20,215,75,'ft_addsub C0..C3'),('state',20,235,215,95,'ft_tile_state / RAM'),('owner',285,20,180,75,'MUX owner + cfg'),('leaf',535,20,205,75,'leaf_array ×1'),('mont',285,235,180,95,'ft_mont_pipe'),('fft',535,235,205,95,'MAC + combine'),('c4',805,20,180,75,'C4 ×1'),('rsp',805,235,180,95,'post / response FF')]:c.node(key,x,y,w,h,t,kind='ff' if key=='rsp' else 'box')
c.edge('as','owner');c.edge('owner','leaf');c.edge('state','mont');c.edge('fft','rsp')
c.edge('mont','owner',ss='T',ds='B',control=False)
c.edge('fft','owner',ss='T',ds='B',via=[(515,205),(515,120),(375,120)])
c.edge('leaf','mont',ss='B',ds='T',via=[(635,160),(375,160)])
c.edge('leaf','fft',ss='B',ds='T')
c.edge('fft','c4',ss='R',ds='B',via=[(775,282),(775,150),(895,150)])
c.edge('mont','c4',ss='R',ds='T',via=[(490,282),(490,5),(895,5)])
c.edge('mont','rsp',ss='B',ds='B',via=[(375,365),(895,365)])
c.text(20,400,'Leaf/C4 dùng chung; return từ C4 về mont/FFT theo mode (không vẽ thêm để tránh chồng dây).',16)
sheet('S18','ft_tile: ranh giới physical sharing và output FF','ft_tile',c,'CT/GS đổi nơi dùng addsub; FFT wrap, NTT modulo; packed two-group nhưng chỉ một context q.','COLD→CFG→READY→BUSY; response không có ready; busy gồm output pending.',
 ['Chỉ1 leaf array,1 C4 và1 addsub/tile. Mont/FFT cấp operand vào owner mux; product về hai controller nhưng valid được qualify theo context, không nối serial hai engine.',
  'Các mux vật lý đi theo cổng leaf/C4/side; không dựng crossbar kết nối mọi khối. Chặn nhận CFG khi busy và giữ cấu hình cũ.'])

c=Circuit('Decode pipeline',400)
for i,(t,s) in enumerate([('FF snapshot','E0 cfg/q/qi'),('D1 + FF','mode/range'),('D2 + FF','stages/bank jobs'),('D3/D4 + FF','planes/rows'),('D5 FF valid','ctx128/done')]):
    c.node(str(i),15+i*200,55,170,90,t,s,'ff')
    if i:c.edge(str(i-1),str(i))
c.node('guard',235,245,530,65,'EQ / LT / AND legality tree','odd q, limits logn/hmin/fmt, rows_per_buffer<=128')
c.text(20,365,'D3 và D4 là hai boundary khác nhau; box gộp trên hình không bỏ một clock.',16)
sheet('S19','ft_cfg_decode: comparator và pipeline5 stage','ft_cfg_decode',c,'Geometry dùng min/max/cộng trừ log; rows=1<<rowlog; capacity exponent kiểm trước dịch/narrow.','E0 snapshot; D1..D5 E1..E5; core E6; frontend E7.',
 ['Mỗi stage có valid tương ứng. Không nối combinational toàn cfg word qua mọi phép so sánh vào ready.',
  'Dùng widened temporaries để bắt hmin>logn và underflow; decode không kiểm primality/root order.'])

c=Circuit('Data RAM bank',400)
row(c,40,['ren / ra8\nwen / wa8 / wd32','RAM bank256×32','FF rd32 / rvalid','Core route FF'],['in','ram','ff','ff'],['mỗi bank','1R sync +1W','sau cạnh R','R+1'])
c.node('raw',260,245,440,65,'EQ8(ra,wa) AND ren AND wen','assert forbidden same-bank/same-row RAW')
c.text(20,365,'Lặp32 bank; row0/row1 theo geometry. Reset rvalid, không reset nội dung RAM.',17)
sheet('S20','ft_data_mem: một bank1R1W, lặp32 lần','ft_data_mem',c,'32×256×32 bit; ping-pong dùng hai vùng row trong cùng bank.','RAM data sau R; route FF R+1; tile fire R+2.',
 ['FF rd trong hình là read register của cổng RAM/inference, không thêm một tầng output FF sau RAM đã sync.',
  'RAW comparator là assertion/monitor để kiểm lịch; không tuyên bố phần cứng tự chữa mọi descriptor sai.'])

c=Circuit('Root RAM bank',400)
row(c,45,['host_we / dest[t]','AND write enable','ROOT512×32','root_data32 / valid'],['in','box','ram','out'],['addr9/data32 chung','we=host_we & dest[t]','read compute_addr9','R đồng bộ'])
c.node('ren',285,240,450,65,'compute_ren[t] / compute_addr9','mỗi tile một root bank;16 instance')
c.edge('ren','r45_2',ss='R',ds='B',via=[(625,272)])
c.text(20,355,'Root assets được nạp sẵn; không có sin/cos, powmod hay multiplier trong RAM.',17)
sheet('S21','ft_root_mem: AND destination và cổng read đồng bộ','ft_root_mem',c,'Root word32 theo format; packed root16 đúng miền R16 trước khi nạp.','Root read cùng R với data; root_valid đi cùng root_data qua route alignment.',
 ['Host chỉ ghi khi idle. ROOT write invalidate root_committed; COMMIT không kiểm root mathematical order.',
  'Lặp16 bank, address compute chung nhưng enable từng tile. Không reset array hoặc nhân đôi bảng root cho mỗi precision.'])

c=Circuit('CG address logic',400)
row(c,35,['cfg + k/plane/tag','SLICE / SHIFT\nROTATE / XOR','CONCAT row fields','row / route selects'],['in','box','box','out'],['read_ctx / write_ctx','n small: rol\nn large: XOR topbit','buffer | plane | row','combinational'])
c.node('roots',270,245,470,65,'root_base + bounded root-index','mask / beat và root-span đã kiểm')
c.text(20,355,'Rotate là hoán vị dây + mux theo cấu hình; không gọi đó là một phép nhân/chia địa chỉ.',16)
sheet('S22','ft_cg_addr: slice, rotate, XOR và nối row','ft_cg_addr',c,'row=buf*rows*planes+pl*rows+(p>>5); bank large=(p&31) XOR (topbit<<4).','Tổ hợp, không clk/rst. Core sở hữu các register boundary.',
 ['Read dùng read_stage; write dùng write_ctx/out_tag của output. Chồng lấp tầng không được lấy chung một stage counter.',
  'Cấu hình n0 tránh rotate width0; mọi field row không chồng bit sau range-check. Không pipeline one-hot32.'])

c=Circuit('MUX4 structural route',420)
for i,t in enumerate(['bank[2t] / bank[(2t)^16]','bank[t] / bank[t+16]']):
    c.node('in'+str(i),20,30+i*150,300,65,t,kind='in')
    c.node('m'+str(i),390,30+i*150,190,65,'MUX2 ×32','swap hoặc far','mux');c.edge('in'+str(i),'m'+str(i))
c.node('final',680,105,155,70,'MUX2 ×32','near','mux')
c.edge('m0','final');c.edge('m1','final');c.pin('x',890,125,'x32',True,w=90);c.edge('final','x')
c.text(20,340,'Đường y tương tự, thêm AND với !dummy. Mask/valid dùng cùng select. Lặp16 tile.',16)
c.text(20,375,'MUX2 bit-level xem S02; tầng mux là tổ hợp, không tự thêm FF giữa hai tầng.',16)
sheet('S23','ft_cg_route: bốn nguồn bằng ba mux2/bus','ft_cg_route',c,'MUX4 = MUX2(near, MUX2(swap,...), MUX2(far,...)); y_dummy=0.','Route tổ hợp tới request FF R+1; write route tới bank commit E+1.',
 ['Mỗi đầu vào có các nguồn constant theo tile, không có selector bank tùy ý. Không dựng mux32 trên mỗi output.',
  'Write route hoán vị theo write_ctx, không dùng select read hiện tại; output bank write-mask cũng đi đúng đường dữ liệu.'])

c=Circuit('FFT program counters',410)
row(c,35,['accepted_first / mask','FF p/step/mask','LOOKUP(i,j,flags)','prog FF / local tile'],['in','ff','box','out'],['cfg L/H/K','inc step; roll p0..2','L1/L2/L4 constant table','early=launch-1'])
c.node('eq',285,235,450,65,'EQ(step,K-1) → carry sang product','enable chỉ theo scheduled program')
c.text(20,365,'ROM/table nhỏ chứa index và flags; không chứa product và không tạo multiplier.',17)
sheet('S24','ft_fft_program: incrementer, EQ và LUT index','ft_fft_program',c,'launch=H+pK+s; K1/4/15. L4 emit ở step5/9/12/14.','Prog phát early; local tile register địa chỉ trước khoảng operand launch.',
 ['Program chung16 tile, mask giữ từ accepted_first. Token return không lấy counter program sống.',
  'Các bit first/last-column/emit được decode từ lookup và delay cùng product. Không tiến step khi không có program hợp lệ.'])

c=Circuit('Issue counters and FSM',400)
row(c,35,['stage_desc / due20','FF k/plane/beat','EQ last + phase slot','AND rd_issue'],['in','ff','box','box'],['snapshot stage_fire','increment + wrap','due==epoch; credit','mask / first / stage_done'])
c.node('fsm',295,245,435,65,'STATE FF EMPTY / WAIT_DUE / ISSUE','next-state priority theo fsm.json','ff')
c.text(20,365,'last_read + next_stage_fire: vẫn phát done của tầng cũ, nạp context tầng mới cùng cạnh.',16)
sheet('S25','ft_issue_ctrl: bộ đếm và cổng qualify issue','ft_issue_ctrl',c,'issue=due/slot hợp lệ AND context-credit; counters liệt kê read theo geometry.','Read R → tile fire R+2; stage_issue_done là last read, không phải DONE kernel.',
 ['Không dùng phi_launch làm phase nhận request. Scheduled deadline miss không được tự stall rồi đổi khoảng gap.',
  'Counter context chuyển tầng bằng mux load/increment/hold, priority reset cao nhất.'])

c=Circuit('Stage controller',410)
row(c,35,['Descriptor RAM10×46','ADD20 due + gap','Context FIFO16×36','HEAD context FF'],['ram','box','ram','ff'],['host write / prefetch','first-read timestamp','push due-1; pop tail','writeback luôn sẵn'])
c.node('tail',275,235,470,75,'OR tail_seen + EQ(active_mask)','owner = lowest set bit, không cố định tile0')
c.text(20,365,'Epoch FF20 riêng với kernel cycle FF32. Descriptor-valid bitmap thuộc core.',17)
sheet('S26','ft_stage_ctrl: RAM descriptor, timestamp và context','ft_stage_ctrl',c,'next_due=old_first_read+gap; all_tail=((seen|commit)&mask)==mask.','Context push trước first_read1 clock; pop ở terminal bank commit của mọi active tile.',
 ['Gap cuối0 bị bỏ qua; không dùng gap làm delay sau last read. Chỉ một context mới mỗi stage.',
  'FIFO có head/next lookahead S27 để không tạo bubble khi output hai tầng ở hai clock liên tiếp.'])

c=Circuit('FIFO lookahead',430)
c.node('ram',20,30,210,90,'Backing RAM16×36','1W / lookahead read','ram')
c.node('next',325,30,210,90,'FF next36','prefetch / bypass','ff')
c.node('head',640,30,210,90,'FF head36','write_ctx valid','ff')
c.edge('ram','next');c.edge('next','head')
c.node('incoming',20,255,210,65,'Incoming push36')
c.node('mux',330,255,520,65,'MUX RAM / next / incoming','count0/1/2/full và pop+push')
c.edge('incoming','mux');c.edge('mux','next',ss='T',ds='B',via=[(590,190),(430,190)])
c.edge('mux','head',ss='R',ds='B',via=[(895,287),(895,170),(745,170)])
c.text(20,385,'Empty forward không hợp thức hóa response thiếu context; queue không được thêm stall vào output.',16)
sheet('S27','Context FIFO: head/next FF và bypass vật lý','ft_stage_ctrl',c,'count_next=count+push-pop; mux selection phụ thuộc old count và sự kiện đồng thời.','Tail-pop E → head mới sau E sẵn cho output kế ở E+1.',
 ['count1 pop+push: incoming thay head. count2 pop+push: old next→head, incoming→next; bypass tránh đọc nhầm word RAM vừa ghi.',
  'Full pop+push phải lấy head cũ; không zero queue hoặc thay head bằng incoming mới nhất.'])

c=Circuit('Writeback gates',430)
row(c,35,['tile_valid / tags','XOR-EQ bank\nmask cohort compare','AND write_ok','bank wen / data'],['in','box','box','out'],['owner từ ctx','check tất cả active','ctx & cohort & !abort','commit edge'])
c.node('tail',300,250,460,65,'AND last-tag & bf_last & actual wen','tail_commit[t] gắn với bank commit thật')
c.text(20,380,'route data và bank row dùng write_ctx. Fault khóa invalid write; không tạo response backpressure.',16)
sheet('S28','ft_writeback: EQ tag, mask và AND write-enable','ft_writeback',c,'write_ok=ctx_valid AND cohort_ok AND NOT(abort/fault). tail_commit chỉ trên terminal write thật.','Response sau E → bank commit E+1; tail-pop cùng commit; DONE muộn hơn khi drain.',
 ['Owner chỉ chọn tag tham chiếu; vẫn kiểm mask và tag của tất cả active tile, kể cả khi tile0 không active.',
  'Không thêm full-width write FF trong0.2. Comparator/qualify là tổ hợp từ các boundary đã khóa.'])

c=Circuit('Host mapping phases',430)
row(c,30,['FF line/data128','MAP 4 word\nEQ bank pairwise','PHASE + SELECT FF','bank1R/1W'],['ff','box','ff','ram'],['H0 snapshot','conflict scheduling','H1→H2..H(p+1)','p=1..4'])
c.node('gather',300,245,470,75,'MUX write-enable → gather FF128','capture từng phase trước, cuối ở G')
c.edge('r30_3','gather',ss='B',ds='R',via=[(875,282)])
c.text(20,385,'Mỗi word gather chỉ cập nhật khi phase đúng; giữ các word đã thu từ phase trước.',16)
sheet('S29','ft_host_map: so bank, mux phase và gather FF','ft_host_map',c,'Tách line thành4 bank/row; phân phase sao cho mỗi bank tối đa1 access trong một phase.','H0 snapshot; H1 prep; H2..H(p+1) service; G=H(p+2) capture cuối.',
 ['Số phase do bank conflict thực, không lấy fmt làm số phase. Selector pipeline phải căn read RAM result.',
  'Không chỉ gather tất cả word ở cuối từ output RAM cuối; phải capture phase cũ trong khi issue phase kế.'])

c=Circuit('Normalizer3 stage',430)
row(c,35,['line128 / fmt / s','FF bias + carry','FF sum wrapW','FF ASR / valid'],['in','ff','ff','ff'],['G gather','G+1','G+2','G+3'])
c.node('bound',180,240,640,70,'CARRY CUT theo fmt + SIGN EXT theo biên W','4×32 hoặc2×64 hoặc1×128; bypass NTT/native cùng latency')
c.text(20,380,'Mạng shift mux theo s; cộng rounding và wrap trước arithmetic shift. Không chia số nguyên signed /2^s.',16)
sheet('S30','ft_read_normalize: carry cut và arithmetic shifter','ft_read_normalize',c,'div2e(v,s)=signed(wrapW(v+2^(s-1)))>>>s, branch s0 trả v.','G+1 bias/carry, G+2 sum, G+3 out_valid; core G+4, frontend G+5.',
 ['Cắt carry giữa hai số64 hoặc bốn số32. Sign extension chỉ dùng sign của đúng giá trị W, không sign của cả line.',
  'Các box FF biểu diễn boundary đã khóa, không phải thêm một FF sau từng bit mux của barrel shifter.'])

c=Circuit('Core state and ownership',430)
row(c,30,['cmd snapshot / guards','STATE FF13 states','DECODE + priority','local cfg/reset FF'],['in','ff','box','ff'],['ack / kernel lifecycle','FSM core','abort > fault > normal','gần tile'])
c.node('count',25,245,220,75,'FF cycles32 / active','enable old active','ff')
c.node('drain',330,245,420,75,'OR pending + AND all-drained','queue, tile busy, pipes, tail, commit')
c.node('done',815,245,170,75,'done / error pulse','sau drain')
c.edge('drain','done');c.text(20,390,'stage_ctrl không sở hữu executor FSM/cycles thứ hai. Host phase FSM nằm ở host_map.',16)
sheet('S31','ft_core: state FF, priority và cây drain','ft_core',c,'DONE=all_reads_issued AND context_empty AND tiles_idle AND pipes_empty AND tail_clear, sau last commit.','START X→reset X+1→CFG X+2→settle X+3→ctx X+4→RUN X+5.',
 ['Cycle counter không chạy cho host/CFG; identity cycles0. Epoch20 thuộc stage, cycle32 thuộc core.',
  'Sơ đồ state bit không ép one-hot hay binary encoding; mapper/implementation chọn, hành vi theo7 FSM khóa.'])

c=Circuit('Frontend snapshot',410)
row(c,35,['MMIO enqueue160','FF snapshot + P0','FF P1 / valid hold','core fire / WAIT_ACK'],['in','ff','ff','box'],['full-width guard','reserve pending','ready0 giữ nguyên','ack release'])
c.node('abort',270,240,470,70,'RESET decode → ABORT_SEND FF → pulse','bypass normal pending; chờ abort_ack')
c.text(20,370,'ACK clear status ở bridge; không đưa ACK vào normal command queue. Không đọc pins MMIO sau enqueue.',16)
sheet('S32','ft_cmd_frontend: snapshot FF và token hold','ft_cmd_frontend',c,'fire=valid AND ready; payload giữ nguyên trong lúc pending.','FREE→P0→P1→WAIT_ACK; RESET đi ABORT_SEND/ABORT_WAIT, abort_req1 clock.',
 ['P1 giữ cả opcode/data khi core chưa sẵn sàng. Không chỉ giữ valid còn payload lấy live pins.',
  'READ line/ack/output/read_complete/pending cập nhật nguyên tử tại frontend; soft reset không hạ AXI B/R đang stall.'])

c=Circuit('Sticky logic',420)
c.pin('old',20,35,'old_done',w=130);c.pin('clear',20,155,'clear_status',w=150)
c.gate('inv',225,145,'NOT','!clear');c.gate('hold',430,45,'AND','hold_old')
c.pin('new',420,235,'core_done',w=155);c.gate('or',665,80,'OR','next_done')
c.node('prio',800,55,180,95,'MUX clear priority','rst / accepted CFG-START','mux')
c.node('doneff',800,240,180,75,'FF done','synchronous','ff')
c.edge('old','hold',ds='I0');c.edge('clear','inv');c.edge('inv','hold',ds='I1',via=[(360,167),(360,77)])
c.edge('hold','or',ds='I0');c.edge('new','or',ds='I1',via=[(620,252),(620,112)])
c.edge('or','prio');c.edge('prio','doneff',ss='B',ds='T')
c.text(20,375,'error_next = old_error OR qualified(core_done&error, ack&ack_error); ACK không clear error.',16)
sheet('S33','Frontend status: AND/OR và reset/clear priority','ft_cmd_frontend',c,'done_next=(old_done & !clear_status)|core_done, trừ accepted CFG/START clear có ưu tiên cao hơn.','Status FF cập nhật tại cạnh; new completion thắng ACK clear khi không có accepted CFG/START.',
 ['OR trên hình là cổng biểu diễn chức năng; mux priority trước D giữ quy tắc sticky chính xác.',
  'Không OR mức core_error cũ vào error mỗi clock; chỉ lấy lỗi tại completion/ack được qualify. read_complete có điều kiện clear riêng theo spec10.'])

c=Circuit('AXI channels',430)
c.node('aw',15,20,180,75,'AW slot FF','addr12 + valid','ff');c.node('w',15,205,180,75,'W slot FF','data32/strb4 + valid','ff')
c.node('join',285,90,210,95,'AND commit','AWfull & Wfull & Bfree')
c.node('b',595,90,170,95,'B hold FF','valid / resp','ff');c.pin('bready',830,110,'BREADY',w=155)
c.edge('aw','join');c.edge('w','join');c.edge('join','b');c.edge('bready','b',ss='L',ds='R',control=True)
c.node('r',280,290,485,70,'AR fire → R snapshot/hold FF','RVALID/RDATA/RRESP ổn định khi !RREADY','ff')
c.text(20,405,'AW và W độc lập, không giả định thứ tự. Bus reset clears slots; soft core RESET giữ B/R.',16)
sheet('S34','ft_axil_top: AW/W slots, join và B/R hold','ft_axil_top',c,'Write commit khi đã nhận đủ address/data và có chỗ B. Read snapshot khi AR fire.','AXI handshake theo mỗi channel; B không phải kernel DONE hoặc core command ack.',
 ['Một write/read outstanding. Giữ RDATA của status đã snapshot dù status nội bộ thay đổi khi R stall.',
  'Không ghép AW cũ với W mới sau bus reset. Invalid address/alignment/command trả SLVERR theo map3.1.'])

c=Circuit('Byte merge gates',400)
row(c,25,['wstrb[3:0]','REPLICATE8 mỗi bit','AND old/~mask\nAND data/mask','OR → FF reg32'],['in','box','box','ff'],['byte select','mask32','hai AND bank32','write-enable commit'])
c.node('cmd',250,235,510,65,'Command decode EQ / onehot / alignment','command old=0 khi merge; field full-width kiểm trước narrow')
c.text(20,355,'Mỗi bit merged=(old AND !mask) OR (wdata AND mask); payload snapshot sau merge hợp lệ.',16)
sheet('S35','AXI byte-enable và cổng merge32','ft_axil_top',c,'mask32=concat(repeat8(wstrb[i])); merged=(old&~mask)|(wdata&mask).','Register update đúng một lần khi AW/W được commit; không lặp write lúc B bị stall.',
 ['Mask1 byte không làm thay các byte khác. Command old0 khác các register RW có old value.',
  'Không thêm tín hiệu security từ AWPROT/ARPROT nếu chưa hiện thực. Các cổng bus đầy đủ nằm trong chương27.'])

# Gate-level expansions referenced by all bus-level structural sheets.
c=Circuit('MUX2 gate expansion',400)
c.pin('d0',20,25,'d0',w=85);c.pin('d1',20,215,'d1',w=85);c.pin('s',20,115,'s',w=85)
c.gate('inv',200,105,'NOT','!s');c.gate('a0',460,35,'AND','d0 AND !s')
c.gate('a1',460,210,'AND','d1 AND s');c.gate('or',730,120,'OR','out');c.pin('out',885,125,'out',True,w=100)
c.edge('s','inv');c.edge('d0','a0',ds='I0',via=[(385,42),(385,47)])
c.edge('inv','a0',ds='I1',via=[(345,127),(345,67)])
c.edge('d1','a1',ds='I1');c.edge('s','a1',ds='I0',via=[(145,132),(145,300),(400,300),(400,222)])
c.edge('a0','or',ds='I0',via=[(660,57),(660,132)]);c.edge('a1','or',ds='I1',via=[(680,232),(680,152)]);c.edge('or','out')
c.text(20,360,'Lặp cho N bit; tất cả bit dùng chung s. D0 chọn khi s=0, D1 khi s=1.',17)
sheet('S02B','MUX2 được mở thành NOT, hai AND và OR','primitive',c,'out=(d0 AND NOT(s)) OR (d1 AND s).','Không có FF; chỉ thêm delay tổ hợp trong stage hiện hữu.',
 ['MUX4 có thể ghép3 MUX2. Mux enable trước DFF còn có nhánh hồi tiếp Q làm d0.',
  'Đây là mức logic chức năng. FPGA thường gộp NOT/AND/OR vào LUT hoặc mux primitive, không bắt buộc có4 cell rời.'])

c=Circuit('EQ and NZ bit tree',410)
for i,y in [(0,25),(1,130),(31,250)]:
    c.pin('a'+str(i),20,y,f'A[{i}], B[{i}]',w=170)
    c.gate('x'+str(i),280,y,'XOR',f'x[{i}]')
    c.edge('a'+str(i),'x'+str(i))
c.node('reduce',480,100,190,125,'OR tree32','5 mức OR2 logic')
for i,port in [(0,'L0'),(1,'L1'),(31,'L2')]:c.edge('x'+str(i),'reduce',ds=port)
c.gate('not',745,140,'NOT','EQ');c.edge('reduce','not');c.pin('eq',885,145,'EQ',True,w=95);c.edge('not','eq')
c.text(20,365,'Các bit2..30 lặp XOR cùng mẫu; NZ(A) bỏ XOR và NOT, chỉ còn OR-reduction(A).',16)
sheet('S02C','Comparator EQ/NZ: XOR bit-slice và cây OR','primitive',c,'EQ(A,B)=NOT(OR_i(A[i] XOR B[i])); NZ(A)=OR_i(A[i]).','Tổ hợp; pipeline EQ chỉ khi contract đã có register boundary.',
 ['OR tree32 có5 mức OR2 trong cấu trúc logic cân bằng; LUT6 có thể gộp nhiều mức nên không dùng số này để tính Fmax.',
  'Trong gate expansion hình dùng bundle hai input A[i]/B[i] vào XOR; cách tách hai chân giống S01. Cây này dùng ở tag, bank conflict, full/empty và decode.'])

c=Circuit('C2 C3 expanded mux',430)
row(c,30,['S_q / Q_q\nfa / fb / fci','MUX PL → A35/B35','C2 ADD35','slice + NTT mux'],['in','mux','box','mux'],['guard theo ch28','trước arithmetic','SQ35 / no-borrow','s32 / fs33'])
row(c,230,['D_q / Q_q\nwa / wb / wci','MUX PL → A34/B34','C3 ADD34','slice + NTT mux'],['in','mux','box','mux'],['guard theo ch28','trước arithmetic','DQ34 / flags','d32 / ws33'])
c.text(20,395,'Raw S_q/D_q bypass tới output mux; candidate chỉ được chọn theo flag đúng lane đã chốt.',16)
sheet('S07B','C2/C3: thấy rõ mux operand, adder và mux output','ft_addsub',c,'C2 NTT S-q hoặc fa+fb+fci; C3 NTT D+q hoặc wa+wb+wci.','Cùng khoảng sau intermediate FF tới FF consumer; không chèn FF giữa mux và adder.',
 ['PL là plain đã register cùng S/D, không là plain của request mới. fs/ws vẫn lấy các operand phụ sống từ FF của caller.',
  'Adder35 và adder34 là hai chain riêng vì cần hai kết quả đồng thời; mỗi chain dùng lại giữa FFT/NTT. Guard và slice chính xác ở chương28.'])

c=Circuit('Increment bit slice',410)
c.pin('qi',20,35,'Q[i]',w=95);c.pin('ci',20,210,'carry[i]',w=115)
c.gate('xor',280,35,'XOR','inc[i]');c.gate('and',280,200,'AND','carry[i+1]')
c.node('mux',515,35,185,75,'MUX reset/en','D hoặc Q hold','mux');c.node('ff',790,35,170,75,'FF Q[i]','posedge','ff')
c.edge('qi','xor',ds='I0');c.edge('ci','xor',ds='I1',via=[(225,227),(225,67)])
c.edge('qi','and',ds='I0',via=[(170,52),(170,212)]);c.edge('ci','and',ds='I1');c.edge('xor','mux');c.edge('mux','ff')
c.edge('ff','mux',ss='B',ds='B',via=[(875,170),(607,170)])
c.text(20,355,'carry[0]=1 khi increment. Lặp cho width3/4/5/20/32; wrap là bỏ carry cuối.',17)
sheet('S14B','Counter/pointer: XOR, AND, mux hold và FF','ft_tile_state',c,'inc[i]=Q[i] XOR carry[i]; carry[i+1]=Q[i] AND carry[i].','State đổi tại cạnh reserve/release/epoch; reset ưu tiên trước enable.',
 ['Đây là khai triển incrementer dùng cho pointer và counter. Count ±1 còn cần chọn cộng/trừ theo hai event; không thay bằng tăng mọi clock.',
  'Pointer có thể wrap nhưng occupancy không được wrap full thành0. Count FFT4 bit, side5 bit là width đã khóa.'])

c=Circuit('Arithmetic shifter gates',420)
row(c,40,['rounded W-bit','MUX2 ×W shift1','MUX2 ×W shift2','MUX2 ×W shift4'],['in','mux','mux','mux'],['sau wrap stage2','select s[0]','select s[1]','select s[2]'])
c.node('last',770,235,210,70,'MUX2 ×W shift8','select s[3]','mux')
c.edge('r40_3','last',ss='B',ds='T')
c.text(20,220,'Một bit: y[i] = sel ? x[i+k] : x[i]; nếu i+k>=W thì dùng sign bit của cùng giá trị.',16)
c.text(20,365,'Bốn tầng mux là tổ hợp trong stage G+2→G+3, không có FF ở giữa.',17)
sheet('S30B','Normalizer: arithmetic barrel shifter bằng mux2','ft_read_normalize',c,'Dịch theo các trọng số1/2/4/8 tạo s0..9; bit ngoài biên W được thay bằng sign của giá trị đó.','rounded register G+2 → mạng mux tổ hợp → output register G+3.',
 ['Ở fmt32 lặp4 miền, fmt64 lặp2 miền; không để x[i+k] chạy sang số kế bên trong line128.',
  'Mạng này là một cách phân rã tổ hợp hợp lệ của stage3. Không đổi bias/wrap hoặc thêm stage chỉ để hợp hình.'])

SHEETS.sort(key=lambda s:s['code'])

class Figure(Flowable):
    def __init__(self,drawing,width=744):
        super().__init__();self.drawing=drawing;self.width=width;self.height=width*drawing.height/drawing.width
    def draw(self):
        self.canv.saveState();self.canv.scale(self.width/self.drawing.width,self.width/self.drawing.width)
        renderPDF.draw(self.drawing,self.canv,0,0);self.canv.restoreState()

def append_annex(story,md,here):
    assets=Path(here)/'structural_svg';assets.mkdir(exist_ok=True)
    title_style=ParagraphStyle('schematic_title',fontName='VN-Bold',fontSize=16,leading=20,textColor=NAVY,spaceAfter=7)
    small=ParagraphStyle('schematic_small',fontName='VN',fontSize=9,leading=12.6,textColor=NAVY,spaceAfter=4)
    mono=ParagraphStyle('schematic_mono',fontName='Mono',fontSize=8.5,leading=12,textColor=TEAL,spaceAfter=5)
    manifest=[]
    for s in SHEETS:
        story.extend([NextPageTemplate('wide'),PageBreak()])
        title=f'{s["code"]}. {s["title"]}'
        story.append(Paragraph(html.escape(title),title_style))
        story.append(Paragraph(html.escape('Module: '+s['module']+' | Hình structural tham chiếu; dây liên tục=data, tím đứt=control.'),small))
        drawing=s['circuit'].drawing();svg=assets/(s['code']+'_'+s['module']+'.svg')
        renderSVG.drawToFile(drawing,str(svg))
        # SVG is an editable deliverable: replace internal ReportLab font aliases
        # with actual system families so it also renders outside this builder.
        svg_text=svg.read_text(encoding='utf-8')
        svg_text=svg_text.replace('font-family: VN-Bold;','font-family: Arial, sans-serif; font-weight: bold;')
        svg_text=svg_text.replace('font-family: VN;','font-family: Arial, sans-serif;')
        svg.write_text(svg_text,encoding='utf-8')
        story.append(Figure(drawing));story.append(Spacer(1,7))
        for label,value in [('Phép toán',s['formula']),('Clock / boundary',s['clock'])]:
            story.append(Paragraph('<b>'+label+':</b> '+html.escape(value),small))
        for i,note in enumerate(s['notes'],1):story.append(Paragraph(f'<b>{i}.</b> '+html.escape(note),small))
        md.extend(['## '+title,'Module: '+s['module'],f'![{title}](structural_svg/{svg.name})',s['formula'],s['clock']]+s['notes']+[''])
        manifest.append({'id':s['code'],'title':s['title'],'module':s['module'],'svg':svg.name,'sha256':hashlib.sha256(svg.read_bytes()).hexdigest()})
    (Path(here)/'structural_manifest.json').write_text(json.dumps({'guide':'1.2','figures':manifest,'not_synthesized_netlist':True},ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
