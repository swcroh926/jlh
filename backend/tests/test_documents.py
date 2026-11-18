import base64,io,json,tempfile,threading,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from urllib import request,error
from http.server import ThreadingHTTPServer
from backend.documents import extract_document,MAX_BYTES
from backend.service import ServiceError,EvaluationService,validate
from backend.server import handler

def archive(files):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
  for name,content in files.items():z.writestr(name,content)
 return stream.getvalue()
def body(name,data):return {'filename':name,'content':base64.b64encode(data).decode()}
DOC='<w:document xmlns:w="urn:word"><w:body><w:p><w:r><w:t>첫번째  주제</w:t></w:r></w:p><w:p><w:r><w:t>두번째 주제</w:t></w:r></w:p></w:body></w:document>'
HWPX='<hp:sec xmlns:hp="urn:paragraph"><hp:p><hp:run><hp:t>생물 성장</hp:t></hp:run></hp:p></hp:sec>'
class Documents(unittest.TestCase):
 def test_docx_preserves_paragraphs_and_spaces(self):
  result=extract_document(body('주제.docx',archive({'word/document.xml':DOC})))
  self.assertEqual(result['text'],'첫번째  주제\n두번째 주제');self.assertTrue(result['warnings'])
 def test_hwpx_sections_sorted_numerically(self):
  result=extract_document(body('주제.hwpx',archive({'Contents/section10.xml':HWPX.replace('생물 성장','10번'),'Contents/section2.xml':HWPX.replace('생물 성장','2번')})))
  self.assertEqual(result['text'],'2번\n10번')
 def test_nested_paragraphs_not_duplicated(self):
  xml='<doc><p><t>바깥</t><table><p><t>안쪽</t></p></table></p></doc>'
  self.assertEqual(extract_document(body('주제.docx',archive({'word/document.xml':xml})))['text'],'바깥\n안쪽')
 def test_txt_encodings(self):
  for encoding in ('utf-8-sig','cp949'):
   self.assertEqual(extract_document(body('주제.txt','원래  주제'.encode(encoding)))['text'],'원래  주제')
 def test_bad_empty_or_unsupported(self):
  for payload in [{},body('a.docx',b'broken'),body('a.txt',b''),body('a.exe',b'abc'),{'filename':'a.txt','content':'???'}]:
   with self.assertRaises(ServiceError):extract_document(payload)
 def test_empty_scan(self):
  with self.assertRaises(ServiceError):extract_document(body('scan.docx',archive({'word/document.xml':'<document/>'})))
 def test_oversize_and_too_many_zip_entries(self):
  with self.assertRaises(ServiceError):extract_document(body('a.txt',b'a'*(MAX_BYTES+1)))
  with self.assertRaises(ServiceError):extract_document(body('a.hwpx',archive({str(i):'x' for i in range(2001)})))
 def test_entity_and_utf16_doctype(self):
  xml='<!DOCTYPE document [<!ENTITY x "unsafe">]><document><p><t>&x;</t></p></document>'
  for content in [xml,xml.encode('utf-16')]:
   with self.assertRaises(ServiceError):extract_document(body('a.docx',archive({'word/document.xml':content})))
 def test_hwp_no_converter(self):
  with patch('backend.documents.shutil.which',return_value=None):
   with self.assertRaises(ServiceError) as e:extract_document(body('a.hwp',b'example'))
  self.assertEqual(e.exception.status,422);self.assertIn('HWPX',str(e.exception))
 def test_hwp_converter_success_and_failure(self):
  def run(args,**kwargs):kwargs['stdout'].write('변환 주제'.encode())
  with patch('backend.documents.shutil.which',return_value='/fake/hwp5txt'),patch('backend.documents.subprocess.run',side_effect=run):
   self.assertEqual(extract_document(body('a.hwp',b'example'))['text'],'변환 주제')
  with patch('backend.documents.shutil.which',return_value='/fake/hwp5txt'),patch('backend.documents.subprocess.run',side_effect=OSError()):
   with self.assertRaises(ServiceError):extract_document(body('a.hwp',b'example'))
 def test_new_conditions_and_privacy(self):
  x=validate({'ideas':['조건을 비교할까?'],'grade':'초등 5학년','budget':0,'weeks':8,'location':'학원','hoursPerSession':2,'sessionsPerWeek':1,'name':'private','region':'private'})
  self.assertEqual(x['budget'],0);self.assertEqual(x['hoursPerSession'],2);self.assertEqual(x['location'],'학원');self.assertNotIn('name',x);self.assertNotIn('region',x)

class ServerDefaults(unittest.TestCase):
 def test_default_budget_vs_zero(self):
  for value in [None,'',300000]:
   payload={'ideas':['조건을 비교할까?'],'grade':'초등 5학년','budget':value}
   self.assertEqual(validate(payload)['budget'],300000);self.assertEqual(validate(payload)['weeks'],8)
  self.assertEqual(validate({'ideas':['조건을 비교할까?'],'grade':'초등 5학년','budget':0})['budget'],0)
 def test_exact_duplicates_not_silently_removed(self):
  with self.assertRaises(ServiceError):validate({'ideas':['같은 주제','같은 주제'],'grade':'초등 5학년'})

class DocumentHTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.svc=EvaluationService(Path(self.tmp.name));self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.svc));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def test_extraction_http_and_origin_guard(self):
  payload=json.dumps(body('a.docx',archive({'word/document.xml':DOC}))).encode()
  r=request.Request(self.url+'/api/extract-topics',data=payload,headers={'Content-Type':'application/json','Origin':self.url})
  with request.urlopen(r) as response:self.assertIn('첫번째',json.load(response)['text'])
  r=request.Request(self.url+'/api/extract-topics',data=payload,headers={'Content-Type':'application/json','Origin':'https://untrusted.example'})
  with self.assertRaises(error.HTTPError) as e:request.urlopen(r)
  self.assertEqual(e.exception.code,403);e.exception.close()
if __name__=='__main__':unittest.main()
