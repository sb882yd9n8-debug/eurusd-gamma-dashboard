# EUR/USD Gamma Monitor AUTO v1.1

Streamlit dashboard pentru **extragerea automată a open interest (OI)** din CME Euro FX PG39 PDF și estimarea **gamma brute** în scenarii cu maturitate/IV/preț futures configurabile. Nu reprezintă dealer net gamma și nu oferă semnale LONG/SHORT.

## Rulare locală

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 0.0.0.0
```

Pe laptop deschide `http://localhost:8501`. Pe iPhone conectat la același Wi-Fi, în Safari deschide `http://IP_LAPTOP:8501` (exemplu `http://192.168.1.5:8501`). Lasă laptopul pornit și verifică firewall-ul. Nu expune portul public fără autentificare.

## Funcționare

1. Apasă **Actualizează din CME**. Aplicația încearcă să descarce raportul oficial `https://www.cmegroup.com/daily_bulletin/current/Section39_Euro_FX_And_Cme%24Index_Options.pdf`.
2. Dacă accesul este restricționat, descarcă manual PG39 de pe https://www.cmegroup.com/market-data/daily-bulletin.html și încarcă PDF-ul. Extracția OI rămâne automată.
3. Verifică data raportului, numărul rândurilor și secțiunea Audit. Filtrează seria/luna dorită.
4. Ajustează **futures 6E**, **IV** și **maturitatea scenariului**. Acestea sunt ipoteze manuale, NU date CME live și NU expirări contractuale verificate.
5. Descarcă CSV cu OI și gamma estimată.

## Limitări critice

- Parserul folosește structura PDF și validări conservatoare. CME poate schimba formatul, iar extragerea trebuie comparată periodic cu raportul original. Rândurile ambigue sunt excluse.
- PG39 poate combina tipuri diferite de opțiuni; nu pretindem clasificare CALL/PUT sau expirare exactă fără mapare verificată. Gamma Black-76 a CALL/PUT este identică la același strike, maturitate și IV, astfel că se poate calcula o **hartă brută de scenariu**.
- Raportul CME este zilnic, întârziat, nu feed intraday. Nu acoperă întreaga piață OTC.
- Gamma scenariului este calculată pe o maturitate aleasă (7–90 zile), nu pe scadența reală. Nu folosi această hartă pentru decizii automate de tranzacționare.
- Downloadul automat poate fi blocat de CME; uploadul manual este fallback.
- Pentru publicare pe Streamlit Community Cloud, urcă fișierele într-un repo GitHub privat și configurează accesul corespunzător. Hostul trebuie să poată accesa CME; altfel folosește upload PDF.

## Testare

```bash
python -m unittest discover -p 'test_*.py'
```
