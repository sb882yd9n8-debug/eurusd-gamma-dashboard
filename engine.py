"""Analytics engine. All exposures are unsigned and use Black-76 gamma."""
from datetime import date
from math import exp, log, sqrt, pi
import pandas as pd
import numpy as np

REQUIRED = ['expiry','strike','option_type','open_interest']
MULTIPLIER = 125_000

def validate(frame):
    df = frame.copy()
    missing = set(REQUIRED)-set(df.columns)
    if missing: raise ValueError('Coloane lipsă: '+', '.join(sorted(missing)))
    df['expiry'] = pd.to_datetime(df['expiry'],errors='coerce').dt.date
    for col in ('strike','open_interest'):
        df[col] = pd.to_numeric(df[col],errors='coerce')
    df['option_type'] = df['option_type'].astype(str).str.upper().str.strip().replace({'C':'CALL','P':'PUT'})
    df = df.dropna(subset=['expiry','strike','open_interest'])
    df = df[(df.strike > 0.5)&(df.strike < 2.5)&(df.open_interest >= 0)&df.option_type.isin(['CALL','PUT'])]
    if df.empty: raise ValueError('Niciun rând valid. Verifică strike-ul (EUR/USD în format zecimal), tipul și scadența.')
    return df

def calculate(df, futures, iv, asof=None):
    if not (0.5 < futures < 2.5 and 0 < iv < 3): raise ValueError('Futures/IV invalide')
    asof = asof or date.today()
    d = validate(df)
    d['days_to_expiry'] = d.expiry.map(lambda x: (x-asof).days)
    d = d[d.days_to_expiry >= 0].copy()
    if d.empty: raise ValueError('Toate opțiunile din fișier sunt expirate.')
    # Intraday expiry times are not provided; 0DTE is floored at 1 calendar day to avoid false precision.
    d['time_years'] = d.days_to_expiry.clip(lower=1)/365.0
    sig_sqrt = iv*np.sqrt(d['time_years'])
    d1 = (np.log(futures/d.strike)+0.5*iv*iv*d['time_years'])/sig_sqrt
    d['gamma'] = np.exp(-0.5*d1*d1)/np.sqrt(2*pi)/(futures*sig_sqrt)
    d['gross_gamma_per_1pct_usd'] = d.gamma*d.open_interest*MULTIPLIER*(futures*0.01)**2
    return d

def summarize(df):
    s = df.groupby('strike',as_index=False).agg(gross_gamma=('gross_gamma_per_1pct_usd','sum'),oi=('open_interest','sum'))
    return s.sort_values('strike')
