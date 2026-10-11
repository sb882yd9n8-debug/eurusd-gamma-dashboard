"""CME PDF retrieval and conservative, explicitly unverified candidate extraction.

PG39 layout can change. The app intentionally does NOT treat PDF candidates as trusted OI.
"""
import io
import re
import requests
import pdfplumber

URL='https://www.cmegroup.com/daily_bulletin/current/Section39_Euro_FX_And_Cme%24Index_Options.pdf'

def fetch_pdf():
    r=requests.get(URL,timeout=25,headers={'User-Agent':'Mozilla/5.0 (compatible; educational research dashboard)'})
    r.raise_for_status()
    if not r.content.startswith(b'%PDF'): raise ValueError('CME nu a returnat un PDF. Posibil acces restricționat.')
    if len(r.content)>15_000_000: raise ValueError('PDF prea mare')
    return r.content

def inspect_pdf(data):
    if not data.startswith(b'%PDF'): raise ValueError('Fișierul nu este PDF')
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        texts=[p.extract_text(layout=False) or '' for p in pdf.pages[:80]]
    all_text='\n'.join(texts)
    if 'EURO FX' not in all_text.upper():
        raise ValueError('Nu am identificat secțiunea EURO FX. Încarcă PG39.')
    # Extract raw lines for visual verification; PDF columns can shift, so no silent mapping to OI.
    candidates=[]
    for idx, page in enumerate(texts,1):
        for line in page.splitlines():
            if re.match(r'^\s*(?:0?[.,]?\d{4,6}|\d{4,6})\s+',line) and len(line.split())>=6:
                candidates.append({'page':idx,'raw_line':line[:450]})
    return all_text[:18000],candidates[:1500]
