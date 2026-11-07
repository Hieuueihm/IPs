"""Read-only layout/content audit plus contact sheets for human inspection."""
from pathlib import Path
import json, math
import pdfplumber
from PIL import Image, ImageOps, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
TMP=ROOT/'tmp/pdfs/flextransform_spec_0_2'
PDF=ROOT/'output/pdf/FlexTransform_Contract_0_2_Toan_hoc_den_RTL.pdf'
audit={'pages':[],'out_of_page_words':[],'body_overruns':[],'replacement_char_pages':[]}
with pdfplumber.open(PDF) as pdf:
    for i,page in enumerate(pdf.pages,1):
        text=page.extract_text() or ''
        audit['pages'].append({'page':i,'chars':len(text),'words':len(page.extract_words())})
        if '\ufffd' in text:audit['replacement_char_pages'].append(i)
        for w in page.extract_words():
            if w['x0'] < 0 or w['x1'] > page.width+0.5 or w['top'] < 0 or w['bottom']>page.height+0.5:
                audit['out_of_page_words'].append({'page':i,**w})
            # Only body region; header/footer intentionally outside body frame.
            if w['top']>45 and w['bottom']<page.height-40 and (w['x0']<46 or w['x1']>page.width-42):
                audit['body_overruns'].append({'page':i,**w})

digits=len(str(len(audit['pages'])))
files=[TMP/f'page-{i:0{digits}d}.png' for i in range(1,len(audit['pages'])+1)]
assert all(x.exists() for x in files)
for group in range(math.ceil(len(files)/12)):
    sheet=Image.new('RGB',(1000,1050),'#dce4eb');draw=ImageDraw.Draw(sheet)
    for j,path in enumerate(files[group*12:(group+1)*12]):
        im=Image.open(path).convert('RGB');im.thumbnail((232,310))
        x=10+(j%4)*248;y=28+(j//4)*345
        sheet.paste(im,(x,y));draw.text((x,y-17),f'Page {group*12+j+1}',fill='#142d45')
    sheet.save(TMP/f'contact-{group+1}.png')

report=HERE/'build_qa.json'
data=json.loads(report.read_text(encoding='utf-8'))
data['layout_audit']={k:v for k,v in audit.items() if k!='pages'}
data['rendered_pages']=len(files)
report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='pages'},ensure_ascii=False))
print('Low-content pages:',[x for x in audit['pages'] if x['chars']<220])
print('Rendered pages:',len(files))
