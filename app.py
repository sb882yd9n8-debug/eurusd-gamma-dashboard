from datetime import date, timedelta
import hashlib
import pandas as pd
import streamlit as st
import plotly.express as px
from parser import parse_pg39
from engine import calculate, summarize

st.set_page_config(page_title='EUR/USD Gamma Monitor · CME PDF', page_icon='📈', layout='wide')
st.title('EUR/USD · Gamma Monitor')
st.caption('CME PG39 · încărcare PDF manuală · Open Interest verificat prin totaluri · gamma BRUTĂ estimată, NU dealer net gamma')

with st.sidebar:
    st.header('Parametri scenariu')
    futures = st.number_input('Futures 6E USD/EUR (manual)', min_value=.5001, max_value=2.4999, value=1.1200, step=.0005, format='%.4f')
    iv_pct = st.number_input('IV anualizată % (manual)', min_value=.1, max_value=200., value=9., step=.5)
    tenor = st.selectbox('Maturitate ipotetică, zile', [7,14,30,60,90], index=2)
    st.warning('Prețul futures, IV și maturitatea sunt ipoteze. Nu sunt cotații live și nu reprezintă scadențele reale.')

st.subheader('1 · Încarcă PDF-ul oficial CME PG39')
st.markdown('[CME Daily Bulletin](https://www.cmegroup.com/daily_bulletin/current/Section39_Euro_FX_And_Cme%24Index_Options.pdf)')
upload = st.file_uploader('Alege PDF-ul salvat în Fișiere (iPhone)', type=['pdf'])
if upload is None:
    st.info('Încarcă PDF-ul oficial. Nu afișăm date simulate ca fiind reale.')
    st.stop()

payload = upload.getvalue()
digest = hashlib.sha256(payload).hexdigest()
if st.session_state.get('digest') != digest:
    try:
        with st.spinner('Extrag și verific totalurile CME...'):
            parsed, report_date, rejected = parse_pg39(payload)
        st.session_state['result'] = (parsed, report_date, rejected)
        st.session_state['digest'] = digest
    except Exception as exc:
        st.error(f'PDF neacceptat / date nevalidate: {exc}')
        st.stop()

parsed, report_date, rejected = st.session_state['result']
if report_date is None:
    st.error('Data raportului nu a putut fi identificată. Calculul este oprit.')
    st.stop()
if report_date > date.today():
    st.warning('Data raportului este în viitor față de data dispozitivului. Verifică documentul.')
elif (date.today()-report_date).days > 5:
    st.warning('Raport mai vechi de 5 zile: datele nu sunt actuale.')

st.info(f'Raport CME: **{report_date}** · **{len(parsed):,}** rânduri acceptate · **{len(rejected)}** grupuri excluse. Date întârziate, nu live.')
if not rejected.empty:
    st.error('Atenție: unele serii/scadențe au fost EXCLUSE deoarece nu au trecut reconcilierea OI. Totalurile și nivelurile de mai jos sunt PARȚIALE.')
    with st.expander('Grupe excluse — vezi motivul'):
        st.dataframe(rejected, use_container_width=True, hide_index=True)

series = sorted(parsed.series.unique())
months = sorted(parsed.contract_month.unique())
c1,c2 = st.columns(2)
with c1:
    chosen_series = st.multiselect('Serii CME', series, default=series)
with c2:
    chosen_months = st.multiselect('Luni contract', months, default=months)
selected = parsed[parsed.series.isin(chosen_series) & parsed.contract_month.isin(chosen_months)].copy()
if selected.empty:
    st.warning('Selecția nu conține rânduri validate.')
    st.stop()

st.subheader('2 · Hartă Open Interest (grupe reconciliate)')
oi = selected.groupby('strike', as_index=False).open_interest.sum()
peak_oi = oi.loc[oi.open_interest.idxmax()]
a,b,c = st.columns(3)
a.metric('Strike cu OI maxim', f'{peak_oi.strike:.4f}')
b.metric('OI acceptat (contracte)', f'{int(selected.open_interest.sum()):,}')
c.metric('Serii / luni', f'{selected.series.nunique()} / {selected.contract_month.nunique()}')
fig = px.bar(oi, x='strike', y='open_interest', labels={'strike':'Strike EUR/USD', 'open_interest':'Open Interest (contracte)'})
fig.add_vline(x=futures, line_dash='dash')
fig.update_layout(xaxis_tickformat='.4f', height=370, margin=dict(l=0,r=10,t=20,b=0))
st.plotly_chart(fig, use_container_width=True)
st.caption('OI extras din PDF, numai pentru grupe cu totaluri reconciliate. CALL/PUT nu este identificat. Grupele excluse pot modifica nivelurile maxime.')

st.subheader('3 · Gamma BRUTĂ — scenariu ipotetic')
st.warning(f'Scenariu cu maturitate uniformă {tenor} zile, IV uniformă {iv_pct:.1f}% și futures manual {futures:.4f}. Nu este dealer net GEX, Gamma Flip sau semnal de tranzacționare.')
scenario = selected[['strike','open_interest']].copy()
scenario['option_type'] = 'CALL'  # computational placeholder only; unsigned Black-76 gamma is identical for C/P
scenario['expiry'] = report_date + timedelta(days=tenor)
computed = calculate(scenario, futures, iv_pct/100, asof=report_date)
summary = summarize(computed)
peak = summary.loc[summary.gross_gamma.idxmax()]
a,b = st.columns(2)
a.metric('Strike cu gamma brută maximă', f'{peak.strike:.4f}')
b.metric('Gamma brută / mișcare 1% (model)', f'${summary.gross_gamma.sum():,.0f}')
fig2 = px.bar(summary, x='strike', y='gross_gamma', labels={'strike':'Strike EUR/USD','gross_gamma':'Gamma brută estimată (USD / mișcare 1%)'})
fig2.add_vline(x=futures, line_dash='dash')
fig2.update_layout(xaxis_tickformat='.4f', height=370, margin=dict(l=0,r=10,t=20,b=0))
st.plotly_chart(fig2, use_container_width=True)

st.download_button('Export OI validat (CSV)', selected.to_csv(index=False).encode(), 'cme_pg39_validated_oi.csv', 'text/csv')
st.download_button('Export gamma scenariu (CSV)', computed.to_csv(index=False).encode(), 'gamma_scenario.csv', 'text/csv')
with st.expander('Audit și limite'):
    st.dataframe(selected, use_container_width=True, hide_index=True)
    if not rejected.empty:
        st.dataframe(rejected, use_container_width=True, hide_index=True)
    st.markdown('Validarea verifică suma OI per serie/scadență, dar NU dovedește individual corectitudinea fiecărui rând. Nu deducem CALL/PUT, pozițiile dealerilor sau expirările exacte. OI nu este live. Gamma este doar un scenariu brut bazat pe Black-76, fără discounting și cu IV/maturitate uniforme. Verifică periodic datele față de PDF-ul CME și respectă termenii CME.')
