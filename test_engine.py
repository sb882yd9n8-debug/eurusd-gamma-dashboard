from datetime import date
import pandas as pd
from engine import validate,calculate,summarize

def test_basic():
    x=pd.DataFrame({'expiry':['2026-12-18','2026-12-18'],'strike':[1.16,1.16],'option_type':['CALL','PUT'],'open_interest':[100,200]})
    y=calculate(x,1.16,.09,date(2026,10,11))
    assert len(y)==2 and y.gamma.iloc[0]>0
    assert summarize(y).oi.iloc[0]==300

def test_invalid():
    try: validate(pd.DataFrame({'strike':[1.16]}));assert False
    except ValueError: pass

if __name__=='__main__': test_basic();test_invalid();print('PASS')
