import unittest,io
try:
 from reportlab.pdfgen import canvas
except ImportError:
 canvas=None
from parser import _num,parse_pg39
class ParserTest(unittest.TestCase):
 def test_oi(self):
  self.assertEqual(_num('1,522'),1522)
  self.assertEqual(_num('40'),40)
  self.assertIsNone(_num('UNCH'))
 @unittest.skipIf(canvas is None,"reportlab optional test dependency")
 def test_pdf_fixture(self):
  b=io.BytesIO();c=canvas.Canvas(b)
  for i,line in enumerate(['EURO FX & CME$INDEX OPTIONS','PG39 EURO FX OPTIONS Fri, Oct 09, 2026 PG39','3EU OPT','OCT26 3EU OPT','11250 ---- ---- ---- ---- 2.70- 10 .413 ---- 780 784 + 725 ---- ----','11300 ---- ---- ---- ---- 1.10- 6 .203 ---- 201 278 + 111 ---- ----']):
   c.drawString(35,780-i*22,line)
  c.save()
  df,dt,rejected=parse_pg39(b.getvalue())
  self.assertEqual(len(df),2)
  self.assertEqual(df.open_interest.tolist(),[784,278])
  self.assertEqual(df.strike.tolist(),[1.125,1.13])
  self.assertEqual(str(dt),'2026-10-09')
if __name__=='__main__':unittest.main()
