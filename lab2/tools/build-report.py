"""Build the report from editable Markdown and existing figures, then render QA PNGs."""
from pathlib import Path
import csv
import html
import json
import re
from PIL import Image as PILImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, NextPageTemplate, KeepTogether
from pdf2image import convert_from_path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report'
SOURCE=OUT/'实验报告.md'
ASSETS=OUT/'assets'
QA=OUT/'qa'/'concise'
ASSETS.mkdir(exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Song','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Hei','C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFontFamily('Song',normal='Song',bold='Hei',italic='Song',boldItalic='Hei')
styles={
 'body':ParagraphStyle('Body',fontName='Song',fontSize=11,leading=17,spaceAfter=7,wordWrap='CJK',splitLongWords=True),
 'title':ParagraphStyle('Title',fontName='Hei',fontSize=20,leading=29,spaceAfter=12,alignment=1,textColor=colors.black,wordWrap='CJK'),
 'h1':ParagraphStyle('H1',fontName='Hei',fontSize=17,leading=25,spaceAfter=12,wordWrap='CJK',keepWithNext=True),
 'h2':ParagraphStyle('H2',fontName='Hei',fontSize=13,leading=21,spaceBefore=4,spaceAfter=8,wordWrap='CJK',keepWithNext=True),
 'caption':ParagraphStyle('Caption',fontName='Song',fontSize=10,leading=15,alignment=1,spaceBefore=4,spaceAfter=10,wordWrap='CJK'),
 'cell':ParagraphStyle('Cell',fontName='Song',fontSize=10,leading=15,wordWrap='CJK'),
 'smallcell':ParagraphStyle('SmallCell',fontName='Song',fontSize=9,leading=13,wordWrap='CJK'),
}

def markup(text):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    return text.replace('`','')

def expand_trace(text):
    if '<!-- traceability -->' not in text:return text
    names={'01-class':'C','02-components':'K','03-event-state':'SE','04-registration-state':'SR','05-register-sequence':'Q1','06-cancel-promote-sequence':'Q2','07-checkin-sequence':'Q3'}
    rows=list(csv.DictReader((ROOT/'planning/traceability.csv').open(encoding='utf-8-sig')))
    lines=['| 需求 | 模块 | UML | UI页面 |','| --- | --- | --- | --- |']
    for r in rows:
        if r['需求ID']=='REQ-027':continue
        figs=' '.join(names[x] for x in r['UML源文件'].split(','))
        ui=' '.join(x[1:] for x in r['UI页面'].split(','))
        lines.append(f"| {r['需求ID'][4:]} {r['需求名称']} | {r['模块']} | {figs} | {ui} |")
    return text.replace('<!-- traceability -->','\n'.join(lines))

def crop_ui(file):
    im=PILImage.open(file).convert('RGB')
    # Retain main work area; remove only prototype chrome and empty footer.
    if file.name.startswith('U01_'):
        box=(0,38,im.width,min(im.height,940))
    elif 'cancel-confirm' in file.name:
        # Modal white pixels are distinct from the dimmed backdrop.
        good=[]
        for y in range(120,min(im.height-20,880)):
            n=sum(1 for x in range(470,970) if all(c>247 for c in im.getpixel((x,y))))
            if n>350:good.append(y)
        box=(460,max(80,min(good)-18),980,min(im.height,max(good)+19)) if good else (224,116,im.width,im.height)
    else:
        footer=[]
        for y in range(260,im.height-20):
            n=sum(1 for x in range(260,im.width-36,3) if im.getpixel((x,y))==(220,229,222))
            if n>(im.width-296)/3*.78:footer.append(y)
        bottom=footer[-1]-8 if footer else im.height-45
        box=(244,128,im.width-16,max(350,bottom))
    cropped=im.crop(box)
    path=ASSETS/file.name
    cropped.save(path)
    return path

def table(lines,width):
    rows=[]
    for line in lines:
        parts=[x.strip() for x in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?',p) for p in parts):continue
        rows.append(parts)
    if len(rows[0])==2:ratios=[.24,.76]
    elif rows[0][0]=='需求':ratios=[.40,.11,.21,.28]
    elif len(rows[0])==4:ratios=[.12,.18,.31,.39]
    else:ratios=[.19,.40,.41]
    cellstyle=styles['smallcell'] if rows[0][0]=='需求' else styles['cell']
    cells=[[Paragraph(markup(c),cellstyle) for c in row] for row in rows]
    obj=Table(cells,colWidths=[width*r for r in ratios],repeatRows=1,hAlign='LEFT')
    commands=[('GRID',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef1')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]
    if rows[0][0]=='需求':commands += [('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]
    obj.setStyle(TableStyle(commands))
    return obj

def body_parts(block,width):
    lines=block.strip().splitlines();parts=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('<!--'):i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i]);i+=1
            parts += [table(rows,width),Spacer(1,10)];continue
        figure=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
        if figure:
            caption,rel=figure.groups();src=(OUT/rel).resolve()
            if 'ui/exports' in src.as_posix():src=crop_ui(src)
            img=Image(str(src));img._kind='report-figure'
            ratio=min(width/img.imageWidth,460/img.imageHeight)
            img.drawWidth=img.imageWidth*ratio;img.drawHeight=img.imageHeight*ratio;img.hAlign='CENTER'
            parts += [img,Paragraph(markup(caption),styles['caption'])];i+=1;continue
        if line.startswith('- '):parts.append(Paragraph('• '+markup(line[2:]),styles['body']));i+=1;continue
        if line.startswith('# '):parts.append(Paragraph(markup(line[2:]),styles['title']));i+=1;continue
        if line.startswith('## '):parts.append(Paragraph(markup(line[3:]),styles['h1']));i+=1;continue
        if line.startswith('### '):parts.append(Paragraph(markup(line[4:]),styles['h2']));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#','|','![','<!--','- ')):paragraph.append(lines[i].strip());i+=1
        parts.append(Paragraph(markup(''.join(paragraph)),styles['body']))
    return parts

def on_page(canvas,doc):
    canvas.saveState();w,h=canvas._pagesize
    canvas.setFont('Song',8.5);canvas.setFillColor(colors.HexColor('#666666'))
    canvas.drawCentredString(w/2,22,f'{doc.page}')
    canvas.restoreState()

def main():
    text=SOURCE.read_text(encoding='utf-8-sig')
    blocks=[b.strip() for b in text.split('<!-- pagebreak -->') if b.strip()]
    split=blocks
    pdf=OUT/'实验报告.pdf'
    doc=BaseDocTemplate(str(pdf),pagesize=A4,title='活动票务与报名系统软件设计与建模实验报告',author='张辰曦',subject='实验二 软件设计与建模',leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=40)
    templates=[]
    for name,size in [('portrait',A4),('landscape',landscape(A4))]:
        w,h=size
        frame=Frame(48,40,w-96,h-82,id=name,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        templates.append(PageTemplate(id=name,frames=[frame],onPage=on_page,pagesize=size))
    doc.addPageTemplates(templates)
    story=[];manifest=[]
    for index,block in enumerate(split):
        orientation='portrait'
        if index:story += [PageBreak()]
        w,h=A4;width=w-96;available=h-82
        parts=body_parts(block,width)
        images=[p for p in parts if isinstance(p,Image)]
        # Size figures using actual wrapped prose and table heights, not fixed row heights.
        if images:
            other=sum(p.wrap(width,available)[1]+p.getSpaceBefore()+p.getSpaceAfter() for p in parts if not isinstance(p,Image))
            budget=max(130,available-other-16)
            natural=[min(1.0,width/img.imageWidth)*img.imageHeight for img in images]
            shrink=min(1.0,budget/sum(natural))
            for img,natural_height in zip(images,natural):
                ratio=natural_height*shrink/img.imageHeight
                img.drawWidth=img.imageWidth*ratio;img.drawHeight=img.imageHeight*ratio
        for n,p in enumerate(parts):
            if isinstance(p,Image):
                caption=parts[n+1] if n+1<len(parts) else None
                story.append(KeepTogether([p,caption]) if isinstance(caption,Paragraph) else p)
            elif n and isinstance(parts[n-1],Image):continue
            else:story.append(p)
        manifest.append({'block':index+1,'orientation':orientation,'text':re.sub(r'!\[.*?\]\(.*?\)','',block)[:130],'figures':len(images)})
    doc.build(story)
    poppler='C:/Users/26545/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
    pages=convert_from_path(str(pdf),dpi=120,fmt='png',output_folder=str(QA),output_file='page',paths_only=True,poppler_path=poppler,thread_count=4)
    for i,p in enumerate(pages,1):Path(p).replace(QA/f'page-{i:02}.png')
    reader=PdfReader(str(pdf));texts=[p.extract_text() or '' for p in reader.pages]
    summary={'pages':len(reader.pages),'figures':sum(m['figures'] for m in manifest),'blocks':manifest,'page_text_lengths':[len(x) for x in texts],'missing_glyph_markers':any('\ufffd' in x for x in texts),'report_words_rough':sum(len(x) for x in texts)}
    (QA/'report-checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (QA/'extracted-text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{x}' for i,x in enumerate(texts)),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='blocks'},ensure_ascii=False))

if __name__=='__main__':main()
