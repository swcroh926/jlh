import csv,json,tempfile,unittest,logging
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
import collector as c
N='''<input name="page" value="1"><table><tbody onclick="fn_moveBbsNttDetail('42', '')"><tr><td>1</td><td>2026</td><td>물리</td><td>(지도논문) A &amp; B <span>연구</span></td><td>등급 외</td><td>이름</td><td>이름</td></tr></tbody></table>'''
S='''<input name="pageIndex" value="1"><table><tr><td>1</td><td>특상</td><td>생물</td><td><a href="javascript:fncDetailView('99');">식물 성장 연구</a></td><td>이름</td><td>학교</td><td>2026</td><td>학생</td><td>3</td></tr></table>'''
class Tests(unittest.TestCase):
 def test_national(self):
  r=c.extract(N,'national',1)[0];self.assertEqual(r['title'],'(지도논문) A & B 연구');self.assertEqual(r['record_type'],'지도논문');self.assertNotIn('이름',json.dumps(r,ensure_ascii=False))
 def test_raw_national_without_tr(self):
  raw=N.replace('<tr>','').replace('</tr>','')
  original=c.extract(raw,'national',1)
  repaired=c.extract(N,'national',1)
  for rows in (original,repaired):
   for row in rows:row.pop('collected_at')
  self.assertEqual(original,repaired)
 def test_multiple_raw_national_rows(self):
  raw=N.replace('<tr>','').replace('</tr>','')
  text=raw+raw.replace("'42'","'43'")
  self.assertEqual([r['id'] for r in c.extract(text,'national',1)],['42','43'])
 def test_national_student_classification_preserves_original(self):
  row=c.extract(N.replace('(지도논문) ',''),'national',1)[0]
  self.assertEqual(row['record_type'],'학생');self.assertEqual(row['raw_record_type'],'미분류')
  self.assertIn('사용자 확인',row['classification_basis'])
 def test_seoul(self):
  r=c.extract(S,'seoul',1)[0];self.assertEqual((r['id'],r['year'],r['record_type']),('99','2026','학생'));self.assertIn('board_seq=99',r['url'])
 def test_bad_pages(self):
  for text,page in [(N,2),('<html>Denied</html>',1)]:
   with self.assertRaises(ValueError):c.extract(text,'national',page)
 def test_bad_columns(self):
  with self.assertRaises(ValueError):c.extract(S.replace('<td>3</td>',''),'seoul',1)
 def test_requests(self):
  n=c.make_request('national',2);s=c.make_request('seoul',3);self.assertTrue(n.full_url.endswith('?page=2'));self.assertEqual(s.get_method(),'POST');self.assertEqual(parse_qs(s.data.decode())['pageIndex'],['3'])
 def test_duplicate(self):
  state={'records':{},'pages':{}};rows=c.extract(N,'national',1);c.remember(state,'national',1,rows);c.remember(state,'national',1,rows);self.assertEqual(len(state['records']),1)
  with self.assertRaises(ValueError):c.remember(state,'national',2,rows)
  self.assertNotIn('national:2',state['pages'])
 def test_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);state=c.load_state(p);rows=c.extract(S,'seoul',1);rows[0]['title']='=1+1';c.remember(state,'seoul',1,rows);c.export(p,state);self.assertEqual(c.load_state(p),state);self.assertEqual(json.loads((p/'awards.json').read_text())[0]['title'],'=1+1')
   with (p/'awards.csv').open(encoding='utf-8-sig',newline='') as f:self.assertEqual(list(csv.DictReader(f))[0]['title'],"'=1+1")
 def test_corrupt(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'state.json').write_text('broken')
   with self.assertRaises(ValueError):c.load_state(p)
   self.assertEqual((p/'state.json').read_text(),'broken')
 def test_robots(self):
  with patch.object(c.Client,'read',return_value='User-agent: *\nDisallow: /'):
   with self.assertRaises(ValueError):c.Client().check_robots('seoul')
 def test_resume_failure(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);state=c.load_state(p);c.remember(state,'national',1,c.extract(N,'national',1));c.export(p,state)
   with patch('sys.argv',['collector.py','--site','national','--pages','3','--output',d]),patch.object(c.Client,'check_robots'),patch.object(c.Client,'read',side_effect=OSError('timeout')) as read:
    self.assertEqual(c.main(),1);self.assertEqual(read.call_count,1);self.assertTrue(read.call_args.args[0].full_url.endswith('?page=2'))
   self.assertEqual(list(c.load_state(p)['pages']),['national:1'])
   logging.shutdown()
   logging.getLogger().handlers.clear()
 def test_failed_html_saved_without_completion(self):
  with tempfile.TemporaryDirectory() as d:
   with patch('sys.argv',['collector.py','--site','national','--pages','1','--output',d]),patch.object(c.Client,'check_robots'),patch.object(c.Client,'read',return_value='<html>Unexpected response</html>'):
    self.assertEqual(c.main(),1)
   p=Path(d);files=list((p/'diagnostics').glob('national-page-1-*.html'))
   self.assertEqual(len(files),1);self.assertEqual(files[0].read_text(),'<html>Unexpected response</html>')
   self.assertEqual(c.load_state(p)['pages'],{})
   logging.shutdown();logging.getLogger().handlers.clear()
 def test_page_counts(self):
  self.assertEqual(c.page_info(N+'전체 <span>21,313</span>건, 현재 페이지 <span>1 / 2132</span>','national')['total_pages'],2132)
  self.assertEqual(c.page_info(S+'총 <strong>733</strong> 건 <strong>1</strong> / 74','seoul')['total_records'],733)
  with self.assertRaises(ValueError):c.page_info(S,'seoul')
 def test_full_run_and_resume(self):
  first=S+'총 2 건 1 / 2'
  second=S.replace('value="1"','value="2"').replace("'99'","'100'")+'총 2 건 2 / 2'
  with tempfile.TemporaryDirectory() as d:
   argv=['collector.py','--site','seoul','--all','--output',d]
   with patch('sys.argv',argv),patch.object(c.Client,'check_robots'),patch.object(c.Client,'read',side_effect=[first,second]) as read:
    self.assertEqual(c.main(),0);self.assertEqual(read.call_count,2)
   logging.shutdown();logging.getLogger().handlers.clear()
   with patch('sys.argv',argv),patch.object(c.Client,'check_robots'),patch.object(c.Client,'read',return_value=first) as read:
    self.assertEqual(c.main(),0);self.assertEqual(read.call_count,1)
   logging.shutdown();logging.getLogger().handlers.clear()
   self.assertEqual(len(c.load_state(Path(d))['records']),2)
 def test_changed_first_page_stops_resume(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);state=c.load_state(p);c.remember(state,'seoul',1,c.extract(S,'seoul',1));c.export(p,state)
   first=S.replace("'99'","'100'")+'총 2 건 1 / 2'
   with patch('sys.argv',['collector.py','--site','seoul','--all','--output',d]),patch.object(c.Client,'check_robots'),patch.object(c.Client,'read',return_value=first) as read:
    self.assertEqual(c.main(),1);self.assertEqual(read.call_count,1)
   logging.shutdown();logging.getLogger().handlers.clear()
   self.assertIn('seoul:99',c.load_state(p)['records'])
 def test_classification_and_csv_lock(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);state=c.load_state(p)
   c.remember(state,'national',1,c.extract(N,'national',1));c.remember(state,'seoul',1,c.extract(S,'seoul',1))
   old_replace=Path.replace
   def locked(src,dst):
    if Path(dst).name=='awards.csv':raise PermissionError('Excel lock')
    return old_replace(src,dst)
   with patch.object(Path,'replace',locked):c.export(p,state)
   self.assertTrue((p/'awards_latest.csv').exists())
   self.assertEqual(len(json.loads((p/'guidance_papers.json').read_text())),1)
   self.assertEqual(len(json.loads((p/'student_projects.json').read_text())),1)
   self.assertEqual(len(json.loads((p/'projects.json').read_text())),1)
 def test_regional_import(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);file=p/'input.csv';state=c.load_state(p)
   file.write_text('source,id,title,year,url\n경기,2026-1,테스트 연구,2026,https://example.org/results\n',encoding='utf-8-sig')
   self.assertEqual(c.import_region(file,state),1);c.import_region(file,state);self.assertEqual(len(state['records']),1)
   row=next(iter(state['records'].values()));self.assertEqual(c.category(row),'unclassified')
if __name__=='__main__':unittest.main()
