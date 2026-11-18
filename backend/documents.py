"""Local document-to-text extraction; no AI, network, or OCR."""
import base64,binascii,io,re,shutil,subprocess,tempfile,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from .service import ServiceError

MAX_BYTES=5_000_000
MAX_TEXT=100_000

class NoDTD(ET.TreeBuilder):
 def doctype(self,*args):raise ServiceError('DTD가 포함된 문서는 처리하지 않습니다.',400)

def paragraph_text(node):
 if node.tag.rsplit('}',1)[-1]=='t':return node.text or ''
 return ''.join(paragraph_text(child) for child in node if child.tag.rsplit('}',1)[-1]!='p')

def decode_txt(data):
 for encoding in ('utf-8-sig','cp949'):
  try:return data.decode(encoding)
  except UnicodeDecodeError:pass
 raise ServiceError('TXT 인코딩을 읽지 못했습니다. UTF-8로 저장한 뒤 다시 불러와주세요.',400)

def archive_text(data,kind):
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
   infos=archive.infolist()
   if len(infos)>2000 or sum(i.file_size for i in infos)>30_000_000:raise ServiceError('문서 압축 해제 크기 제한을 초과했습니다.',400)
   if kind=='.docx':names=['word/document.xml']
   else:names=sorted([i.filename for i in infos if re.fullmatch(r'Contents/section\d+\.xml',i.filename)],key=lambda n:int(re.search(r'\d+',n)[0]))
   if not names:raise ServiceError('HWPX 본문을 찾지 못했습니다.',400)
   lines=[]
   for name in names:
    raw=archive.read(name)
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)',raw,re.I):raise ServiceError('외부 엔터티가 포함된 문서는 처리하지 않습니다.',400)
    root=ET.fromstring(raw,parser=ET.XMLParser(target=NoDTD()))
    # DOCX paragraphs and HWPX paragraphs both use local tag p/t.
    for para in root.iter():
     if para.tag.rsplit('}',1)[-1]=='p':
      value=paragraph_text(para)
      if value:lines.append(value)
   return '\n'.join(lines)
 except (zipfile.BadZipFile,KeyError,RuntimeError,ET.ParseError,ValueError):
  raise ServiceError('문서 본문을 읽지 못했습니다. 암호화 여부를 확인하거나 TXT로 변환해주세요.',400) from None

def extract_document(body):
 if not isinstance(body,dict) or not isinstance(body.get('filename'),str) or not isinstance(body.get('content'),str):raise ServiceError('파일 요청 형식이 올바르지 않습니다.',400)
 if len(body['content'])>6_700_000:raise ServiceError('파일은 5MB 이하로 선택해주세요.',400)
 try:data=base64.b64decode(body['content'],validate=True)
 except (binascii.Error,ValueError):raise ServiceError('파일 전송 형식이 올바르지 않습니다.',400) from None
 if not data or len(data)>MAX_BYTES:raise ServiceError('파일은 비어 있지 않은 5MB 이하 파일이어야 합니다.',400)
 kind=Path(body['filename']).suffix.lower();warnings=[]
 if kind=='.txt':text=decode_txt(data)
 elif kind in ('.docx','.hwpx'):text=archive_text(data,kind)
 elif kind=='.hwp':
  converter=shutil.which('hwp5txt')
  if not converter:raise ServiceError('이 환경에는 HWP 변환 도구가 없습니다. 한글의 다른 이름으로 저장에서 HWPX 또는 DOCX를 선택하거나 TXT로 저장해주세요.',422)
  try:
   with tempfile.TemporaryDirectory() as folder:
    file=Path(folder)/'document.hwp';file.write_bytes(data)
    output=Path(folder)/'output.txt'
    # Output cap is checked after conversion; execution is time-limited and shell-free.
    with output.open('wb') as stream:subprocess.run([converter,str(file)],stdout=stream,stderr=subprocess.DEVNULL,timeout=20,check=True)
    if output.stat().st_size>MAX_TEXT*4:raise ServiceError('추출된 텍스트가 너무 깁니다. 주제 목록만 별도 파일로 저장해주세요.',400)
    text=output.read_text(encoding='utf-8')
  except (subprocess.SubprocessError,OSError,UnicodeError):raise ServiceError('HWP 변환에 실패했습니다. 한글에서 HWPX·DOCX·TXT로 저장 후 다시 불러와주세요.',422) from None
 else:raise ServiceError('TXT, DOCX, HWPX, HWP 파일을 선택해주세요.',400)
 if not text.strip():raise ServiceError('추출할 텍스트가 없습니다. 스캔 문서 OCR은 지원하지 않습니다.',400)
 if len(text)>MAX_TEXT:raise ServiceError('추출된 텍스트가 너무 깁니다. 주제 목록만 별도 파일로 저장해주세요.',400)
 warnings.append('문단/줄 단위 추출 결과입니다. 주제 하나를 한 줄로 정리하고, 번호·표·설명문이 섞이지 않았는지 확인해주세요.')
 return {'text':text,'format':kind[1:],'warnings':warnings}
