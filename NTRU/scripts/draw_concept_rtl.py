"""Draw conceptual RTL schematics as editable SVG and matching PNG. No RTL changes."""
from pathlib import Path
from html import escape
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/figures'
INK='#20334a';GRAY='#586878';LINE='#324c65';BLUE='#17599d';TEAL='#087c74'
FONT=Path('C:/Windows/Fonts/arial.ttf')
BOLD=Path('C:/Windows/Fonts/arialbd.ttf')


class Figure:
    def __init__(self,w,h,title):
        self.w=w;self.h=h;self.parts=[]
        self.im=Image.new('RGB',(w*2,h*2),'white');self.d=ImageDraw.Draw(self.im)
        self.parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{escape(title)}</title><rect width="100%" height="100%" fill="white"/>')
    def line(self,points,color=LINE,width=2,dash=False,arrow=False):
        coords=' '.join(f'{x},{y}' for x,y in points)
        self.parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="8 6"' if dash else '')+'/>')
        for p,q in zip(points,points[1:]):
            if dash:
                import math
                dist=math.dist(p,q);steps=max(1,int(dist/14))
                for i in range(steps):
                    t0=i/steps;t1=min(1,t0+8/max(1,dist))
                    self.d.line([(2*(p[0]+t*(q[0]-p[0])),2*(p[1]+t*(q[1]-p[1]))) for t in (t0,t1)],fill=color,width=width*2)
            else:self.d.line([(2*p[0],2*p[1]),(2*q[0],2*q[1])],fill=color,width=width*2)
        if arrow:
            import math
            p,q=points[-2:];a=math.atan2(q[1]-p[1],q[0]-p[0]);s=10
            tri=[q,(q[0]-s*math.cos(a-.45),q[1]-s*math.sin(a-.45)),(q[0]-s*math.cos(a+.45),q[1]-s*math.sin(a+.45))]
            self.poly(tri,fill=color,stroke=color)
    def poly(self,points,fill='white',stroke=LINE,width=2):
        self.parts.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        self.d.polygon([(x*2,y*2) for x,y in points],fill=fill)
        self.d.line([(x*2,y*2) for x,y in points+[points[0]]],fill=stroke,width=width*2)
    def rect(self,x,y,w,h,fill='white',stroke=LINE,dash=False):
        if dash:
            self.line([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)],stroke,dash=True)
        else:self.poly([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],fill,stroke)
    def text(self,x,y,value,size=23,bold=False,color=INK,anchor='middle'):
        self.parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="central" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')
        font=ImageFont.truetype(str(BOLD if bold else FONT),size*2)
        self.d.text((x*2,y*2),value,font=font,fill=color,anchor={'middle':'mm','start':'lm','end':'rm'}[anchor])
    def labels(self,x,y,values,size=23,gap=31,bold=False,color=INK):
        for i,value in enumerate(values):self.text(x,y+i*gap,value,size,bold,color)
    def box(self,x,y,w,h,values,fill='white',color=INK,size=23):
        self.rect(x,y,w,h,fill)
        self.labels(x+w/2,y+h/2-(len(values)-1)*15,values,size,color=color)
    def reg(self,x,y,w,h,label):
        self.rect(x,y,w,h,'#f1f5f9');self.line([(x+9,y),(x+9,y+h)])
        self.poly([(x+w/2-7,y+h),(x+w/2,y+h-10),(x+w/2+7,y+h)])
        self.text(x+w/2,y+h/2,label,20,bold=True)
    def mux(self,x,y,w,h,label='MUX'):
        self.poly([(x,y),(x+w,y+22),(x+w,y+h-22),(x,y+h)],'#edf2f7')
        self.text(x+w*.46,y+h/2,label,18,bold=True)
    def save(self,name):
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/f'{name}.svg').write_text(''.join(self.parts)+'</svg>',encoding='utf8')
        self.im.save(OUT/f'{name}.png')


def core():
    f=Figure(1800,850,'Conceptual RTL of the shared FFT/NTT core')
    f.text(55,42,'SHARED RECONFIGURABLE FFT / NTT CORE',31,True,anchor='start')
    f.text(55,78,'Conceptual RTL  |  16 tiles shown as a baseline  |  not a synthesized netlist',21,color=GRAY,anchor='start')
    f.box(70,115,400,85,['CONFIG / CONTROL FSM','mode, width, q-profile, N, batch'],fill='#f1f5f9',size=22)
    f.box(565,115,245,85,['TWIDDLE ROM','FFT roots / NTT bundles'],size=21)
    f.reg(850,125,70,65,'Rtw')
    f.line([(810,158),(850,158)],arrow=True)
    f.line([(920,158),(975,158),(975,280)],width=3,arrow=True)
    f.text(1050,220,'twiddle bus',20)
    f.line([(470,158),(510,158),(510,235),(1605,235)],dash=True)
    f.line([(510,235),(400,235)],dash=True)
    f.line([(470,158),(565,158)],dash=True,arrow=True)
    for x,y in ((400,335),(690,280),(1280,290),(1605,345)):
        f.line([(x,235),(x,y)],dash=True,arrow=True)
    f.text(1320,216,'mode / width / valid / select',20,color=GRAY)
    f.line([(165,200),(165,320)],dash=True,arrow=True)
    f.text(165,282,'addr / en',19,color=GRAY)
    # Working memory, operand selection and input register.
    f.rect(70,320,250,250,'#f4f7fa')
    f.labels(195,356,['COEFFICIENT RAM','64 banks x 16 bit'],24,bold=True)
    for i in range(6):f.rect(94+i*34,420,25,61,'white')
    f.text(195,519,'A / B / output storage',20)
    f.text(195,548,'1R + 1W per bank',20,color=GRAY)
    f.mux(365,335,70,190)
    f.text(400,555,'Gather / pack',20)
    f.line([(320,430),(365,430)],width=3,arrow=True)
    f.reg(480,335,70,190,'Rin')
    f.line([(435,430),(480,430)],width=3,arrow=True)
    f.line([(550,430),(610,430)],width=3,arrow=True)
    # Physical shared array, same tiles across modes.
    f.rect(610,280,470,325,'#eef4fb')
    f.text(845,314,'FUSION / FISSION INTERCONNECT',23,True,color=BLUE)
    f.text(845,346,'16 shared tiles = 64 leaf multipliers',21)
    for row in range(4):
        for col in range(4):
            x=637+col*109;y=373+row*48
            f.rect(x,y,89,35,'white',BLUE)
            f.text(x+44.5,y+17.5,f'T{4*row+col}',21,True)
    f.text(845,584,'Tile pipeline and modular units: see detail below',19,color=GRAY)
    # FFT-specific exact fusion / complex arithmetic, NTT products already reduced in tiles.
    f.rect(1150,290,285,155,'#eef4fb')
    f.text(1292,317,'FFT POSTPROCESS',22,True,color=BLUE)
    f.labels(1292,354,['Limb fusion + exact rounding','Product registers for 3M','Complex butterfly / scaling'],21,gap=31)
    f.box(1150,490,285,95,['NTT PACK / REORDER','Montgomery + BF inside tiles'],fill='#edf8f5',color=TEAL,size=21)
    f.line([(1080,380),(1110,380),(1110,367),(1150,367)],width=3,arrow=True)
    f.line([(1080,490),(1110,490),(1110,538),(1150,538)],width=3,arrow=True)
    f.text(1112,425,'FFT',18,color=BLUE)
    f.text(1112,560,'NTT',18,color=TEAL)
    f.reg(1470,322,65,90,'Rf')
    f.reg(1470,493,65,90,'Rn')
    f.line([(1435,367),(1470,367)],width=3,arrow=True)
    f.line([(1435,538),(1470,538)],width=3,arrow=True)
    f.mux(1570,345,70,215)
    f.line([(1535,367),(1570,385)],width=3,arrow=True)
    f.line([(1535,538),(1570,520)],width=3,arrow=True)
    f.reg(1670,407,65,90,'Rout')
    f.line([(1640,452),(1670,452)],width=3,arrow=True)
    f.line([(1735,452),(1760,452),(1760,685),(195,685),(195,570)],width=3,arrow=True)
    f.text(1020,662,'WRITE-BACK BUS  |  output register / buffer  |  bank write mask',22)
    f.text(70,745,'Solid: data path     Dashed: control     Double-line box: clocked register',21,anchor='start',color=GRAY)
    f.text(70,785,'clk / ce / rst -> pipeline registers    |    FFT exact arithmetic    |    NTT canonical modular arithmetic',21,anchor='start',color=GRAY)
    f.save('shared-fft-ntt-rtl')


def tile():
    f=Figure(1900,720,'Conceptual four-leaf shared tile pipeline')
    f.text(55,42,'ONE SHARED TILE: 4 x 16-BIT MULTIPLIERS',31,True,anchor='start')
    f.text(55,80,'Two compute stages; FFT partial products or NTT one/two-layer butterflies',22,color=GRAY,anchor='start')
    f.rect(55,132,1790,450,dash=True)
    f.text(490,165,'COMPUTE STAGE 1',23,True)
    f.text(1160,165,'COMPUTE STAGE 2',23,True)
    f.labels(133,246,['FFT limbs /','NTT data','and roots'],20,gap=31)
    f.mux(200,215,65,265)
    f.reg(300,215,60,265,'R0')
    f.line([(65,350),(200,350)],width=3,arrow=True)
    f.line([(265,350),(300,350)],width=3,arrow=True)
    f.box(390,265,80,170,['SEL','/','GS'],fill='#edf2f7',size=20)
    for x,y,name in ((510,225,'M0'),(510,382,'M1'),(1120,225,'M2'),(1120,382,'M3')):
        f.rect(x,y,110,83,'white',BLUE)
        f.text(x+55,y+21,name,19,True,color=BLUE)
        f.text(x+55,y+52,'16 x 16',23,True)
    f.line([(360,350),(390,350)],width=3,arrow=True)
    f.line([(470,350),(490,350),(490,266),(510,266)],width=3,arrow=True)
    f.line([(490,350),(490,423),(510,423)],width=3,arrow=True)
    f.box(660,215,185,265,['MODE-SELECT','','FFT: raw products','+ limb operands','','NTT: Montgomery','+ modular add/sub'],fill='#f4f7fa',size=19)
    f.line([(620,266),(660,266)],width=3,arrow=True)
    f.line([(620,423),(660,423)],width=3,arrow=True)
    f.reg(890,215,70,265,'Rmid')
    f.line([(845,350),(890,350)],width=3,arrow=True)
    f.line([(360,450),(375,450),(375,508),(865,508),(865,450),(890,450)],width=2,arrow=True)
    f.text(680,497,'forward FFT operands',17,color=GRAY)
    f.box(990,265,90,170,['SEL','/','GS'],fill='#edf2f7',size=20)
    f.line([(960,350),(990,350)],width=3,arrow=True)
    f.line([(1080,350),(1098,350),(1098,266),(1120,266)],width=3,arrow=True)
    f.line([(1098,350),(1098,423),(1120,423)],width=3,arrow=True)
    f.box(1275,215,240,265,['MODE-SELECT LOGIC','','FFT: fuse raw 32 x 32','with retained products','','NTT: Montgomery','+ second-layer add/sub'],fill='#f4f7fa',size=21)
    f.line([(1230,266),(1275,266)],width=3,arrow=True)
    f.line([(1230,423),(1275,423)],width=3,arrow=True)
    # Retained FFT diagonals and bypass NTT first-layer data.
    f.line([(960,260),(970,260),(970,190),(1395,190),(1395,215)],width=2,arrow=True)
    f.text(1190,201,'retained products',17,color=GRAY)
    f.mux(1555,265,65,170)
    f.line([(1515,350),(1555,350)],width=3,arrow=True)
    f.reg(1660,265,70,170,'Rout')
    f.line([(1620,350),(1660,350)],width=3,arrow=True)
    f.line([(1730,350),(1820,350)],width=3,arrow=True)
    f.labels(1775,480,['FFT raw65','or NTT result'],20,gap=27)
    f.line([(960,455),(980,455),(980,505),(1535,505),(1535,410),(1555,410)],width=2,arrow=True)
    f.text(1185,494,'NTT one-layer bypass',18,color=TEAL)
    f.line([(233,132),(233,215)],dash=True,arrow=True)
    f.line([(1588,132),(1588,265)],dash=True,arrow=True)
    f.text(233,115,'mode / sign',20,color=GRAY)
    f.text(1588,115,'one / two layers',20,color=GRAY)
    f.text(950,552,'NTT paired mode keeps first-layer results in Rmid; it does not return them to coefficient RAM.',22,color=TEAL)
    f.text(55,630,'FFT: M0/M1 form diagonal limb products; M2/M3 form cross products. Wider FFT fusion happens across tiles.',21,anchor='start')
    f.text(55,674,'NTT: GS pre-subtraction / CT post-addition are mode-selected; the one-layer path bypasses stage-2 results.',21,anchor='start')
    f.save('shared-tile-rtl-detail')


if __name__=='__main__':
    from draw_revised_rtl import all_figures
    all_figures();print(OUT)
