"""Offline agent CLI checks using real subprocess pipes, including Windows shims."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Cancelled, Pipeline, ROOT


# Long enough to exceed both cmd.exe's 8,191-character limit and Windows'
# 32,767-character process command line, with characters a shell could interpret.
PROMPT = ('[12.34\u201356.78] Za\u017c\u00f3\u0142\u0107 g\u0119\u015bl\u0105 ja\u017a\u0144 \U0001f3ac \u4e16\u754c "quoted" \'single\' '
          '%PATH% !value! & | < > ^ ( ) \\path\\file\n') * 1300
ANSWER = {'clips': [{'start': 12.34, 'end': 56.78, 'score': 9,
                     'title': 'Za\u017c\u00f3\u0142\u0107 \U0001f3ac', 'reason': 'Offline fixture',
                     'hook_sentence': 'Pe\u0142ny tekst bez obci\u0119cia.'}]}

CLAUDE_FIXTURE = '''import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
(root / "claude-stdin.bin").write_bytes(sys.stdin.buffer.read())
(root / "claude-call.json").write_text(
    json.dumps({"argv": sys.argv[1:], "cwd": str(Path.cwd())}), encoding="utf-8")
sys.stdout.buffer.write((root / "claude-response.txt").read_bytes())
'''

CODEX_FIXTURE = '''import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
(root / "codex-stdin.bin").write_bytes(sys.stdin.buffer.read())
(root / "codex-call.json").write_text(
    json.dumps({"argv": sys.argv[1:], "cwd": str(Path.cwd())}), encoding="utf-8")
if (root / "codex-fail").exists():
    sys.stderr.write("Offline simulated Codex failure")
    sys.exit(23)
output = Path(sys.argv[sys.argv.index("--output-last-message") + 1])
output.write_bytes((root / "codex-response.json").read_bytes())
'''


class AgentCliReview(unittest.TestCase):
    def setUp(self):
        checks = (ROOT / 'checks').resolve()
        self.assertTrue(checks.is_relative_to(ROOT.resolve()))
        checks.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='agent-cli-', dir=checks)
        self.addCleanup(self.temporary.cleanup)
        self.fixture = Path(self.temporary.name).resolve()
        self.assertTrue(self.fixture.is_relative_to(checks))
        self.work = self.fixture / 'work'
        self.claude_script = self.fixture / 'fake_claude.py'
        self.codex_script = self.fixture / 'fake_codex.py'
        self.claude_script.write_text(CLAUDE_FIXTURE, encoding='utf-8')
        self.codex_script.write_text(CODEX_FIXTURE, encoding='utf-8')
        (self.fixture / 'codex-response.json').write_text(
            json.dumps(ANSWER, ensure_ascii=False), encoding='utf-8')
        self.response('wrapped')

    def response(self, style):
        answer = json.dumps(ANSWER, ensure_ascii=False)
        if style in ('fenced', 'wrapped-fenced'):
            answer = '```json\n' + answer + '\n```'
        if style in ('wrapped', 'wrapped-fenced'):
            # Claude Code's --output-format json returns the assistant text in
            # a result envelope, not directly as the application clips object.
            answer = json.dumps({'type': 'result', 'subtype': 'success',
                                 'is_error': False, 'result': answer}, ensure_ascii=False)
        (self.fixture / 'claude-response.txt').write_text(answer, encoding='utf-8')

    def request(self, claude, codex=None):
        pipeline = Pipeline()
        # Wrap run rather than replacing the process: real child stdin is the
        # regression oracle, and the spy also checks the configured timeout.
        with patch('engine.find_codex', return_value=codex), \
                patch('engine.find_claude', return_value=claude), \
                patch.object(pipeline, 'run', wraps=pipeline.run) as run:
            answer = pipeline.model_request(PROMPT, self.work)
        self.assertEqual(answer, ANSWER)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs['cwd'], self.work)
            self.assertEqual(call.kwargs['input_text'], PROMPT)
            self.assertEqual(call.kwargs['timeout'], 600)
            self.assertLess(len(subprocess.list2cmdline(call.args[0])), 8191)
        return run

    def received(self, agent):
        received = (self.fixture / f'{agent}-stdin.bin').read_bytes()
        # Popen's text-mode stdin converts LF to the host's line ending. Check
        # every transported UTF-8 byte, then the original LF transcript text.
        self.assertEqual(received, PROMPT.replace('\n', os.linesep).encode('utf-8'))
        self.assertEqual(received.decode('utf-8').replace('\r\n', '\n'), PROMPT)
        call = json.loads((self.fixture / f'{agent}-call.json').read_text(encoding='utf-8'))
        self.assertEqual(Path(call['cwd']).resolve(), self.work.resolve())
        if agent == 'claude':
            self.assertEqual(call['argv'], ['-p', '--output-format', 'json'])
        else:
            self.assertEqual(call['argv'][0], 'exec')
            self.assertEqual(call['argv'][-1], '-')
        self.assertNotIn(PROMPT, call['argv'])

    def test_claude_only_long_unicode_prompt_uses_real_stdin(self):
        self.assertGreater(len(PROMPT), 100000)
        self.assertGreater(len(PROMPT.encode('utf-16-le')) // 2, 32767)
        run = self.request([sys.executable, str(self.claude_script)])
        self.assertEqual(run.call_count, 1)
        self.received('claude')
        self.assertFalse((self.fixture / 'codex-call.json').exists())

    @unittest.skipUnless(os.name == 'nt', 'cmd.exe shims are specific to Windows')
    def test_windows_cmd_shim_accepts_long_prompt_without_command_expansion(self):
        shim = self.fixture / 'fake_claude.cmd'
        # Only the fixed CLI flags reach %*. The transcript must stay in the
        # inherited pipe so quotes, percent expansions and shell operators are text.
        shim.write_text(f'@echo off\n"{sys.executable}" "{self.claude_script}" %*\n',
                        encoding='utf-8')
        self.request([str(shim)])
        self.received('claude')

    def test_claude_json_result_and_markdown_fences(self):
        for style in ('wrapped-fenced', 'fenced'):
            with self.subTest(style=style):
                self.response(style)
                self.request([sys.executable, str(self.claude_script)])
                self.received('claude')

    def test_codex_is_preferred_when_both_agents_are_available(self):
        run = self.request([sys.executable, str(self.claude_script)],
                           [sys.executable, str(self.codex_script)])
        self.assertEqual(run.call_count, 1)
        self.received('codex')
        self.assertFalse((self.fixture / 'claude-call.json').exists())
        self.assertEqual(list(self.work.glob('selection-*.json')),
                         [self.work / 'selection-schema.json'])

    def test_failed_codex_falls_back_to_claude_with_the_complete_prompt(self):
        (self.fixture / 'codex-fail').touch()
        self.response('wrapped-fenced')
        run = self.request([sys.executable, str(self.claude_script)],
                           [sys.executable, str(self.codex_script)])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(Path(run.call_args_list[0].args[0][1]), self.codex_script)
        self.assertEqual(Path(run.call_args_list[1].args[0][1]), self.claude_script)
        self.received('codex')
        self.received('claude')
        self.assertEqual(list(self.work.glob('selection-*.json')),
                         [self.work / 'selection-schema.json'])

    def test_cancellation_propagates_without_trying_another_agent(self):
        for codex in (None, [sys.executable, str(self.codex_script)]):
            with self.subTest(codex_available=bool(codex)):
                pipeline = Pipeline()
                with patch('engine.find_codex', return_value=codex), \
                        patch('engine.find_claude', return_value=[sys.executable, str(self.claude_script)]), \
                        patch.object(pipeline, 'run', side_effect=Cancelled('Offline cancellation')) as run:
                    with self.assertRaises(Cancelled):
                        pipeline.model_request(PROMPT, self.work)
                self.assertEqual(run.call_count, 1)
        self.assertFalse((self.fixture / 'claude-call.json').exists())
        self.assertFalse((self.fixture / 'codex-call.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
