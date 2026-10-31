"""Conceptual RTL v2: explicit operands, context, bank service and exact fusion.

Drawings only. Proposed buffering/batching is not newly implemented RTL.
"""
from draw_concept_rtl import Figure,OUT,BLUE,TEAL,GRAY,LINE,INK

PALE='#eef4fb';GREEN='#edf8f5';NEUTRAL='#f1f5f9';PURPLE='#77518b'


def title(f,heading,sub):
    f.text(55,42,heading,30,True,anchor='start')
    f.text(55,80,sub,21,color=GRAY,anchor='start')


def core_v2():
    f=Figure(1900,1100,'Revised conceptual RTL: shared FFT/NTT core')
    title(f,'SHARED FFT / NTT CORE - REVISED RTL CONCEPT',
          'Proposed block interfaces and buffering; existing arithmetic contract retained. No new RTL performance claim.')
    f.box(55,125,400,100,['COMMAND + LATCHED CONFIG','mode / W / q-profile / N / batch'],NEUTRAL,size=22)
    f.box(535,125,450,100,['ISSUE / RETIRE + STAGE BARRIER','Change config only when pipeline is empty'],NEUTRAL,size=22)
    f.line([(455,175),(535,175)],dash=True,arrow=True)
    f.box(1090,125,325,100,['TWIDDLE STORE','FFT: 1 complex root / cycle','NTT: 16 x 48-bit bundle banks'],size=20)
    f.box(1490,125,350,100,['PREFETCH + ROOT BUFFER','FFT roots for 16 / 4 / 1 lanes','ping-pong; root_ready gate'],size=20)
    f.line([(1415,175),(1490,175)],width=3,arrow=True)
    # Shared coefficient store and explicit port-limited bank service.
    f.rect(55,325,265,280,NEUTRAL)
    f.labels(187,360,['BANKED DATA RAM','64 x 16-bit banks'],24,bold=True)
    for b in range(6):f.rect(85+34*b,424,24,70)
    f.labels(187,535,['one read + one write','per bank / per cycle'],21,gap=30)
    f.box(375,325,270,120,['BANK SERVICE + GATHER','row requests / conflict rounds','write-mask + scatter'],size=21)
    f.line([(320,385),(375,385)],width=3,arrow=True)
    f.box(375,505,270,100,['PING-PONG BATCH BUFFER','operands + roots','2 contexts / lane mask'],NEUTRAL,size=19)
    f.line([(510,445),(510,505)],width=3,arrow=True)
    # Root data has a visible delivery path to the input buffer, not only a config arrow.
    f.line([(1665,225),(1665,275),(690,275),(690,475),(575,475),(575,505)],width=3,arrow=True)
    f.text(1155,257,'prepared roots; batch waits until operands AND roots are ready',20,color=GRAY)
    # FFT pre-processing and NTT logical packing are different input paths.
    f.box(720,340,280,110,['FFT OPERAND PREP','pre-adds for 3M + keep-data','see FFT detail'],PALE,color=BLUE,size=21)
    f.box(720,520,280,105,['NTT PACK + JOB PLACEMENT','same N / q-profile per batch','roots carried with coefficients'],GREEN,color=TEAL,size=20)
    f.line([(645,555),(680,555),(680,395),(720,395)],width=3,arrow=True)
    f.line([(680,555),(720,572)],width=3,arrow=True)
    f.mux(1040,375,65,235)
    f.line([(1000,395),(1040,420)],width=3,arrow=True)
    f.line([(1000,572),(1040,565)],width=3,arrow=True)
    f.reg(1140,420,65,145,'Rin')
    f.line([(1105,493),(1140,493)],width=3,arrow=True)
    # The physical multiplication island remains the center.
    f.rect(1245,340,330,295,PALE)
    f.labels(1410,372,['SHARED TILE ARRAY','16 tiles x 4 leaves'],24,bold=True,color=BLUE)
    for row in range(4):
        for col in range(4):
            x=1264+col*77;y=435+row*40
            f.rect(x,y,64,29,'white',BLUE);f.text(x+32,y+14.5,f'T{4*row+col}',18,True)
    f.text(1410,613,'sign / limb route / lane mask',19)
    f.line([(1205,493),(1245,493)],width=3,arrow=True)
    # Distinct post paths. Complex operand context bypasses the shared multiplier.
    f.box(1630,350,220,115,['FFT POST','exact limb fusion','3M collector + BF'],PALE,color=BLUE,size=21)
    f.box(1630,525,220,100,['NTT POST','result reorder / mask','reduction stays in tiles'],GREEN,color=TEAL,size=19)
    f.line([(1575,395),(1630,408)],width=3,arrow=True)
    f.line([(1575,575),(1630,575)],width=3,arrow=True)
    f.box(720,690,440,100,['CONTEXT / KEEP-DATA STORE','Kre, Kim, destination + job/stage','ctx + lane key / valid / lifetime'],NEUTRAL,size=20)
    f.line([(860,450),(860,480),(1015,480),(1015,660),(940,660),(940,690)],color=PURPLE,width=3,arrow=True)
    f.text(865,642,'keep operand',19,color=PURPLE)
    f.line([(1160,740),(1605,740),(1605,440),(1630,440)],color=PURPLE,width=3,arrow=True)
    f.text(1390,720,'lookup by context + lane',20,color=PURPLE)
    f.box(1235,855,615,100,['RESULT BUFFER / WRITE-BACK RETIRE','{data, destination, mask, job_id, stage_id, last}'],NEUTRAL,size=22)
    f.line([(1850,408),(1870,408),(1870,875),(1850,875)],width=3,arrow=True)
    f.line([(1850,575),(1885,575),(1885,925),(1850,925)],width=3,arrow=True)
    f.line([(1235,905),(350,905),(350,430),(375,430)],width=3,arrow=True)
    f.text(920,884,'scatter requests / data / bank enables',20)
    f.line([(375,415),(345,415),(345,655),(187,655),(187,605)],width=3,arrow=True)
    # Handshake/control lines visibly stop at block ports.
    f.line([(760,225),(760,295),(510,295),(510,325)],dash=True,arrow=True)
    f.line([(985,175),(1030,175),(1030,305),(1170,305),(1170,420)],dash=True,arrow=True)
    f.line([(1030,175),(1090,175)],dash=True,arrow=True)
    f.line([(1030,305),(1410,305),(1410,340)],dash=True,arrow=True)
    f.line([(375,350),(335,350),(335,965),(1500,965),(1500,955)],dash=True,arrow=True)
    f.text(850,945,'bank_write_commit acknowledgement',20,color=GRAY)
    f.line([(1850,950),(1880,950),(1880,1000),(30,1000),(30,100),(760,100),(760,125)],dash=True,arrow=True)
    f.text(1210,979,'stage_complete only after ALL writes retire; drain before config changes',20,color=GRAY)
    f.text(55,1040,'Context accompanies data: valid, ctx_id, job_id, stage_id, lane_mask, product_sel, dst_addr, last.',21,anchor='start')
    f.text(55,1075,'Each buffer uses valid/ready. Two batch contexts are proposed; internal pipeline depths remain open. clk / ce / rst are common.',20,color=GRAY,anchor='start')
    f.save('shared-fft-ntt-rtl')


def fft_v2():
    f=Figure(1900,1080,'Explicit complex FFT/IFFT datapath with keep operands and 3M context')
    title(f,'FFT / IFFT: EXPLICIT PRE-ADDS, KEEP PATH AND 3M COLLECTOR',
          'W = 32 / 64 / 128 per real component. Every wrap and rounding follows the selected fixed-point contract.')
    f.box(55,140,320,130,['INPUT CONTEXT','Ar, Ai, Br, Bi, wr, wi','op / ctx / lane / destinations'],NEUTRAL,size=22)
    f.box(445,140,610,130,['BUTTERFLY PREP / OPERAND SELECT','FFT: X = B, Y = w, K = A','IFFT: X = wrap(A-B), Y = conjugate(w), K = wrap(A+B)'],PALE,color=BLUE,size=21)
    f.line([(375,205),(445,205)],width=3,arrow=True)
    f.reg(1110,155,75,100,'Rxy')
    f.line([(1055,205),(1110,205)],width=3,arrow=True)
    f.box(1260,140,575,130,['KEEP-DATA / DESTINATION STORE','Kre, Kim, op, ctx_id, lane_id, dst0, dst1','Retain until corresponding product triplet retires'],NEUTRAL,size=21)
    f.line([(815,270),(815,305),(1548,305),(1548,270)],color=PURPLE,width=3,arrow=True)
    f.text(1165,291,'K + context',20,color=PURPLE)
    # Explicit product operands and wrap of the 3M sums.
    f.box(55,380,335,145,['REAL / IMAG OPERANDS','Xr, Xi, Yr, Yi','from Rxy'],PALE,color=BLUE,size=23)
    f.line([(1185,205),(1220,205),(1220,340),(220,340),(220,380)],width=3,arrow=True)
    f.box(445,385,345,135,['3M PRE-ADDERS','Sx = wrap_W(Xr + Xi)','Sy = wrap_W(Yr + Yi)'],PALE,color=BLUE,size=23)
    f.line([(390,450),(445,450)],width=3,arrow=True)
    f.box(850,365,370,195,['PRODUCT SELECT / ISSUE','phase 0: Xr x Yr','phase 1: Xi x Yi','phase 2: Sx x Sy','tag = {ctx, lane, phase}'],NEUTRAL,size=22)
    f.line([(790,450),(850,450)],width=3,arrow=True)
    f.line([(220,525),(220,595),(1035,595),(1035,560)],width=3,arrow=True)
    f.text(590,578,'Xr / Xi / Yr / Yi bypass pre-adders',20)
    f.box(1280,365,270,195,['SHARED MULTIPLIERS','limb/sign routing','+ exact fusion','+ per-product rounding'],PALE,color=BLUE,size=22)
    f.line([(1220,462),(1280,462)],width=3,arrow=True)
    f.box(1610,365,235,195,['3M COLLECTOR','Rp0 / Rp1 / Rp2','per ctx + lane','valid triplet'],NEUTRAL,size=23)
    f.line([(1550,462),(1610,462)],width=3,arrow=True)
    f.box(1280,670,565,130,['COMPLEX COMBINE','Tre = wrap_W(p0 - p1)','Tim = wrap_W(p2 - p0 - p1)'],PALE,color=BLUE,size=23)
    f.line([(1727,560),(1727,670)],width=3,arrow=True)
    f.box(535,670,600,130,['BUTTERFLY OUTPUT','FFT: U = wrap(K+T), V = wrap(K-T)','IFFT: U = K, V = T'],PALE,color=BLUE,size=23)
    f.line([(1280,735),(1135,735)],width=3,arrow=True)
    f.line([(1740,270),(1740,320),(1570,320),(1570,635),(835,635),(835,670)],color=PURPLE,width=3,arrow=True)
    f.text(1120,617,'K / op / destination context',20,color=PURPLE)
    f.box(55,670,325,130,['FINAL IFFT SCALE ONLY','wrap_W(x + bias) >>> s','s = logN - 1'],PALE,color=BLUE,size=21)
    f.line([(535,735),(380,735)],width=3,arrow=True)
    f.box(55,875,1790,85,['WRITE-BACK PACKET: results + addresses + masks + context; stage barrier waits for committed writes'],NEUTRAL,size=23)
    f.line([(217,800),(217,875)],width=3,arrow=True)
    f.text(55,1005,'Rounding is applied to EACH real product before the 3M combine. Pre-adds wrap at W; widening them changes this contract.',21,anchor='start')
    f.text(55,1043,'The scale block is bypassed for FFT and for non-final IFFT stages. Other polynomial kernels reuse parts of this datapath.',20,color=GRAY,anchor='start')
    f.save('fft-3m-rtl-detail')


def tile_v2():
    f=Figure(1900,1160,'Shared tile and explicit CT/GS operand-retention paths')
    title(f,'SHARED TILE: MULTIPLIER USE + EXPLICIT NTT OPERAND RETENTION',
          'One tile has four physical 16x16 multipliers. Below: one butterfly unit and the two-layer tile arrangement.')
    # One physical multiply unit shown with CT/GS paths and FFT raw bypass.
    f.box(55,140,265,135,['INPUT REGISTER R0','A, B, w, mode, q','valid / context'],NEUTRAL,size=22)
    f.box(380,140,300,135,['NTT PRE-ARITHMETIC','D = subq(A,B)','S = addq(A,B)'],GREEN,color=TEAL,size=22)
    f.line([(320,207),(380,207)],width=3,arrow=True)
    f.mux(745,150,70,235)
    f.labels(780,402,['CT: B / GS: D','FFT: selected limb'],18,gap=26)
    f.line([(680,207),(745,207)],width=3,arrow=True)
    f.line([(320,247),(345,247),(345,345),(745,345)],width=3,arrow=True)
    f.text(555,327,'B / FFT limb',20)
    f.box(880,165,165,90,['M: 16 x 16','sign selected'],PALE,color=BLUE,size=22)
    f.line([(815,267),(845,267),(845,210),(880,210)],width=3,arrow=True)
    f.line([(187,275),(187,475),(962,475),(962,255)],width=3,arrow=True)
    f.text(565,458,'w for NTT / other FFT limb',20)
    f.box(1110,150,275,120,['MONTGOMERY REDUCE','T = Mont(product,q)','NTT only'],GREEN,color=TEAL,size=22)
    f.line([(1045,210),(1110,210)],width=3,arrow=True)
    f.box(1450,135,395,155,['NTT OUTPUT COMBINE','CT: (addq(Ahold,T), subq(Ahold,T))','GS: (Shold, T)'],GREEN,color=TEAL,size=21)
    f.line([(1385,210),(1450,210)],width=3,arrow=True)
    f.box(380,535,680,95,['SIDE-DATA REGISTER / ELASTIC ALIGNMENT','Ahold = A for CT; Shold = S for GS; carry roots + context'],NEUTRAL,size=22)
    f.line([(530,275),(530,535)],color=PURPLE,width=3,arrow=True)
    f.line([(320,167),(345,167),(345,582),(380,582)],color=PURPLE,width=3,arrow=True)
    f.line([(1060,582),(1420,582),(1420,250),(1450,250)],color=PURPLE,width=3,arrow=True)
    f.text(1255,563,'Ahold / Shold',21,color=PURPLE)
    f.box(1450,380,395,95,['FFT RAW PRODUCT REGISTER','retain unrounded limb product'],PALE,color=BLUE,size=22)
    f.line([(1045,210),(1080,210),(1080,427),(1450,427)],width=3,arrow=True)
    f.text(1260,409,'raw bypass: no Montgomery',19,color=BLUE)
    # Array of four physical units; paired tile arithmetic and explicit root distribution.
    f.rect(55,710,1790,290,dash=True)
    f.box(95,770,350,135,['STAGE 0: M0 + M1','two butterfly units','CT roots: w0,w0 / GS: w1,w2'],GREEN,color=TEAL,size=21)
    f.reg(495,780,85,115,'Rmid')
    f.line([(445,837),(495,837)],width=3,arrow=True)
    f.box(655,770,350,135,['STAGE 1: M2 + M3','two butterfly units','CT roots: w1,w2 / GS: w0,w0'],GREEN,color=TEAL,size=21)
    f.box(595,790,45,95,['SW'],NEUTRAL,size=19)
    f.line([(580,837),(595,837)],width=3,arrow=True)
    f.line([(640,837),(655,837)],width=3,arrow=True)
    f.mux(1100,750,70,190)
    f.line([(1005,837),(1100,795)],width=3,arrow=True)
    f.line([(580,870),(615,870),(615,960),(1060,960),(1060,895),(1100,895)],width=3,arrow=True)
    f.text(825,940,'one-layer data bypass',20,color=TEAL)
    f.reg(1250,785,90,115,'Rout')
    f.line([(1170,845),(1250,845)],width=3,arrow=True)
    f.box(1420,770,370,135,['TILE OUTPUT','NTT one/two-layer coefficients','or FFT raw 32 x 32 result'],NEUTRAL,size=21)
    f.line([(1340,842),(1420,842)],width=3,arrow=True)
    f.text(950,737,'TWO-LAYER TILE / ROOT SELECTION / LATENCY-MATCHED BYPASS',23,True)
    f.text(55,1050,'NTT intermediate coefficients stay in Rmid. Roots, mode and context must advance/stall with their corresponding data.',21,anchor='start')
    f.text(55,1092,'FFT uses M0/M1 for diagonal and M2/M3 for cross limb products; raw products are fused without intermediate rounding.',21,anchor='start')
    f.text(55,1132,'SW = interstage lane permutation; w is Montgomery-encoded. Side paths use matched valid/ready; pipeline depths remain open.',20,color=GRAY,anchor='start')
    f.save('shared-tile-rtl-detail')


def fusion_v2():
    f=Figure(1900,1110,'Explicit FFT limb grouping, signed limbs, fusion and rounding')
    title(f,'FFT LIMB ROUTING / SIGN CONTROL / EXACT FUSION',
          'Real-product lanes, not complex-butterfly throughput. Four 16x16 leaves form one raw 32x32 tile product.')
    rows=[(32,16,1,135,PALE),(64,4,4,360,PALE),(128,1,16,585,PALE)]
    for w,lanes,tiles,y,fill in rows:
        f.text(60,y+18,f'W{w}',27,True,anchor='start',color=BLUE)
        f.text(60,y+52,f'{lanes} real lane'+('s' if lanes!=1 else ''),22,anchor='start')
        f.rect(270,y,850,165,fill)
        for t in range(16):
            x=290+t*50;f.rect(x,y+58,41,44,'white',BLUE);f.text(x+20.5,y+80,str(t),18,True)
        if tiles==1:
            f.text(695,y+28,'T0 | T1 | ... | T15: one raw 32x32 product per tile',22)
        elif tiles==4:
            for g in range(4):
                x=288+g*200;f.line([(x,y+113),(x,y+127),(x+194,y+127),(x+194,y+113)],color=BLUE)
            f.text(695,y+28,'4 groups of 4 tiles; 2x2 partial products per lane',22)
        else:
            f.line([(288,y+113),(288,y+127),(1082,y+127),(1082,y+113)],color=BLUE)
            f.text(695,y+28,'1 group of 16 tiles; 4x4 partial products',22)
        f.text(695,y+148,'tile index',17,color=GRAY)
        frac=w//2;acc=w+frac
        f.box(1195,y,650,165,[f'FUSE TO LOW {acc} BITS (MOD 2^{acc})',
            f'add 2^{frac-1}, then take bits [{acc-1}:{frac}]',
            f'output = wrap_{w}(floor((X*Y + 2^{frac-1}) / 2^{frac}))'],fill,size=23)
        f.line([(1120,y+82),(1195,y+82)],width=3,arrow=True)
    f.box(55,830,850,160,['LIMBS AND SIGN CONTROL','32-bit limbs: a_i, b_j; only each operand\'s most-significant limb is signed.',
        'Tile(i,j) returns the raw a_i*b_j product with a signed container.',
        'Within a tile, apply the same rule to the high 16-bit half.'],NEUTRAL,size=21)
    f.box(975,830,870,160,['FIXED-SHIFT FUSION','sum( raw_product(i,j) << (32*(i+j)) ), modulo the retained width.',
        'Terms whose shift is outside the retained width contribute zero.',
        'Round once per REAL product; the 3M collector receives p0,p1,p2.'],NEUTRAL,size=21)
    f.text(55,1040,'W128/Q64.64 follows the pinned R8 contract. W32/Q16.16 and W64/Q32.32 are separate contracts, not PQC-accuracy claims.',21,anchor='start')
    f.text(55,1080,'Grouping and sign tags are explicit design requirements; this drawing does not introduce a new RTL implementation.',20,color=GRAY,anchor='start')
    f.save('fft-fusion-sign-rtl-detail')


def all_figures():
    core_v2();fft_v2();tile_v2();fusion_v2()


if __name__=='__main__':
    all_figures();print(OUT)
