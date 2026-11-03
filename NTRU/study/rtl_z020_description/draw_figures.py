"""Draw RTL operator/gate schematics; not a fabricated vendor gate netlist."""
from pathlib import Path
from html import escape
import math
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/figures/rtl_z020'
OUT.mkdir(parents=True,exist_ok=True)
NAVY='#17324d';BLUE='#245b91';WIRE='#52677c';GREEN='#e5f3ed';GRAY='#edf1f5';GOLD='#fff2cc'
inventory=[]

class Fig:
    def __init__(self,name,title,sub,h=650):
        self.name=name;self.w=1360;self.h=h
        self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="{h}" viewBox="0 0 1360 {h}">',
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#52677c"/></marker></defs>',
            f'<rect width="1360" height="{h}" fill="white"/>']
        self.text(35,38,title,25,anchor='start',weight='bold')
        self.text(35,72,sub,16,anchor='start')
    def text(self,x,y,s,size=17,anchor='middle',weight='normal'):
        lines=s.split('\n');start=y-(len(lines)-1)*size*.62
        for i,line in enumerate(lines):
            self.s.append(f'<text x="{x}" y="{start+i*size*1.24}" text-anchor="{anchor}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{NAVY}">{escape(line)}</text>')
    def wire(self,points,label='',at=None,arrow=True):
        pts=' '.join(f'{x},{y}' for x,y in points)
        self.s.append(f'<polyline points="{pts}" fill="none" stroke="{WIRE}" stroke-width="2" stroke-linejoin="round"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
        if label:
            x,y=at or points[len(points)//2];self.text(x,y-9,label,14)
    def box(self,x,y,w,h,label,fill=GRAY,size=17,dash=False):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{BLUE}" stroke-width="1.8"'+(' stroke-dasharray="6,4"' if dash else '')+'/>')
        self.text(x+w/2,y+h/2+5,label,size)
    def dot(self,x,y): self.s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{WIRE}"/>')
    def mux(self,x,y,label='MUX2',h=90,invert=False):
        self.s.append(f'<polygon points="{x},{y} {x+80},{y+18} {x+80},{y+h-18} {x},{y+h}" fill="{GOLD}" stroke="{BLUE}" stroke-width="2"/>')
        self.text(x+35,y+h/2+5,label,14)
        self.text(x+10,y+22,'1' if invert else '0',12);self.text(x+10,y+h-13,'0' if invert else '1',12)
    def ff(self,x,y,w,h,label):
        self.box(x,y,w,h,label,GRAY)
        self.s.append(f'<path d="M{x} {y+h-22} l12 8 l-12 8" fill="none" stroke="{BLUE}" stroke-width="1.5"/>')
        self.text(x+12,y+20,'D',12);self.text(x+w-13,y+20,'Q',12)
    def gate(self,x,y,kind,h=50,w=85):
        if kind=='AND':
            d=f'M{x},{y} H{x+w-h/2} A{h/2},{h/2} 0 0 1 {x+w-h/2},{y+h} H{x} Z'
        else:
            d=f'M{x},{y} Q{x+28},{y+h/2} {x},{y+h} Q{x+53},{y+h} {x+w},{y+h/2} Q{x+53},{y} {x},{y} Z'
        self.s.append(f'<path d="{d}" fill="{GREEN}" stroke="{BLUE}" stroke-width="2"/>')
        if kind=='XOR':self.s.append(f'<path d="M{x-7},{y} Q{x+21},{y+h/2} {x-7},{y+h}" fill="none" stroke="{BLUE}" stroke-width="2"/>')
        if kind in ('OR','XOR'):
            for dy in (h/4,3*h/4):self.wire([(x,y+dy),(x+10.5,y+dy)],arrow=False)
        self.text(x+36,y+h/2+5,kind,12)
    def save(self):
        self.text(35,self.h-20,'Theo RTL hiện tại • ADD/MUX/cổng: logic tổ hợp • D/Q: thanh ghi • RAM/DSP: primitive phần cứng.',13,anchor='start')
        (OUT/f'{self.name}.svg').write_text('\n'.join(self.s+['</svg>']),encoding='utf-8')
        inventory.append(dict(name=self.name,width=self.w,height=self.h))

def overview():
    f=Fig('01_toan_loi','1. Toàn lõi hiện tại trên XC7Z020','16 tile giống nhau về chức năng; một context biến đổi tại mỗi thời điểm.',750)
    f.box(30,140,175,100,'Host\nconfig / root\nload / read',GOLD)
    f.ff(250,140,175,100,'P: 341 FF\nnhận gói')
    f.ff(475,140,175,100,'Q: 341 FF\nchuyển gói')
    f.box(720,125,245,130,'Điều khiển CG\nFSM + descriptor\nbộ đếm + lịch tích',GOLD)
    f.box(1050,140,260,100,'Root cache\n16 × 512 × 32\n16 RAMB18E1')
    f.wire([(205,190),(250,190)]);f.wire([(425,190),(475,190)]);f.wire([(650,190),(720,190)])
    f.wire([(965,190),(1050,190)],'địa chỉ',at=(1008,180))
    f.box(35,380,255,140,'Dữ liệu ping-pong\n32 bank × 256 × 32\n32 RAMB18E1')
    f.box(350,390,240,120,'MUX chọn bank\n4 ứng viên / đầu vào\n+ FF yêu cầu',GOLD)
    f.box(665,370,340,160,'16 × tile_a2\nnhân + cộng/trừ dùng chung\nFFT32/64/128 hoặc NTT\n64 DSP48E1 toàn mảng',GREEN)
    f.ff(1080,390,230,120,'Phản hồi đọc\n128 data + 1 valid\n129 FF')
    f.wire([(290,430),(350,430)]);f.wire([(590,430),(665,430)])
    f.wire([(1180,240),(1180,305),(900,305),(900,370)],'root / tile',at=(1060,300))
    f.wire([(840,255),(840,370)],'bước tính',at=(775,340))
    f.wire([(835,530),(835,600),(160,600),(160,520)],'MUX ghi bank + địa chỉ CG',at=(495,594))
    f.wire([(290,480),(320,480),(320,655),(1195,655),(1195,510)],'host adapter: ghép lại dòng 128 bit',at=(735,650))
    f.text(1080,690,'P/Q và phản hồi nằm ngoài u_exec.',15,anchor='start')
    f.save()

def frontend():
    f=Fig('02_nhan_lenh','2. Giữ chỗ và pipeline lệnh','Đường giữ chỗ cho cfg/start/load/read; root và descriptor dùng các cờ riêng.',660)
    f.text(950,105,'334-bit payload clock qua P → Q mỗi chu kỳ; token xác định gói hợp lệ.',14)
    f.box(35,140,245,105,'Ưu tiên yêu cầu\ncfg/start > load > read\n→ main_request',GOLD)
    f.gate(385,170,'AND',70,110)
    f.wire([(280,192),(385,192)],'main_request',at=(335,170))
    f.text(315,115,'frontend_live',16);f.wire([(315,125),(350,125),(350,180),(385,180)])
    f.text(315,278,'NOT reserved',16);f.wire([(330,260),(360,260),(360,225),(385,225)])
    f.ff(580,130,230,100,'P: 341 FF\npayload + 7 token')
    f.ff(900,130,230,100,'Q: 341 FF\npayload + 7 token')
    f.wire([(495,205),(535,205),(535,180),(580,180)],'accept',at=(535,155))
    f.wire([(810,180),(900,180)]);f.wire([(1130,180),(1290,180)],'vào u_exec',at=(1210,169))
    f.ff(575,350,225,95,'accepted_main_d')
    f.gate(900,365,'OR',65,105)
    f.ff(1080,350,225,95,'reserved')
    f.wire([(535,205),(535,397),(575,397)])
    f.wire([(535,300),(860,300),(860,380),(900,380)]);f.dot(535,300)
    f.wire([(800,397),(900,412)]);f.wire([(1005,397),(1080,397)])
    f.wire([(1305,397),(1320,397),(1320,500),(310,500),(310,295)])
    f.box(40,540,1265,65,'reserved_next = accepted_main_d OR (frontend_live AND NOT reserved AND main_request)',GRAY,19)
    f.text(680,320,'Cùng điều kiện accept được dùng cho trạng thái giữ chỗ.',15)
    f.save()

def bank_mux():
    f=Fig('03_mux_bank','3. Mạng chọn dữ liệu tính toán của tile t','Các chỉ số chứa t là hằng elaboration; XOR 16 trong chỉ số là dây nối cố định.',630)
    candidates=[('(2t)^16',150),('2t',230),('t+16',375),('t',455)]
    for label,y in candidates:f.box(40,y-28,190,56,'bank['+label+']',GRAY,18)
    f.mux(390,130,h=120,invert=True);f.mux(390,355,h=120,invert=True);f.mux(775,240,h=145,invert=True)
    for sy,dy in [(150,155),(230,225),(375,380),(455,450)]:f.wire([(230,sy),(310,sy),(310,dy),(390,dy)])
    f.text(430,280,'r_near',16);f.text(430,505,'r_far',16)
    f.wire([(470,190),(630,190),(630,270),(775,270)])
    f.wire([(470,415),(630,415),(630,355),(775,355)])
    f.text(815,415,'rgeom',16)
    f.ff(1020,250,250,130,'req_x[t]\n32-bit register')
    f.wire([(855,312),(1020,312)],'32 bit',at=(935,302))
    f.box(40,545,1230,50,'req_y[t]: near dùng 2t+1; far đảo thứ tự X; rdummy chọn giá trị 0.',GRAY,18)
    f.save()

def full_adder():
    f=Fig('04_cong_1_bit','4. Cổng logic của một bit cộng đầy đủ','Mô tả hàm logic; Vivado ánh xạ carry sang CARRY4 trên Z020.',665)
    for label,y in [('a',165),('b',250),('cin',520)]:f.text(60,y+5,label,20)
    f.gate(270,180,'XOR',60,90);f.gate(720,180,'XOR',60,90)
    f.gate(460,320,'AND',60,90);f.gate(720,420,'AND',60,90);f.gate(1020,355,'OR',70,100)
    f.wire([(90,165),(210,165),(210,195),(270,195)])
    f.wire([(90,250),(230,250),(230,225),(270,225)])
    f.wire([(360,210),(640,210),(640,195),(720,195)],'p = a XOR b',at=(535,192))
    f.wire([(810,210),(1190,210)],'sum',at=(1180,197))
    f.wire([(210,165),(210,335),(460,335)]);f.dot(210,165)
    f.wire([(230,250),(230,365),(460,365)]);f.dot(230,250)
    f.wire([(90,520),(665,520),(665,225),(720,225)])
    f.wire([(580,210),(580,435),(720,435)]);f.dot(580,210)
    f.wire([(665,465),(720,465)]);f.dot(665,465)
    f.wire([(550,350),(960,350),(960,373),(1020,373)])
    f.wire([(810,450),(960,450),(960,407),(1020,407)])
    f.wire([(1120,390),(1250,390)],'cout',at=(1210,380))
    f.box(75,570,1200,55,'sum = a XOR b XOR cin       cout = (a AND b) OR (cin AND (a XOR b))',GRAY,20)
    f.save()

def addsub():
    f=Fig('05_addsub','5. tl_addsub: cộng/trừ, hiệu chỉnh modulus và chọn FFT','Toàn bộ hình là logic tổ hợp hiện tại; chưa có FF cắt giữa raw và correction.',745)
    f.box(35,170,170,90,'a, b\nci, bi\n32 bit',GRAY)
    f.box(265,130,235,105,'Cộng raw\nsum = a+b+ci',GREEN)
    f.box(265,360,235,115,'Trừ raw theo nửa\ndfl, dfh\nborrow có điều kiện',GREEN)
    f.wire([(205,195),(235,195),(235,182),(265,182)])
    f.wire([(235,195),(235,417),(265,417)]);f.dot(235,195)
    f.box(575,130,260,105,'Trừ q theo nửa\nsql, sqh\nborrow từ low → high',GREEN)
    f.box(575,360,260,115,'Cộng lại q\ndql, dqh\ncarry từ low → high',GREEN)
    f.wire([(500,182),(575,182)]);f.wire([(500,417),(575,417)])
    f.box(875,130,185,105,'MUX theo dấu\nchọn raw\nhoặc corrected',GOLD)
    f.box(875,360,185,115,'MUX theo dấu\nchọn raw\nhoặc corrected',GOLD)
    f.wire([(835,182),(875,182)]);f.wire([(835,417),(875,417)])
    f.mux(1140,140,'plain',90);f.mux(1140,372,'plain',90)
    f.wire([(1060,182),(1100,182),(1100,160),(1140,160)])
    f.wire([(500,160),(525,160),(525,105),(1120,105),(1120,210),(1140,210)])
    f.wire([(1060,417),(1100,417),(1100,392),(1140,392)])
    f.wire([(500,390),(525,390),(525,325),(1120,325),(1120,442),(1140,442)])
    f.wire([(1220,185),(1315,185)],'s',at=(1290,173));f.wire([(1220,417),(1315,417)],'d',at=(1290,405))
    f.gate(600,560,'AND',65,100)
    f.text(375,573,'carry/borrow của nửa thấp',17);f.wire([(515,570),(600,575)])
    f.text(470,643,'NOT split',17);f.wire([(530,635),(565,635),(565,607),(600,607)])
    f.wire([(700,592),(1040,592)],'carry/borrow sang nửa cao',at=(885,581))
    f.text(700,690,'split=1: cắt liên kết giữa hai làn 16 bit. plain=1: lấy raw sum/diff cho FFT.',17)
    f.save()

def leaves():
    f=Fig('06_mang_nhan','6. Mảng nhân trong mỗi tile','4 lá 16×16 dùng chung FFT / NTT; mỗi lá suy diễn thành một DSP48E1.',690)
    f.box(35,135,205,100,'Chọn toán hạng\nla/lb và lsa/lsb',GOLD)
    f.ff(300,135,220,100,'ar/br: 16 bit\nsar/sbr: 1 bit')
    f.wire([(240,185),(300,185)])
    f.box(610,120,290,125,'Sign extension\nax = {sar AND ar[15], ar}\nbx = {sbr AND br[15], br}',GREEN,17)
    f.wire([(520,185),(610,185)])
    f.box(990,125,325,115,'DSP48E1\nnhân signed 17×17\nđầu ra hữu ích 33 bit',GREEN)
    f.wire([(900,185),(990,185)])
    f.ff(1000,340,300,100,'pp[1] → pp[2]\n2 tầng product FF')
    f.wire([(1152,240),(1152,340)])
    f.box(45,345,405,115,'Bốn kết quả: p0,p1,p2,p3\ncat = {p1, p0[31:0]}\np2r, p3r và cat có thanh ghi')
    f.wire([(1000,390),(450,390)],'4 lá song song',at=(725,379))
    f.ff(575,515,690,90,'f = cat + (sign_extend(p2r) << 16) + (sign_extend(p3r) << 16)\n65 bit; thanh ghi kết quả fused')
    f.wire([(245,460),(245,560),(575,560)])
    f.text(680,648,'Packed16: lá 0 và 1 tính hai tích riêng; A của lá 2 và 3 được đưa về 0.',17)
    f.save()

def fft():
    f=Fig('07_fft','7. Đường FFT đa precision hiện tại','Giữ 32-bit limb và số lượt khác nhau; không có nhóm tile ghép lại thành một bộ nhân rộng.',700)
    f.box(30,140,240,110,'CT: giữ A, chọn B\nGS: tính A+B, A−B\nnative: wrap64(v+1)\n>>> 1 trước nhân',GOLD)
    f.box(330,140,240,110,'LUTRAM theo limb\nwma / wmx / wmw\nwmsx / wmsw')
    f.box(630,140,270,110,'Lịch p0, p1, p2\nMUX limb + sign\n4 DSP / tile',GREEN)
    f.ff(990,130,320,130,'wacc: 68-bit MAC\nrounding trong winit\nxuất wpl: 32 bit')
    f.wire([(270,195),(330,195)]);f.wire([(570,195),(630,195)]);f.wire([(900,195),(990,195)])
    f.box(45,395,340,125,'T.re = p0 − p1\nT.im = p2 − (p0+p1)\nwps + carry/borrow theo limb',GREEN)
    f.wire([(1150,260),(1150,315),(215,315),(215,395)])
    f.box(455,395,345,125,'CT: fft_ct_addsub(A,T)\nGS: rounding / scaling\nwy0/wy1 có thanh ghi',GREEN)
    f.wire([(385,455),(455,455)])
    f.box(875,395,435,125,'MUX limb hiện tại / trước\nfunnel shift từ 64-bit window\nMUX FFT/NTT → FF rsp',GOLD)
    f.wire([(800,455),(875,455)])
    f.box(45,575,1265,65,'FFT32: 3 tích limb/BF       FFT64: 12       FFT128: 45       (3 × 1/4/15)',GRAY,21)
    f.save()

def ntt():
    f=Fig('08_ntt','8. Montgomery và butterfly NTT hiện tại','NTT32: R=2³²; packed16: R=2¹⁶ và hai làn cắt carry độc lập.',750)
    f.box(30,130,210,105,'CT: A=y\nGS: A=(x−y) mod q\nB=root',GOLD)
    f.box(300,130,220,105,'Lượt 1 trên 4 lá\nT = A × B',GREEN)
    f.box(580,130,235,105,'Lượt 2 trên 4 lá\nm = T.low × q′\nchỉ giữ low',GREEN)
    f.box(875,130,250,105,'Lượt 3 trên 4 lá\nm × q',GREEN)
    f.wire([(240,182),(300,182)]);f.wire([(520,182),(580,182)]);f.wire([(815,182),(875,182)])
    f.ff(900,340,390,110,'u = T.high + (m q).high\n+ [T.low khác 0]\n33-bit register u32')
    f.wire([(1000,235),(1000,340)])
    f.wire([(410,235),(410,285),(1180,285),(1180,340)],'delay T.high / NZ',at=(745,275))
    f.ff(435,340,365,110,'Trừ q theo nửa + MUX\nu ≥ q ? u−q : u\n32-bit register r32r')
    f.wire([(900,395),(800,395)])
    f.box(35,340,305,110,'CT: x+t, x−t mod q\nGS: half(side), t\nMUX pairing packed16',GREEN)
    f.wire([(435,395),(340,395)])
    f.box(50,540,1235,105,'GS inverse: nhánh tổng chia 2 theo modulo q.\nRoot inverse đã chứa hệ số 1/2, nên nhánh nhân cũng được chuẩn hóa.\nq′ = −q⁻¹ mod R; modulus phải có root phù hợp với N và hmin.',GRAY,19)
    f.save()

if __name__=='__main__':
    for draw in (overview,frontend,bank_mux,full_adder,addsub,leaves,fft,ntt):draw()
    (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('Wrote',len(inventory),'SVG schematics to',OUT)
