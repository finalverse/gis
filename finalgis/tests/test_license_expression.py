import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/spatialdb_exchange.py'
spec=importlib.util.spec_from_file_location('exchange',p);exchange=importlib.util.module_from_spec(spec);spec.loader.exec_module(exchange)
class Licenses(unittest.TestCase):
 def test_nested_repetition_keeps_all_terms(self):
  self.assertEqual(exchange.conjunctive_license(['(CC-BY-4.0) AND (OGL-Canada-2.0 AND CC-BY-4.0)','MIT','(MIT AND (CC-BY-4.0))']),'CC-BY-4.0 AND MIT AND OGL-Canada-2.0')
 def test_other_operators_and_malformed_refuse(self):
  for text in ['MIT OR Apache-2.0','GPL-2.0-only WITH Classpath-exception-2.0','(MIT','MIT AND','()','MIT;curl','AND MIT','MIT Apache-2.0','']:
   with self.subTest(text=text):
    with self.assertRaises(ValueError):exchange.conjunctive_license([text])
 def test_bounds(self):
  for text in ['a'*129,'('*26+'MIT'+')'*26]:
   with self.assertRaises(ValueError):exchange.conjunctive_license([text])
if __name__=='__main__':unittest.main()
