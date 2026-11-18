"""Explicit, terminal-only OpenAI preview. Keys are never written to files."""
import getpass,os,sys,warnings
from . import server
from .service import ROOT

def main():
    if not sys.stdin.isatty():
        print('키가 화면에 노출되지 않도록 직접 터미널에서 START_AI_LOCAL.bat를 실행해주세요.')
        return 1
    print('OpenAI API를 사용하는 로컬 테스트입니다. Gemini API 연결은 아직 없습니다.')
    print('관심사 분석과 실제 평가 버튼을 실행하면 OpenAI API 요금이 발생할 수 있습니다.')
    try:
        if input('계속하려면 YES를 입력하세요 (취소: Enter): ').strip()!='YES':
            print('AI 실행을 취소했습니다. 무료 테스트는 START_LOCAL.bat를 사용하세요.')
            return 0
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            api_key=getpass.getpass('OpenAI API 키 입력 (화면에 표시되지 않음): ').strip()
    except getpass.GetPassWarning:
        print('비밀 입력을 지원하는 터미널이 필요합니다. Windows 실행 창에서 다시 실행해주세요.')
        return 1
    except (KeyboardInterrupt,EOFError):
        print('\nAI 실행을 취소했습니다.')
        return 130
    if not api_key or any(c.isspace() for c in api_key):
        print('키가 비어 있거나 공백이 포함됐습니다. 키를 확인한 후 다시 실행해주세요.')
        return 1
    names=('LLM_API_KEY','OPENAI_API_KEY','DATA_DIR')
    previous={name:os.environ.get(name) for name in names};argv=sys.argv[:]
    try:
        os.environ['LLM_API_KEY']=api_key
        os.environ.pop('OPENAI_API_KEY',None)
        os.environ['DATA_DIR']=str(ROOT/'.local')
        sys.argv=['backend.server','--port','8012','--open-browser']
        server.main()
        return 0
    except KeyboardInterrupt:return 130
    except Exception:
        print('AI 테스트 서버를 시작하지 못했습니다. 이전 실행 창과 Python 환경을 확인해주세요.')
        return 1
    finally:
        for name,value in previous.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value
        sys.argv=argv
        api_key=''

if __name__=='__main__':raise SystemExit(main())
