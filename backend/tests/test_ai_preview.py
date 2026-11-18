import io,os,sys,unittest
from unittest.mock import patch
from backend import ai_preview

class Preview(unittest.TestCase):
 def execute(self,answer='YES',secret='dummy-key',tty=True,effect=None):
  stream=io.StringIO()
  with patch('backend.ai_preview.sys.stdin.isatty',return_value=tty),patch('builtins.input',return_value=answer) as prompt,patch('backend.ai_preview.getpass.getpass',return_value=secret) as password,patch('backend.ai_preview.server.main',side_effect=effect) as run,patch('sys.stdout',stream):
   code=ai_preview.main()
  self.assertNotIn(secret,stream.getvalue())
  return code,prompt.call_count,password.call_count,run.call_count
 def test_cancel_never_prompts_for_key_or_runs_server(self):
  self.assertEqual(self.execute(answer=''),(0,1,0,0))
 def test_redirected_input_does_not_echo_key(self):
  self.assertEqual(self.execute(tty=False),(1,0,0,0))
 def test_unsafe_getpass_fallback_stops_without_server(self):
  with patch('backend.ai_preview.sys.stdin.isatty',return_value=True),patch('builtins.input',return_value='YES'),patch('backend.ai_preview.getpass.getpass',side_effect=ai_preview.getpass.GetPassWarning()),patch('backend.ai_preview.server.main') as run,patch('sys.stdout',io.StringIO()):
   self.assertEqual(ai_preview.main(),1);run.assert_not_called()
 def test_empty_or_whitespace_key_rejected(self):
  for value in ['','one two']:
   with patch('backend.ai_preview.sys.stdin.isatty',return_value=True),patch('builtins.input',return_value='YES'),patch('backend.ai_preview.getpass.getpass',return_value=value),patch('backend.ai_preview.server.main') as run,patch('sys.stdout',io.StringIO()):
    self.assertEqual(ai_preview.main(),1);run.assert_not_called()
 def test_key_is_process_only_and_environment_restored(self):
  before=sys.argv[:]
  def inside():
   self.assertEqual(os.environ['LLM_API_KEY'],'dummy-key');self.assertNotIn('OPENAI_API_KEY',os.environ);self.assertEqual(sys.argv,['backend.server','--port','8012','--open-browser'])
  with patch.dict(os.environ,{'LLM_API_KEY':'previous','OPENAI_API_KEY':'other-previous','DATA_DIR':'previous-folder'}):
   self.assertEqual(self.execute(effect=inside)[0],0)
   self.assertEqual(os.environ['LLM_API_KEY'],'previous');self.assertEqual(os.environ['OPENAI_API_KEY'],'other-previous');self.assertEqual(os.environ['DATA_DIR'],'previous-folder')
  self.assertEqual(sys.argv,before)
 def test_failure_restores_environment_without_error_details(self):
  with patch.dict(os.environ,{'LLM_API_KEY':'previous'}):
   self.assertEqual(self.execute(effect=RuntimeError('dummy-key must not leak'))[0],1);self.assertEqual(os.environ['LLM_API_KEY'],'previous')
if __name__=='__main__':unittest.main()
