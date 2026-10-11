"""Black-76 gamma scenario. Unsigned gross exposure; NOT dealer net gamma."""
from datetime import date
from math import pi
import numpy as np
import pandas as pd

MULTIPLIER = 125_000
REQUIRED = {'expiry', 'strike', 'option_type', 'open_interest'}

def validate(frame):
    df = frame.copy()
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError('Coloane lipsă: ' + ', '.join(sorted(missing)))
    df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce').dt.date
    for col in ('strike', 'open_interest'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['option_type'] = df['option_type'].astype(str).str.upper().str.strip().replace({'C':'CALL','P':'PUT'})
    df = df.dropna(subset=['expiry','strike','open_interest'])
    df = df[(df.strike > .5) & (df.strike < 2.5) & (df.open_interest >= 0) & df.option_type.isin(['CALL','PUT'])].copy()
    if df.empty:
        raise ValueError('Niciun rând valid pentru calcul.')
    return df

def calculate(df, futures, iv, asof=None):
    if not (.5 < futures < 2.5 and 0 < iv < 3):
        raise ValueError('Futures/IV invalide.')
    asof = asof or date.today()
    d = validate(df)
    d['days_to_expiry'] = d.expiry.map(lambda x: (x-asof).days)
    d = d[d.days_to_expiry >= 0].copy()
    if d.empty:
        raise ValueError('Toate opțiunile sunt expirate.')
    d['time_years'] = d.days_to_expiry.clip(lower=1)/365.0
    sigma_t = iv * np.sqrt(d.time_years)
    d1 = (np.log(futures/d.strike) + .5*iv*iv*d.time_years)/sigma_t
    d['gamma'] = np.exp(-.5*d1*d1)/np.sqrt(2*pi)/(futures*sigma_t)
    d['gross_gamma_per_1pct_usd'] = d.gamma*d.open_interest*MULTIPLIER*(futures*.01)**2
    return d

def summarize(df):
    return df.groupby('strike',as_index=False).agg(gross_gamma=('gross_gamma_per_1pct_usd','sum'),oi=('open_interest','sum')).sort_values('strike')
