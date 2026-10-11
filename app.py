from datetime import date
import pandas as pd
import streamlit as st
import plotly.express as px
from cme import fetch_pdf,URL
from parser import parse_pg39
from engine import calculate, summarize, validate

st.set_page_config(page_title='EUR/USD Gamma Monitor AUTO',page_icon='📈',layout='wide')
st.markdown('<style>.block-container{padding-top:1rem}div[data-testid="stMetric"]{background:#192738;padding:12px;border-radius:10px}</style>',unsafe_allow_html=True)
st.title('EUR/USD · Gamma Monitor AUTO')
st.caption('CME PG39 · Open interest extras automat · Gamma BRUTĂ estimată · NU dealer net gamma')
with st.sidebar:
    st.header('Parametri model')
    futures=st.number_input('Futures 6E USD/EUR (manual)',min_value=.5,max_value=2.5,value=1.12,step=.0005,format='%.4f')
    iv=st.number_input('IV anualizată % (manual)',min_value=.1,max_value=200.,value=9.,step=.5)
    tenor=st.selectbox('Scenariu maturitate (NU expirare verificată)',[7,14,30,60,90],index=2)
    st.warning('Futures, IV și maturitatea sunt ipoteze manuale. Nu reprezintă cotații CME live sau expirările contractelor.')

st.subheader('1 · Preluare automată CME')
st.markdown(f'[Sursă CME PG39]({URL}) · Daily Bulletin publicat cu întârziere')
if st.button('Actualizează din CME',type='primary'):
    try:
        with st.spinner('Descarc și extrag open interest...'):
            b=fetch_pdf(); parsed,report_date,rejected=parse_pg39(b)
            st.session_state['parsed']=(parsed,report_date,rejected)
            st.session_state['pdf_bytes']=b
        st.success('PDF preluat și interpretat. Verifică data raportului și rândurile excluse.')
    except Exception as e:st.error(f'Actualizarea nu a reușit: {e}. Încarcă manual PDF-ul oficial.')
upload=st.file_uploader('Alternativ: încarcă PDF CME PG39',type=['pdf'])
if upload is not None:
    try:
        b=upload.getvalue();parsed,report_date,rejected=parse_pg39(b)
        st.session_state['parsed']=(parsed,report_date,rejected);st.session_state['pdf_bytes']=b
    except Exception as e:st.error(f'PDF neacceptat: {e}')

if 'parsed' not in st.session_state:
    st.info('Apasă Actualizează din CME sau încarcă un PDF oficial. Nu afișăm date demonstrative drept date reale.')
    st.stop()
parsed,report_date,rejected=st.session_state['parsed']
st.info(f'Data raportului CME: **{report_date or "nedetectată"}** · {len(parsed)} rânduri extrase · {len(rejected)} rânduri excluse. Raportul nu este live.')
if report_date and (date.today()-report_date).days>5:st.warning('Raportul este mai vechi de 5 zile. Verifică dacă CME a publicat unul mai nou.')
series=sorted(parsed.series.unique());months=sorted(parsed.contract_month.unique())
c1,c2=st.columns(2)
with c1: chosen_series=st.multiselect('Serii CME',series,default=series)
with c2: chosen_months=st.multiselect('Luni contract',months,default=months)
selected=parsed[parsed.series.isin(chosen_series)&parsed.contract_month.isin(chosen_months)].copy()
if selected.empty:st.warning('Nu există date pentru selecție.');st.stop()

st.subheader('2 · Hartă open interest REAL, din PDF')
oi=selected.groupby('strike',as_index=False).open_interest.sum()
max_oi=oi.loc[oi.open_interest.idxmax()]
a,b,c=st.columns(3)
a.metric('Max OI strike',f'{max_oi.strike:.4f}')
b.metric('OI extras (contracte)',f'{int(selected.open_interest.sum()):,}')
c.metric('Serii / luni',f'{selected.series.nunique()} / {selected.contract_month.nunique()}')
fig=px.bar(oi,x='strike',y='open_interest',labels={'strike':'Strike EUR/USD','open_interest':'Open interest (contracte)'})
fig.add_vline(x=futures,line_dash='dash',annotation_text='Futures manual')
fig.update_layout(xaxis_tickformat='.4f',height=370,margin=dict(l=0,r=10,t=20,b=0))
st.plotly_chart(fig,use_container_width=True)
st.caption('Suma OI este din CME PG39. Tipul CALL/PUT și scadența exactă NU sunt deduse din rândurile ambigue ale PDF-ului.')

st.subheader('3 · Gamma brută estimată (scenariu)')
st.warning(f'Gamma calculată pentru maturitate ipotetică de {tenor} zile, IV {iv:.1f}% și futures {futures:.4f}. Nu este gamma exactă CME și nu arată direcția hedgingului.')
scenario=selected[['strike','open_interest']].copy()
scenario['option_type']='CALL' # gamma Black-76 identical for CALL and PUT at same F,K,T,IV
scenario['expiry']=(pd.Timestamp(date.today())+pd.Timedelta(days=tenor)).strftime('%Y-%m-%d')
computed=calculate(scenario,futures,iv/100,date.today());summary=summarize(computed)
peak=summary.loc[summary.gross_gamma.idxmax()]
a,b=st.columns(2)
a.metric('Max gamma brută (scenariu)',f'{peak.strike:.4f}')
b.metric('Gamma total / mișcare 1% (scenariu)',f'${summary.gross_gamma.sum():,.0f}')
fig2=px.bar(summary,x='strike',y='gross_gamma',labels={'strike':'Strike EUR/USD','gross_gamma':'Gamma brută estimată USD / mișcare 1%'})
fig2.add_vline(x=futures,line_dash='dash',annotation_text='Futures manual')
fig2.update_layout(xaxis_tickformat='.4f',height=370,margin=dict(l=0,r=10,t=20,b=0))
st.plotly_chart(fig2,use_container_width=True)
st.download_button('Export OI extras CSV',selected.to_csv(index=False).encode(),'cme_pg39_oi_extracted.csv','text/csv')
st.download_button('Export gamma scenariu CSV',computed.to_csv(index=False).encode(),'gamma_scenario.csv','text/csv')
with st.expander('Audit extracție și limitări'):
    st.dataframe(selected,use_container_width=True,hide_index=True)
    if not rejected.empty:st.dataframe(rejected.head(500),use_container_width=True,hide_index=True)
    if 'pdf_bytes' in st.session_state:st.download_button('Descarcă PDF sursă',st.session_state['pdf_bytes'],'cme_pg39_source.pdf','application/pdf')
    st.markdown('''**Atenție:** Unele serii din PG39 pot include tipuri diferite de opțiuni. Parserul extrage OI pe strike și lună, dar nu pretinde să clasifice CALL/PUT. Gamma Black-76 are aceeași valoare pentru CALL și PUT la același strike și aceiași parametri; eticheta tehnică CALL din calcul NU este clasificarea CME. Rândurile ambigue sunt excluse, nu completate. Nu deducem dealer net gamma, semnale LONG/SHORT sau orele exacte de expirare. Pentru producție, verifică periodic extragerea față de PDF și termenii de utilizare CME.''')
