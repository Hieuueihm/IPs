"""Build a separate, reproducible implementation guide. Never edits locked sources."""
from pathlib import Path
import sys, json, hashlib, re, html, unicodedata, importlib.util
from collections import Counter

from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, NextPageTemplate, Table, TableStyle, Preformatted, KeepTogether, Flowable)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACK=ROOT/'rebuild/flextransform'
OUT=ROOT/'output/pdf'
TMP=ROOT/'tmp/pdfs/flextransform_spec_0_2'
OUT.mkdir(parents=True,exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
PDF=OUT/'FlexTransform_Contract_0_2_Toan_hoc_den_RTL.pdf'
MD=HERE/'SPEC_TOAN_HOC_DEN_RTL.md'
PORTS=json.loads((PACK/'microarchitecture/ports.json').read_text(encoding='utf-8'))['ports']
TIM=json.loads((PACK/'microarchitecture/timing.json').read_text(encoding='utf-8'))
FSM=json.loads((PACK/'microarchitecture/fsm.json').read_text(encoding='utf-8'))['machines']
spec=importlib.util.spec_from_file_location('guide_content', HERE/'content.py')
content=importlib.util.module_from_spec(spec); spec.loader.exec_module(content)
assert set(PORTS)==set(content.ORDER), 'Missing/extra module'

NAVY=colors.HexColor('#142D45'); BLUE=colors.HexColor('#176B92')
TEAL=colors.HexColor('#167D86'); GRAY=colors.HexColor('#526574')
LIGHT=colors.HexColor('#EDF3F7'); LINE=colors.HexColor('#D5E0E7')
FONTDIR=Path('C:/Windows/Fonts')
for name, file in [('VN','arial.ttf'),('VN-Bold','arialbd.ttf'),('VN-Italic','ariali.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONTDIR/file)))
pdfmetrics.registerFontFamily('VN',normal='VN',bold='VN-Bold',italic='VN-Italic',boldItalic='VN-Bold')
styles={
 'body':ParagraphStyle('body',fontName='VN',fontSize=10.1,leading=15.2,spaceAfter=6,textColor=NAVY),
 'small':ParagraphStyle('small',fontName='VN',fontSize=8.3,leading=11.5,spaceAfter=4,textColor=GRAY),
 'hash':ParagraphStyle('hash',fontName='Mono',fontSize=7.0,leading=9.4,spaceAfter=2,textColor=GRAY),
 'h1':ParagraphStyle('h1',fontName='VN-Bold',fontSize=20,leading=26,spaceAfter=15,textColor=NAVY,keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='VN-Bold',fontSize=12.2,leading=17,spaceBefore=12,spaceAfter=7,textColor=TEAL,keepWithNext=True),
 'h3':ParagraphStyle('h3',fontName='VN-Bold',fontSize=10.4,leading=15,spaceBefore=7,spaceAfter=4,textColor=NAVY,keepWithNext=True),
 'cell':ParagraphStyle('cell',fontName='VN',fontSize=8.6,leading=12,textColor=NAVY),
 'cellmono':ParagraphStyle('cellmono',fontName='Mono',fontSize=8.0,leading=11,textColor=NAVY),
 'th':ParagraphStyle('th',fontName='VN-Bold',fontSize=8.5,leading=11.5,textColor=colors.white),
 'code':ParagraphStyle('code',fontName='Mono',fontSize=8.1,leading=11.5,spaceBefore=6,spaceAfter=8,backColor=LIGHT,borderPadding=8),
}
W,H=A4; LEFT=48; RIGHT=45; TOP=58; BOT=47; CW=W-LEFT-RIGHT
story=[]; md=[]; QA={'chapters':[],'port_count':sum(map(len,PORTS.values()))}

def clean(t):
    return unicodedata.normalize('NFC',str(t)).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
def esc(t): return html.escape(clean(t))
def p(t,kind='body'):
    story.append(Paragraph(esc(t),styles[kind]));md.append(clean(t)+'\n')
def h(t,level=1):
    story.append(Paragraph(esc(t),styles['h'+str(level)]));md.append('#'*level+' '+clean(t)+'\n')
def bullets(items):
    for i,t in enumerate(items,1):
        story.append(Paragraph(f'<font color="#167D86">{i:02d}.</font> '+esc(t),styles['body']))
        md.append(f'{i}. '+clean(t))
    md.append('')
def code(t):
    lines=clean(t).splitlines()
    assert max(map(len,lines),default=0)<=94, 'Code too wide'
    story.append(Preformatted(clean(t),styles['code']));md.append('```text\n'+clean(t)+'\n```\n')
def table(headers,rows,widths=None,mono_col=None,compact=False):
    data=[[Paragraph(esc(x),styles['th']) for x in headers]]
    for row in rows:
        data.append([Paragraph(esc(x).replace('\n','<br/>'),styles['cellmono' if mono_col and j in mono_col else 'cell']) for j,x in enumerate(row)])
    tb=Table(data,colWidths=widths or [CW/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
       ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('LINEBELOW',(0,0),(-1,0),.5,TEAL),
       ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
       ('TOPPADDING',(0,0),(-1,-1),3 if compact else 5),('BOTTOMPADDING',(0,0),(-1,-1),3 if compact else 5)]))
    tb.spaceAfter=7
    story.append(tb)
    md.append('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |')
    for row in rows:md.append('| '+' | '.join(clean(x).replace('\n',' / ').replace('|','\\|') for x in row)+' |')
    md.append('')
def new():story.append(PageBreak())

class Diagram(Flowable):
    def __init__(self,kind):
        super().__init__();self.width=CW;self.height=175 if kind=='core' else 148;self.kind=kind
    def draw(self):
        c=self.canv
        def box(x,y,w,hh,title,sub):
            c.setFillColor(LIGHT);c.setStrokeColor(LINE);c.roundRect(x,y,w,hh,5,fill=1,stroke=1)
            c.setFillColor(NAVY);c.setFont('VN-Bold',8.4);c.drawCentredString(x+w/2,y+hh-17,title)
            c.setFont('VN',7.7);c.setFillColor(GRAY);c.drawCentredString(x+w/2,y+12,sub)
        def arrow(x,y,xx,yy):
            c.setStrokeColor(TEAL);c.setFillColor(TEAL);c.setLineWidth(1.1);c.line(x,y,xx,yy)
            if xx>=x and yy==y:
                q=c.beginPath();q.moveTo(xx,yy);q.lineTo(xx-5,yy+3);q.lineTo(xx-5,yy-3);q.close();c.drawPath(q,fill=1,stroke=0)
        if self.kind=='core':
            boxes=[(0,100,102,'AXI / frontend','snapshot + ack'),(124,100,113,'ft_core','FSM + context'),(260,100,108,'16 tile','shared arithmetic'),(391,100,110,'Data / root','32 + 16 bank')]
            for x,y,w,t,s in boxes:box(x,y,w,57,t,s)
            for x,xx in [(102,124),(237,260),(368,391)]:arrow(x,129,xx,129)
            box(124,12,244,54,'Stage / issue / program / writeback','read context và write context riêng')
            c.setStrokeColor(TEAL);c.line(180,66,180,100);c.line(314,66,314,100)
        else:
            for x,t,s in [(0,'Leaf array','4 DSP / raw33 / fused65'),(174,'Mont hoặc FFT','token / history / MAC'),(348,'C4 + C5 / AS','correction / combine')]:box(x,72,153,58,t,s)
            arrow(153,101,174,101);arrow(327,101,348,101)
            box(65,0,370,46,'Tile state: 6 RAM nhỏ + buffer / side credit','state và payload ở tại tile; controller dùng chung')
            c.setStrokeColor(TEAL);c.line(250,46,250,72)

class Doc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOT,
             title='FlexTransform - Toán học đến RTL - Contract 0.2',author='FlexTransform project',subject='Vietnamese RTL implementation guide')
        self.addPageTemplates(PageTemplate(id='normal',frames=[Frame(LEFT,BOT,CW,H-TOP-BOT,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.decorate))
        self.addPageTemplates(PageTemplate(id='wide',pagesize=(H,W),frames=[Frame(LEFT,BOT,H-LEFT-RIGHT,W-TOP-BOT,id='wide_body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.decorate))
    def decorate(self,c,doc):
        c.saveState()
        PW,PH=c._pagesize
        if doc.page>1:
            c.setStrokeColor(LINE);c.line(LEFT,PH-39,PW-RIGHT,PH-39)
            c.setFillColor(GRAY);c.setFont('VN',8)
            c.drawString(LEFT,PH-29,'FLEXTRANSFORM / TOÁN HỌC ĐẾN RTL')
            c.drawRightString(PW-RIGHT,PH-29,'Contract 0.2 · Guide 1.2 / Pin-level')
        c.setStrokeColor(LINE);c.line(LEFT,33,PW-RIGHT,33)
        c.setFillColor(GRAY);c.setFont('VN',7.6)
        c.drawString(LEFT,21,'07/11/2026  |  Tài liệu triển khai, không phải chứng nhận RTL/PPA')
        c.drawRightString(PW-RIGHT,21,str(doc.page));c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name=='h1':
            title=f.getPlainText();key='sec_'+hashlib.sha1(title.encode()).hexdigest()[:12]
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,0,False)
            self.notify('TOCEntry',(0,title,self.page,key))
            QA['chapters'].append({'title':title,'page':self.page})
        elif isinstance(f,Paragraph) and f.style.name=='schematic_title':
            title=f.getPlainText();key='sch_'+hashlib.sha1(title.encode()).hexdigest()[:12]
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,1,False)
            QA.setdefault('structural_pages',[]).append({'title':title,'page':self.page})

# Cover
story.append(Spacer(1,62))
p('FLEXTRANSFORM  /  ENGINEERING GUIDE','small')
story.append(Paragraph('TỪ TOÁN HỌC<br/>ĐẾN TRIỂN KHAI RTL',ParagraphStyle('cover',fontName='VN-Bold',fontSize=30,leading=39,textColor=NAVY,spaceAfter=19)))
p('FFT/IFFT đa precision và NTT/INTT đa modulus cho PQC')
story.append(Spacer(1,18));story.append(Diagram('tile'));story.append(Spacer(1,17))
table(['Hồ sơ','Giá trị'],[
 ['Mã tài liệu','FT-IG-002 / Phiên bản hướng dẫn 1.2 - pin, net và register'],['Nền tảng bắt buộc','Microarchitecture contract 0.2 / arithmetic compatibility 3.1'],
 ['Phạm vi','23 module SystemVerilog + ft_defs.svh; từ công thức đến datapath, port, clock, FSM và test'],
 ['Thiết bị mục tiêu','xc7z020clg400-2 / 16 tile / 64 DSP / 48 RAMB18'],
 ['Mục tiêu bản viết lại','Toàn hệ thống ≤35k LUT, 160 MHz; chưa phải số đo RTL mới'],
 ['Trạng thái','Hướng dẫn triển khai để review. Không sửa contract khóa hoặc baseline được chấp nhận.']],[125,CW-125])
p('Ngày phát hành: 07/11/2026. Đơn vị bit/word và mốc cạnh được định nghĩa tường minh trong chương 2. Những đoạn RTL rút gọn là mẫu tổ chức, không phải implementation đã mô phỏng.','small')

new();h('Mục lục')
toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc',fontName='VN',fontSize=9.3,leading=13.5,leftIndent=0,firstLineIndent=0,spaceBefore=4,textColor=NAVY)]
story.append(toc)

new();h('1. Phạm vi, thứ tự ưu tiên và cách đọc')
p('Mục tiêu là cho người viết RTL hiểu vì sao cần từng phép tính, phép tính đó được chia thành phần cứng nào và lúc nào dữ liệu được phép dùng. Tài liệu bao phủ cả tile, bộ nhớ, scheduler và host; không chỉ mô tả block diagram.')
h('1.1 Điều bắt buộc và lựa chọn triển khai',2)
bullets(['Quy định khóa: numerical semantics, port/width, latency cạnh, ownership và FSM ở spec08..11 và microarchitecture JSON0.2. Những nội dung này không được đổi ngầm để giảm LUT hoặc đạt timing.',
 'Gợi ý implementation: tên thanh ghi nội bộ, cách viết always_comb/always_ff, bitmap ownership hoặc ring đã kiểm. Có thể chọn cách khác nếu giữ đúng port/clock/semantics và kiểm tương đương.',
 'Nếu phát hiện mâu thuẫn: ưu tiên spec08..11 và JSON0.2 hơn phần draft spec01..07. Mở issue/version mới nếu cần đổi contract; không cập nhật hash để hợp thức hóa drift.',
 'Nguồn tham chiếu được ghi hash ở phụ lục. Bản hướng dẫn này là tài liệu dẫn giải riêng, không thay thế hoặc làm thay đổi LOCK_0_2.json.'])
h('1.2 Phạm vi PQC',2)
p('FN-DSA là ứng dụng kiểm chứng chính. FFT128 phải khớp R8 ở đường được chỉ định; native64 khớp NTRUGen. FFT32/64 thường là chức năng linh hoạt của IP, không tự động được phép thay precision của signer. Multi-modulus chứng minh kernel NTT dùng lại được, không đồng nghĩa có full RTL của ML-KEM/ML-DSA hoặc mọi scheme PQC.')
p('FFT N1024 theo API này có1024 hệ số thực và512 điểm phức. Không so trực tiếp với FFT1024 điểm phức mà bỏ qua convention này.')
h('1.3 Cách sử dụng khi tự viết',2)
bullets(['Đọc chương2 và3, rồi làm các module arithmetic theo thứ tự chương5..13. Mỗi module đọc theo: toán học → tổ chức RTL → port chính xác → clock → test.',
 'Viết unit test và probe latency trước khi ghép tile. Dùng oracle integer/C độc lập, không dùng cùng một sai sót của RTL để tính expected.',
 'Khi tile đủ mode đúng, ghép bộ nhớ/geometry và chạy NTT core trước, rồi FFT và host. PPA target chỉ được ghi thành kết quả sau synth/P&R đúng scope.'])

new();h('2. Hợp đồng số học và mốc cạnh')
h('2.1 Số nguyên và fixed-point',2)
code('wrapW(x) = x mod 2^W, diễn giải two\'s-complement W bit\nmulW(a,b) = wrapW((signed(a)*signed(b)+2^(F-1)) >>> F)\nF=W/2; W in {32,64,128}\nnative_mul64(a,b) = wrap64((signed64(a)*signed64(b)) >>> 32)\nnative_half64(v) = signed(wrap64(v+1)) >>> 1')
p('FFT cộng/trừ wrap, không saturation. Nhân thường round ties toward +infinity, không ties-to-even. Native không có rounding seed. Trong div2e và half, wrap xảy ra trước arithmetic shift; thay thứ tự có thể khác bit ở overflow.')
h('2.2 NTT và miền Montgomery',2)
code('R=2^w; w=32 scalar, w=16 packed\nq odd; 3<=q<2^(w-1); qi=-inverse(q,R) mod R\nT=a*root; m=low_w(T)*qi mod R; P=m*q\nU=high_w(T)+high_w(P)+(low_w(T)!=0)\nz=(U>=q) ? U-q : U')
p('Hệ số input/output là residue thường [0,q). Root chứa hệ số R nên Mont(a,root) trả hệ số về miền thường. Root inverse còn chứa1/2 theo convention INTT; không half nhánh nhân thêm lần nữa. q hợp lệ không bảo đảm tồn tại root cho mọi N: producer phải kiểm root order.')
p('Modular half của nhánh side INTT: half_q(s)=(s+(s lẻ ? q : 0)) >>1. Phép cộng là unsigned có thêm bit carry (33 bit scalar hoặc17 bit/lane packed), không wrap trước dịch và không dùng native_half signed. Hai quy tắc half này khác nhau.')
h('2.3 Một cách đếm clock duy nhất',2)
table(['Mốc','Ý nghĩa'],[['Launch sau L0','Operand/mux được cập nhật sau cạnh L0; leaf input FF nhận tại L1.'],['Raw sau L3 / fused sau L5','Consumer có FF nhận ở L4 / L6. Capture-edge-relative lần lượt +2/+4, không phải +3/+5.'],['Tile fire C0','Request đã được nhận khi req_valid AND req_ready tại cạnh C0.'],['Data read R','RAM read output sau R, route FF tại R+1, tile fire R+2.'],['Tile rsp sau E','Bank commit tại E+1; DONE chỉ sau commit và drain.']],[130,CW-130])
p('Dùng nonblocking cho state. Giá trị tạo sau cạnh không thể được FF khác lấy ở chính cạnh đó. Testbench nên drive ở negedge và observe sau posedge/NBA; assertion phải phân biệt giá trị trước và sau cạnh.')
h('2.4 Profile tài nguyên và chứng cứ',2)
p('Mục tiêu RTL mới là16 tile, mỗi tile4 leaf;64 DSP và48 RAMB18 gồm32 data +16 root. ≤35k LUT và160 MHz là target toàn hệ thống. Baseline cũ đạt34.277 LUT/160 MHz không phải chứng cứ của bản viết lại. Không gọi setup/hold sign-off chỉ từ WNS synth.')

new();h('3. Kiến trúc và ranh giới dùng chung')
story.append(Diagram('core'))
p('Mỗi tile tự giữ dữ liệu cục bộ; core chia sẻ program và geometry. Một context đang chạy dùng cùng mode/N/q/root/batch configuration. Không trộn hai modulus hoặc FFT/NTT song song trong cùng kernel.')
table(['Tài nguyên','FFT sử dụng','NTT sử dụng'],[
 ['4 leaf16/tile','Ghép fused32×32 rồi MAC đa limb theo thời gian','Scalar fused32×32 hoặc hai group packed2×16'],
 ['C0/C1','Butterfly sum/diff, carry/borrow limb','Sum/diff modulo q qua correction'],
 ['C2/C3','operand.re+im và root.re+im','sum−q và difference+q'],
 ['C4','p0+p1 để tạo imaginary 3M','Correction U−q, scalar hoặc hai lane'],
 ['Tile RAM','Side, operand/root/sums và partial','Side/tag/pairing; history ở mont'],
 ['Data/root banks','Fixed-point limbs và FFT roots','Residue scalar/packed và Montgomery roots']],[105,198,CW-303])
h('3.1 Phần giữ riêng có lý do',2)
bullets(['FFT MAC68/C5/native alignment phục vụ fixed-point và quan hệ limb; NTT feedback/history/NZ phục vụ reduction. Chia sẻ leaf và correction không có nghĩa ép mọi thanh ghi/adder vào một datapath duy nhất.',
 'C0/C1 hoạt động đồng thời; C2/C3 cũng cần hai kết quả riêng. Chia thời gian tất cả qua một adder sẽ đổi throughput, port và schedule.',
 'Wide FFT dùng nhiều lượt trong tile, không phải fusion giữa tile. Không gắn nhãn inter-tile PE fusion cho kiến trúc contract0.2.'])
h('3.2 ft_defs.svh',2)
p('Một header include-guard, chỉ macro/kiểu pack-unpack thống nhất cho width và opcode. Các giá trị chính: word32, leaf16/ext17/full34/raw33, raw bus132, fused65, MAC68, U34, C4=36, side42, tag8, meta10/7, read_meta30, write_ctx36, cfg_ctx128. Không đặt register, initial block hoặc hardware state trong header.')

new();h('4. Bản đồ module và lộ trình viết')
table(['Chặng','Module và kết quả cần có'],[
 ['A / arithmetic','defs → leaf → addsub → C4. Oracle đúng bit, latency đúng,4 DSP/tile.'],
 ['B / NTT tile','state + mont → ghép tile scalar rồi packed. Đúng group/history/side và reset.'],
 ['C / FFT tile','accum + combine + native → tile đủ32/64/128/native. Buffer và partial đúng liveness.'],
 ['D / core memory','cfg_decode, data/root, cg_addr/route → kiểm mapping và synchronous RAM latency.'],
 ['E / scheduler','issue, stage_ctrl, writeback, core. NTT có barrier trước; FFT program và overlap sau.'],
 ['F / host/system','host_map, normalizer, frontend, AXI; kernel/C regressions; synth/P&R toàn hệ thống.']],[100,CW-100])
p('Các chương module phía sau đi theo đường dữ liệu và ownership. Bảng cổng được lấy trực tiếp từ ports.json khóa0.2, không chép lại bằng tay. Input/output đều là bit pattern; signedness phải được diễn giải rõ bên trong phép toán.')
table(['Nhóm','Module'],[['Tile / 9 loại','leaf_array, addsub, reduce_or_sum, mont_pipe, tile_state, fft_accum, fft_combine, native_align, tile'],['Memory / geometry / 5 loại','cfg_decode, data_mem, root_mem, cg_addr, cg_route'],['Schedule / 5 loại','fft_program, issue_ctrl, stage_ctrl, writeback, core'],['Host / 4 loại','host_map, read_normalize, cmd_frontend, axil_top']],[160,CW-160])
p('23 module +1 header. Một module nhỏ vẫn cần kiểm chức năng; không cần tạo23 FSM. Các khối tổ hợp là cg_addr/cg_route/reduce_or_sum; leaf free-running không có reset/valid. FSM đã khóa chỉ có7 máy ở phụ lục.')

for n,m in enumerate(content.MODULES,5):
    new();h(f'{n}. {m["name"]}')
    module_start=len(story)-1
    p(m['purpose'])
    h('A. Bản chất toán học',2);bullets(m['math'])
    h('B. Phân rã thành RTL',2);bullets(m['rtl'])
    if m.get('code'):code(m['code'])
    if m.get('caution'):
        p('Điểm phải giữ: '+m['caution'],'small')
    ports_start=len(story)
    h('C. Cổng chính xác và cách nối',2)
    p('IN: đầu vào; OUT: đầu ra. Mọi độ rộng tính bằng bit.','small')
    plist=PORTS[m['name']]
    half=(len(plist)+1)//2
    pins=plist[:half];pouts=plist[half:]
    rows=[]
    for i in range(max(len(pins),len(pouts))):
        pi=pins[i] if i<len(pins) else None
        po=pouts[i] if i<len(pouts) else None
        def portlabel(x):return ('IN  ' if x['direction']=='input' else 'OUT ')+x['name'] if x else ''
        rows.append([portlabel(pi),str(pi['width']) if pi else '',portlabel(po),str(po['width']) if po else ''])
    table(['Cổng / hướng','Bit','Cổng / hướng','Bit'],rows,[(CW-64)/2,32,(CW-64)/2,32],mono_col={0,2},compact=True)
    h('D. Pipeline và thời điểm chốt',2);bullets(m['clock'])
    h('E. Điều kiện nghiệm thu unit',2);bullets(m['checks'])
    def height_of(flows):
        total=0
        for f in flows:
            _,hh=f.wrap(CW,100000)
            total+=hh+f.getSpaceBefore()+f.getSpaceAfter()
        return total
    # Keep compact modules on one page; separate narrative from interface
    # for longer modules so checklist/traceability never form orphan pages.
    if height_of(story[module_start:])>H-TOP-BOT-12:
        story.insert(ports_start,PageBreak())

# Exact arithmetic appendix
new();h('28. Phương trình bit để đối chiếu RTL')
p('Đây là các biểu thức bắt buộc về width/slice, diễn giải theo W32/H16. Đoạn mã trình bày theo tên intermediate; caller vẫn phải giữ register/valid đúng chương module.')
h('28.1 C0/C1 và thanh ghi trung gian',2)
code("S33={1'b0,a}+{1'b0,b}+{32'b0,ci};\nD34={1'b0,a[31:16],1'b1,a[15:0]}\n   +{1'b0,~b[31:16],split16,~b[15:0]}\n   +{33'b0,!bi};\nco_now=S33[32]; bo_now=!D34[33];\n// chốt S33->S, D34->D, q->Q, split16->PK, plain->PL")
h('28.2 C2 correction35 hoặc FFT sum',2)
code("A35=PL ? {2'b0,fa[31:16],1'b1,fa[15:0]}\n       : {1'b0,S[32:16],1'b1,S[15:0]};\nB35=PL ? {2'b0,fb[31:16],1'b0,fb[15:0]}\n       : {1'b0,~{1'b0,Q[31:16]},PK,~Q[15:0]};\nSQ35=A35+B35+{34'b0,(PL ? fci : 1'b1)};\nfs={SQ35[33],SQ35[32:17],SQ35[15:0]};")
h('28.3 C3 correction34 hoặc FFT sum',2)
code("A34=PL ? {1'b0,wa[31:16],1'b1,wa[15:0]}\n       : {1'b0,D[32:17],!PK,D[15:0]};\nB34=PL ? {1'b0,wb[31:16],1'b0,wb[15:0]}\n       : {1'b0,Q[31:16],1'b0,Q[15:0]};\nDQ34=A34+B34+{33'b0,(PL && wci)};\nws={DQ34[33],DQ34[32:17],DQ34[15:0]};")
h('28.4 Chọn kết quả addsub',2)
code("SNH=!SQ35[34]; SNL=PK ? !SQ35[16] : SNH;\nDNH=!D[33];    DNL=PK ? !D[16] : DNH;\nmod_s={SNH ? S[31:16] : SQ35[32:17],\n       SNL ? S[15:0]  : SQ35[15:0]};\nmod_d={DNH ? DQ34[32:17] : D[32:17],\n       DNL ? DQ34[15:0]  : D[15:0]};\ns=PL ? S[31:0] : mod_s;\nd=PL ? {D[32:17],D[15:0]} : mod_d;")
new();h('29. C4, bundle và phép tính mẫu')
h('29.1 Adder36 dùng chung',2)
code("// FFT\nA36={4'b0,fft_a}; B36={4'b0,fft_b}; CI=fft_ci;\n// Scalar NTT\nA36={3'b0,u_bus[32:0]}; B36=~{4'b0,q_word}; CI=1;\n// Packed NTT: Uhi=u_bus[33:17], Ulo=u_bus[16:0]\nA36={1'b0,Uhi,1'b1,Ulo};\nB36={1'b0,~{1'b0,q_word[31:16]},\n     1'b1,~{1'b0,q_word[15:0]}}; CI=1;\nR36=A36+B36+{35'b0,CI};\n// Scalar borrow R36[35]; packed borrow !R36[35]/!R36[17]\n// Packed candidates R36[33:18], R36[15:0]")
h('29.2 Bundle chuẩn',2)
table(['Bundle','Layout từ bit cao xuống thấp'],[
 ['side42','{reserved0, pairing, tag8, side32}'],['MAC meta10','{buffer3, product2, limb2, emit, column_last, first}'],['limb meta7','{buffer3, product2, limb2}'],['read_meta30','{mask16, tag8, near, swap, far, dummy, pairing, first}'],
 ['write_ctx36','{owner4, expected_last_tag8, last_stage, internal, write_far, dst_buf, mask16, stage4}'],
 ['cfg_ctx128','Xem bundle đầy đủ trích nguyên văn ở chương giao tiếp; không sắp lại field theo thứ tự struct C.']],[125,CW-125])
h('29.3 Ví dụ được tính lại bằng integer',2)
q=12289;R=1<<16;qi=(-pow(q,-1,R))%R;a=1000;w=3*R%q;T=a*w;mm=(T%R)*qi%R;P=mm*q;U=(T>>16)+(P>>16)+int(T%R!=0);z=U-q if U>=q else U
assert z==3000
table(['Đại lượng','Giá trị'],[['q / R / qi',f'{q} / {R} / {qi}'],['a / root=3R modq',f'{a} / {w}'],['T / T_hi / T_lo',f'{T} / {T>>16} / {T%R}'],['m / mq',f'{mm} / {P}'],['U / z',f'{U} / {z}'],['Oracle','a×3 mod12289=3000']],[180,CW-180])
p('Ví dụ kiểm miền: input a là residue thường; root ở Montgomery. Output trở lại residue thường. Đừng nhân thêm R vào a nếu API không yêu cầu.')

new();h('30. Lịch clock đầy đủ và liveness')
ntt_rows=[['C0','Tile fire; reserve side'],['C1','GS pre-addsub capture / CT align'],['C2','Operand/side write; launch T sau cạnh'],['C3','Leaf input T capture'],['C4','T product FF1'],['C5','T raw FF2'],['C6','T cat/cross hoặc packed align1'],['C7','T fused/aligned; launch m'],['C8','History stage0 T_hi/NZ; leaf m capture'],['C9','m product FF1'],['C10','m raw'],['C11','m cat/cross hoặc align1'],['C12','m fused/aligned; launch mq'],['C13','Leaf mq capture'],['C14','mq product FF1'],['C15','mq raw'],['C16','mq cat/cross hoặc align1'],['C17','mq fused/aligned; history stage9 sẵn'],['C18','U FF lấy old history9 và mq'],['C19','Correction + side/tag FF; release side'],['C20','GS response / CT post-addsub1'],['C21','GS bank commit / CT response'],['C22','CT bank commit']]
table(['Cạnh','Event của một packet'],ntt_rows,[65,CW-65])
h('30.1 FFT program và output',2)
p('Launch=H+pK+s; H7/9/13, K1/4/15 cho W32/64/128; native inverse64 H11. early=launch-1; raw=+3; fused=+5; MAC=+6; combine=+7. Những offset này là tương đối tile fire của butterfly, không là số chu kỳ từ host START.')
table(['Profile','Period','Free','Response offsets'],[[k,str(v['period']),str(v['release_edge']),', '.join(map(str,[o['rsp'] for o in v['outputs']]))] for k,v in TIM['fft'].items()],[150,50,45,CW-245])
h('30.2 Reserve / write / release / retire',2)
table(['Tài nguyên','Reserve','Write','Release','Retire'],[['NTT side16','C0','C2','C19','GS20 / CT21'],['FFT buffers8/4/2','beat0 C0','C2+b; native inverse +2','combine p2 cuối','rsp imaginary cuối'],['Context FIFO16','first_read-1','payload khi push','tail commit mọi active tile','kernel drain']],[100,85,110,105,CW-400])
p('Model đã kiểm peak: side reserved13/16, side written12/16, NTT outstanding14; FFT buffer6/8,3/4,2/2. Đây là peak trên traffic hợp lệ đã quét, không cho phép traffic tùy ý hoặc tự giảm depth. Những kết quả model không chứng minh RTL mới đã đúng.')
h('30.3 Quy tắc ownership FIFO',2)
table(['Before','Event','After / yêu cầu'],[['count0','push','Incoming bypass vào head'],['count1','pop+push','Incoming thay head cũ'],['count>=2','pop','old next thành head'],['count2','pop+push','next=incoming; bypass RAM cùng địa chỉ'],['count16','pop+push','Đọc head cũ trước overwrite, không bubble']],[85,95,CW-180])

new();h('31. FSM và giao tiếp chuẩn')
p('Các bảng dưới được lấy trực tiếp từ fsm.json. Guard xét theo thứ tự từ trên xuống; các global rule có ưu tiên trước state-local. Action dùng giá trị trước cạnh, state mới có hiệu lực sau cạnh. Tên C0/C1 của adder không phải tên state.')
for name,machine in FSM.items():
    h('FSM '+name+' / initial '+machine['initial'],2)
    rows=[]
    for rule in machine.get('global_rules',[]):rows.append(['ALL',rule['when'],rule['to'],', '.join(rule.get('actions',[])) or 'hold'])
    for state,rules in machine['states'].items():
        for rule in rules:rows.append([state,rule['when'],rule['to'],', '.join(rule.get('actions',[])) or 'hold'])
    table(['State','Guard','Next','Actions'],rows,[78,118,80,CW-276])

# Transcribe normative interface tables as references, not editable contract copies.
def append_md_source(path,subsections=None):
    lines=path.read_text(encoding='utf-8').splitlines(); para=[];codebuf=[];tbl=[];incode=False;active=subsections is None
    def flushpara():
        if para:p(' '.join(para));para.clear()
    def flushtable():
        if tbl:
            hdr=tbl[0];rows=[r for r in tbl[1:] if not all(re.fullmatch(r'[:\- ]+',c or '-') for c in r)]
            table(hdr,rows);tbl.clear()
    for line in lines:
        if line.startswith('## '):
            flushpara();flushtable();active=(subsections is None or any(line.startswith('## '+x) for x in subsections))
            if active:h(line[3:],2)
            continue
        if not active or line.startswith('# '):continue
        if line.startswith('```'):
            flushpara();flushtable()
            if incode:code('\n'.join(codebuf));codebuf=[]
            incode=not incode;continue
        if incode:codebuf.append(line);continue
        if line.startswith('|'):
            flushpara();tbl.append([x.strip().replace('`','') for x in line.strip().strip('|').split('|')]);continue
        flushtable()
        if not line.strip():flushpara()
        else:para.append(line.replace('**','').replace('`',''))
    flushpara();flushtable()

new();h('32. Register map, payload và status')
p('Phần này chép lại layout từ nguồn contract để tránh người triển khai phải đoán địa chỉ hoặc opcode. Các đường dẫn trong bản trích là tham chiếu trong bộ spec gốc.')
append_md_source(PACK/'spec/04_interfaces.md', ['2.','3.','4.','6.','7.'])
h('32.1 Bundle context chính xác',2)
append_md_source(PACK/'spec/07_block_interfaces.md',['1.'])
h('32.2 Ưu tiên sticky status',2)
append_md_source(PACK/'spec/10_locked_fsm.md',['Default pulse'])

new();h('33. Verification plan và tiêu chí hoàn thành')
table(['Lớp','Đầu vào / oracle','Gate'],[
 ['Unit arithmetic','Integer full precision, C fixed-point, vector biên','Đúng mọi bit và clock, không X khi valid'],
 ['State/control','Deque/ownership reference, reset injection','Không overflow, double-free, mất token hoặc stale context'],
 ['Tile đủ mode','Scalar/packed, FFT32/64/128/native CT/GS','Đúng data/tag/pairing/latency/rate'],
 ['Geometry/core','Planner, bank version scoreboard, root assets','Không alias/conflict/RAW, đúng natural order host'],
 ['Protocol/C','AXI adversarial +1026 kernel +74 live C calls','14 artifact byte-exact,4 chữ ký, không fallback'],
 ['Physical','Same part/tool/constraint/scope host+root','Synth resource; P&R setup/hold/pulse, CDC/DRC/endpoints']],[95,210,CW-305])
h('33.1 Assertion và trace tối thiểu',2)
bullets(['Mọi event trace có edge, module/tile, transaction ID, stage/buffer/group, tag, địa chỉ read/write và valid. Kiểm bit data và lifetime cùng lúc.',
 'assert occupancy<=depth; release chỉ vật sống; full+release xử lý đúng; không valid cũ sau reset; data giữ ổn định dưới AXI stall.',
 'Packed group selection T5/mq15, history10 có bubble; negative test history9 hoặc alias group phải fail.',
 'C4 packed guard và scalar polarity; half/wrap-before-shift; rounding ties; FIFO count2 pop+push; host gather nhiều phase phải có negative controls.',
 'Điều kiện hoàn thành một module: unit oracle PASS, latency probe PASS, reset PASS; với arithmetic/RAM thêm infer-resource check. Điều kiện hoàn thành project gồm ứng dụng C và full-system STA.'])
h('33.2 Ranh giới đo và claim',2)
p('Bản hướng dẫn này không tạo RTL mới và không chạy simulation/synth/P&R cho RTL viết lại. Các phép tính mẫu được kiểm bằng Python integer; integrity checker xác nhận nguồn contract/baseline không đổi. Mọi chứng cứ functional/PPA phải có source/tool/constraint hash riêng của implementation tương ứng.')
p('Mục tiêu 160 MHz/≤35k LUT không được dùng làm số thực nghiệm. Nếu chưa đo board, không ghi hardware-tested. Các kernel ngoài transform như sampler, keygen đầy đủ, basemul, CMUL/SPLIT/MERGE độc lập, DMA/DDR và inter-tile fusion nằm ngoài profile0.2.')

new();h('34. Nguồn, tính tái lập và checklist bàn giao')
p('Nguồn chính đều nằm trong workspace, không lấy các đoạn hướng dẫn chat làm normative. Hash dưới đây là SHA-256 của snapshot đã dùng để dựng PDF. Bộ LOCK_0_2.json gốc vẫn là nguồn khóa đầy đủ; bảng này chỉ là tập tham chiếu của hướng dẫn.')
sources=[PACK/'spec'/f for f in ['01_requirements.md','02_arithmetic.md','03_memory_schedule.md','04_interfaces.md','05_rtl_blocks.md','06_verification.md','07_block_interfaces.md','08_locked_ports.md','09_locked_cycles.md','10_locked_fsm.md','11_liveness_and_lock.md']]+[PACK/'microarchitecture'/f for f in ['ports.json','timing.json','fsm.json','LOCK_0_2.json']]
manifest=[]
for path in sources:
    digest=hashlib.sha256(path.read_bytes()).hexdigest();rel=path.relative_to(ROOT).as_posix();manifest.append({'path':rel,'sha256':digest})
    p(rel,'hash');p(digest,'hash')
h('34.1 Checklist trước khi bắt đầu code',2)
bullets(['Khóa đúng arithmetic compatibility3.1 và microarchitecture0.2; phần code mới ở vùng riêng; không copy default parameter sai từ RTL nghiên cứu cũ.',
 'Đọc đủ port và ownership của module mình viết; chọn state nội bộ nhưng không đổi boundary. Các ví dụ RTL ở PDF là mẫu, không phải netlist đã kiểm.',
 'Ghi rõ output nào tổ hợp, output nào sau FF và consumer chốt ở cạnh nào. Không thêm FF chỉ vì muốn mọi output cùng latency.',
 'Chuẩn bị oracle/testbench, unit source hash và resource report. Khi phát hiện cần đổi contract, tạo revision có planner/test tương ứng trước integration.'])
p('Các file kèm: SPEC_TOAN_HOC_DEN_RTL.md (bản đọc/sửa); content.py và build_pdf.py (nguồn dựng); source_manifest.json (hash tham chiếu); build_qa.json (kiểm PDF). Không file nào trong số này được thêm vào lock0.2 cũ.')

new();h('35. Sơ đồ structural và cổng logic chi tiết')
p('Phiên bản1.2 có58 bản vẽ vector A4 ngang cho đủ23 module: S01..S35 và các sheet B/C là cấu trúc tổng quan; D01..D18 mở sâu xuống pin D/Q/CLK, operand mux, token, history và register boundary. Hình là sơ đồ structural chức năng để viết RTL, không phải netlist công nghệ hoặc sơ đồ transistor sau tổng hợp.')
table(['Ký hiệu','Cách đọc'],[
 ['AND / OR / XOR / NOT','Cổng logic, dùng định nghĩa Boolean; thể hiện full-adder và compare/qualify.'],
 ['MUX2 / MUX4','Mux bus là lặp bit-slice với select chung; hình thang không phải register.'],
 ['FF + tam giác clk','Ranh giới register. Chỉ thêm khi contract cho phép. Tên L/C là cạnh theo spec09.'],
 ['DSP / RAM','Primitive arithmetic hoặc memory macro, không vẽ từng transistor. Cổng/latency vẫn phải giữ.'],
 ['Đường liên tục / tím đứt','Data/bus và control tương ứng. Bus width ghi trên cell/net hoặc theo tên port.'],
 ['Không có dot tại giao dây','Không tự coi hai dây cắt nhau là nối điện. Dây có cùng tên là cùng net.']],[150,CW-150])
p('Các cổng clk/rst/valid không lặp thành một cây dây xuyên mọi hình để tránh che datapath. FF có cùng clock trong profile một clock; reset chỉ áp vào control/valid theo chương module. Các cổng phụ không vẽ tại một sheet vẫn giữ nguyên bảng port đầy đủ ở chương5..27.')
p('CARRY4, DSP48E1 và LUTRAM là cách hiện thực mục tiêu, không phải số primitive đã đo của RTL mới. Những cell ký hiệu ADD3, mux/guard hoặc counter thể hiện quan hệ tổ hợp; mapper có thể tối ưu/gộp chúng. Không được dùng hình để tự đổi precision, số tầng pipeline hoặc giả định kết quả timing.')
sys.path.insert(0,str(HERE))
import structural
import structural_detail
structural_figures=structural.append_annex(story,md,HERE)
assert set(x['module'] for x in structural_figures if x['module']!='primitive')==set(PORTS)

story.append(NextPageTemplate('normal'));new()
h('36. Nối instance và thứ tự consume dữ liệu')
p('Bảng dưới là net binding theo vai trò instance. Dấu / trong tên a/b chỉ hai net song song độc lập, không ghép bit hoặc nối điện hai cổng output. Các instance đều cùng clock trong profile0.2; clk/rst không được tự lấy từ tín hiệu data hoặc FSM.')
import detail_contract as dc
h('36.1 Wiring trong một tile',2)
table(['Nguồn','Đích','Bit','Quy tắc'],dc.TILE_WIRES,[110,130,40,CW-280],compact=True)
new()
h('36.2 Wiring cấp core và host',2)
table(['Nguồn','Đích','Bit','Quy tắc'],dc.CORE_WIRES,[110,130,40,CW-280],compact=True)
h('36.3 Các chân không được nối nhầm',2)
bullets(['C4.result vào mont.corrected32; C4.fft_sum vào combine.c4_sum33. Đừng bỏ carry của tổng FFT chỉ vì result cũng có low32.',
 'mont.side_re là event trước C19 để state release slot; corr_valid mới xuất hiện sau C19 và không thay thế event đó.',
 'Leaf raw/fused cùng thời điểm thuộc hai lượt khác nhau. Packed không dùng fused; FFT không lấy raw lane như một real product32×32 hoàn chỉnh.',
 'out_valid của addsub xác nhận s/d từ intermediate FF; fs/ws và co_now/bo_now có latency khác, caller phải dùng qualifier riêng.',
 'write_ctx/out_tag tạo write row/route; read_ctx tạo read row/route. Nếu buộc hai context thành một khi overlap, dữ liệu đúng số học vẫn có thể ghi sai tầng.'])

new();h('37. Hồ sơ triển khai chi tiết từng module')
p('Mỗi hồ sơ có binding cho toàn bộ port, bảng D/width/enable/reset của register nội bộ tham chiếu và các bất biến phải assert. Tên register nội bộ là gợi ý có thể thay; numerical semantics, port và clock boundary vẫn theo contract khóa. Những lựa chọn encoding/ownership chưa khóa không được ghi thành chứng cứ RTL đã triển khai.')
table(['Hồ sơ','Sheet structural đối chiếu'],[[name,', '.join(s['code'] for s in structural.SHEETS if s['module']==name)] for name in content.ORDER],[240,CW-240],compact=True)
coverage=0
for index,name in enumerate(content.ORDER,1):
    c=dc.CARDS[name];names={x['name'] for x in PORTS[name]}
    assert names==set(c['port_semantics']),(name,names-set(c['port_semantics']),set(c['port_semantics'])-names)
    coverage+=len(names)
    new();h(f'37.{index:02d}. {name}')
    h('A. Binding và nghĩa của từng nhóm cổng',2)
    table(['Port / nhóm port','Nguồn, nơi dùng và điều kiện hợp lệ'],c['bindings'],[170,CW-170],mono_col={0},compact=True)
    h('B. Register, D và update/reset',2)
    table(['Register tham chiếu','Width','D / điều kiện update','Reset / thời điểm'],c['regs'],[118,88,160,CW-366],compact=True)
    rules_start=len(story)
    h('C. Bất biến để viết assertion',2);bullets(c['rules'])
    story[rules_start:]=[KeepTogether(story[rules_start:])]

new();h('38. Bảng mux và lịch token để tự viết RTL')
h('38.1 Các mux arithmetic không được bỏ sót',2)
table(['Mux','Điều kiện','D được chọn'],[
 ['Leaf sign extension','signed_flag=0 /1','0 / word[15] ở bit16'],
 ['C2/C3 owner','plain_q0 /1','NTT correction operands / live FFT aux operands'],
 ['C4 owner','FFT / scalar NTT / packed NTT','A36/B36/Cin đúng bảng chương29'],
 ['Mont A','T / m / mq','operand_q / low(T) / low(product_m)'],
 ['Mont B','T / m / mq','root_q / qi_word / q_word'],
 ['Mont high Cin','scalar / packed','Ulo[16] / NZhi'],
 ['MAC acc_in','first / !first&&prev_last / còn lại','seed / arithmetic_shift32(acc_q) / acc_q'],
 ['C5 A/B','product1 / product2','partial,p1 / p2,partial_sum'],
 ['C5 bi','limb0 / limb>0 product1 / product2','0 / borrow_real / borrow_imag'],
 ['Native half','native inverse64 / còn lại','wrap64(v+1) ASR1 / profile bypass'],
 ['Normalizer','normalize&&s>0 / còn lại','wrap-bias rồi ASR / bypass cùng latency'],
 ['AXI register D','bus reset / accepted write / hold','reset value / byte merge / old Q']],[110,165,CW-275])
h('38.2 Token Montgomery: xem giá trị trước cạnh',2)
table(['Cạnh','Q đang có trước cạnh','Capture tại cạnh','Q sau cạnh'],[
 ['C2','packet_valid/input X','Operand/root, v0, side write','Launch T(X)'],
 ['C7','old v4(X), group4','Select m nhìn trước','T return và launch m(X), v5(X)'],
 ['C8','T(X), old v5','H0={Thi,NZ}; leaf m input','H0(X)'],
 ['C12','old v9(X)','Select mq','m return và launch mq(X), v10(X)'],
 ['C17','old v14 và H8(X)','Leaf mq return; history shift','mq(X), H9(X), v15(X)'],
 ['C18','mq(X), OLD H9(X), old v15','U_q, VU','U(X), v16(X)'],
 ['C19','C4(U(X)), side_rd(head cũ), old VU','Correction/side/tag FF; release','corr_valid(X), head tiến'],
 ['C20 / C21','Correction/post token đã chốt','GS/CT response theo profile','Retire outstanding tại rsp cuối']],[46,145,155,CW-346])
p('v_age0 ở ví dụ chốt tại operand C2. Đây khác với mốc leaf capture C3. Khi viết testbench, score dữ liệu sau NBA, nhưng model consumer ở cạnh phải dùng giá trị cũ trước cạnh.')
checklist_start=len(story)
h('38.3 Checklist khi chuyển sơ đồ thành always_ff',2)
bullets(['Mỗi register chỉ có một owner always_ff. Mỗi combinational block gán đủ default; không tạo latch từ một nhánh mode bị bỏ sót.',
 'Literal có width; concat trước NOT; $signed rõ tại DSP/MAC/ASR. Carry/borrow và residue dùng unsigned có bit mở rộng.',
 'Phân biệt EN update với clock gate. Không làm gated clock bằng valid; profile một clock, payload có thể free-run dưới valid riêng.',
 'Bảng register mô tả implementation tham chiếu, không cho phép thêm stage. Nếu cần thêm FF vì timing, phải version pipeline/planner/test trước integration.',
 'Test ít nhất hai transaction liên tiếp có dữ liệu/tag/flags khác nhau; vector đơn lẻ không bắt lỗi lấy pins sống hoặc trộn stage.'])
story[checklist_start:]=[KeepTogether(story[checklist_start:])]

MD.write_text('\n'.join(md),encoding='utf-8')
(HERE/'source_manifest.json').write_text(json.dumps({'contract':'0.2','guide':'1.2','sources':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
doc=Doc(PDF);doc.multiBuild(story)
r=PdfReader(PDF)
texts=[page.extract_text() or '' for page in r.pages]
alltext='\n'.join(texts)
QA.update({'pdf':str(PDF),'pages':len(r.pages),'modules':len(content.MODULES),'port_count':sum(map(len,PORTS.values())),
 'all_modules_in_pdf':all(name in alltext for name in PORTS),'all_port_names_in_pdf':all(x['name'] in alltext for ports in PORTS.values() for x in ports),
 'page_chars':[len(x) for x in texts], 'pdf_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
 'structural_figures':len(structural_figures),'structural_module_coverage':23,
 'port_semantic_coverage':coverage,'implementation_cards':len(dc.CARDS),
 'math_example':{'q':q,'qi':qi,'R':R,'a':a,'root':w,'T':T,'m':mm,'P':P,'U':U,'z':z}})
missing={}
for fn in ['VN','VN-Bold','Mono']:
    face=pdfmetrics.getFont(fn).face
    bad=sorted({c for c in '\n'.join(md) if ord(c)>31 and ord(c) not in face.charWidths})
    missing[fn]=bad
QA['missing_glyphs']=missing
QA['chapters']=list({x['title']:x for x in QA['chapters']}.values())
QA['structural_pages']=list({x['title']:x for x in QA.get('structural_pages',[])}.values())
assert QA['all_modules_in_pdf'] and QA['all_port_names_in_pdf']
assert not any(missing.values()),missing
(HERE/'build_qa.json').write_text(json.dumps(QA,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:QA[k] for k in ['pages','modules','port_count','all_modules_in_pdf','all_port_names_in_pdf','missing_glyphs','pdf_sha256']},ensure_ascii=False))
print(PDF)
