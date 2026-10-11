"""Conservative CME PG39 text parser. Never silently infer option side or expiry.

Extracts only recognizable Euro FX option series, month and OI. CME layouts may change.
"""
import io
import re
from datetime import datetime
import pandas as pd
import pdfplumber

SERIES = re.compile(r'^\s*([A-Z0-9]{2,6})\s+OPT\s*$')
MONTH = re.compile(r'^\s*([A-Z]{3}\d{2})\s+([A-Z0-9]{2,6})\s+OPT\s*$')
ROW = re.compile(r'^\s*(\d{4,5})\s+(.+)$')
MONTHS = {x:i for i,x in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split(),1)}

def _num(token):
    t=token.replace(',','').replace('+','').replace('-','')
    if not t.isdigit(): return None
    return int(t)

def parse_pg39(data:bytes):
    if not data.startswith(b'%PDF'): raise ValueError('Nu este PDF.')
    records=[]; rejected=[]; series=None; month=None; report_date=None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages)>100: raise ValueError('PDF prea mare.')
        for page_idx,page in enumerate(pdf.pages,1):
            txt=page.extract_text(x_tolerance=2,y_tolerance=3) or ''
            if page_idx==1 and 'EURO FX' not in txt.upper(): raise ValueError('Nu este CME PG39 Euro FX.')
            if report_date is None:
                m=re.search(r'(Mon|Tue|Wed|Thu|Fri),\s+([A-Za-z]{3})\s+(\d{1,2}),\s+(20\d{2})',txt)
                if m:
                    report_date=datetime.strptime(' '.join(m.groups()[1:]),'%b %d %Y').date()
            for line in txt.splitlines():
                line=line.strip()
                sm=SERIES.match(line)
                if sm:
                    series=sm.group(1);month=None;continue
                mm=MONTH.match(line)
                if mm:
                    month,series=mm.groups();continue
                if line.startswith(('TOTAL','EURO FX FUT','EURO FX (','ADDITIONAL','EURO FX &')):
                    if line.startswith('TOTAL'): month=None
                    continue
                if not series or not month or not series.endswith('EU'): continue
                rm=ROW.match(line)
                if not rm: continue
                strike_raw,rest=rm.groups()
                # A valid row has a delta column formatted .000 through 1.000.
                toks=rest.split()
                matches=[i for i,t in enumerate(toks) if re.fullmatch(r'(?:0?\.\d{3}|1\.000)',t)]
                if len(matches)!=1:
                    rejected.append({'page':page_idx,'reason':'delta missing/ambiguous','raw':line[:180]});continue
                idx=matches[0]
                # Following delta: exercises, volume cleared, open interest, change.
                if len(toks)<idx+4:
                    rejected.append({'page':page_idx,'reason':'incomplete row','raw':line[:180]});continue
                oi=_num(toks[idx+3])
                if oi is None:
                    rejected.append({'page':page_idx,'reason':'OI missing/ambiguous','raw':line[:180]});continue
                strike=int(strike_raw)/10000
                if not (0.5<strike<2.5):continue
                if month[:3] not in MONTHS:continue
                records.append({'series':series,'contract_month':month,'strike':strike,'open_interest':oi,'delta_reported':float(toks[idx]),'page':page_idx,'raw_line':line[:220]})
    if not records: raise ValueError('Nu am găsit rânduri validate; CME poate fi schimbat formatul. Nu folosim date inventate.')
    df=pd.DataFrame(records)
    # Keep duplicate strikes in different products; duplicate exact raw rows across page boundaries discarded.
    df=df.drop_duplicates(subset=['series','contract_month','strike','raw_line','page'])
    return df,report_date,pd.DataFrame(rejected)
