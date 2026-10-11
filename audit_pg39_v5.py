"""Read-only diagnostic for CME PG39. Does NOT certify data for gamma calculations."""
import io,re,sys
from collections import defaultdict
import pdfplumber
import pandas as pd
SER=re.compile(r'^([A-Z0-9]{2,6}) OPT$')
MON=re.compile(r'^([A-Z]{3}\d{2}) ([A-Z0-9]{2,6}) OPT$')
STRIKE=re.compile(r'^(\d{4,5})\s')

def audit(data):
    observations=[]; totals=[]; series=month=None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_no,page in enumerate(pdf.pages[:18],1):
            section='A' if page_no<=9 else 'B'
            words=page.extract_words(x_tolerance=2,y_tolerance=3)
            for item in page.extract_text_lines():
                line=item['text'].strip()
                m=MON.fullmatch(line)
                if m: month,series=m.groups();continue
                m=SER.fullmatch(line)
                if m: series=m.group(1);continue  # continuation across pages
                if line.startswith('TOTAL'):
                    if series and month:
                        rowwords=[w for w in words if abs(w['top']-item['top'])<2.5]
                        candidates=[w for w in rowwords if 455<=w['x0']<=500 and re.fullmatch(r'\d+[+-]?',w['text'])]
                        total=int(candidates[0]['text'].rstrip('+-')) if len(candidates)==1 else None
                        totals.append(dict(section=section,series=series,month=month,page=page_no,official_oi=total,total_line=line))
                    month=None;continue
                m=STRIKE.match(line)
                if not m or not series or not month:continue
                strike=int(m.group(1))/10000
                if not .5<strike<2.5:continue
                rowwords=[w for w in words if abs(w['top']-item['top'])<2.5]
                candidates=[w for w in rowwords if 470<=w['x0']<=500 and re.fullmatch(r'\d+',w['text'])]
                oi=int(candidates[0]['text']) if len(candidates)==1 else None
                observations.append(dict(section=section,series=series,month=month,page=page_no,strike=strike,oi=oi,raw=line))
    rows=pd.DataFrame(observations); t=pd.DataFrame(totals)
    if rows.empty:return rows,t,pd.DataFrame()
    agg=rows.groupby(['section','series','month'],as_index=False).agg(extracted_oi=('oi','sum'),rows=('oi','size'),unreadable=('oi',lambda s:s.isna().sum()))
    if not t.empty:
        t=t.drop_duplicates(['section','series','month'],keep='last')
        agg=agg.merge(t[['section','series','month','official_oi']],how='left',on=['section','series','month'])
        agg['difference']=agg['extracted_oi']-agg['official_oi']
        agg['verified']=agg['official_oi'].notna() & (agg['difference']==0) & (agg['unreadable']==0)
    return rows,t,agg

if __name__=='__main__':
    with open(sys.argv[1],'rb') as f: rows,totals,summary=audit(f.read())
    summary.to_csv(sys.argv[2],index=False)
    print(summary.to_string(index=False))
