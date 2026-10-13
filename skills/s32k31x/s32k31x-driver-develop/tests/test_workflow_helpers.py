from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ecuc_roundtrip import compare
from s32ds_cli import classify


ECUC = b'''<?xml version="1.0"?><AUTOSAR><AR-PACKAGES><AR-PACKAGE>
<SHORT-NAME>Can_43_FLEXCAN</SHORT-NAME><ELEMENTS><ECUC-MODULE-CONFIGURATION-VALUES>
<SHORT-NAME>Can</SHORT-NAME><DEFINITION-REF>/Can_43_FLEXCAN_v1/Can</DEFINITION-REF>
<CONTAINERS><ECUC-CONTAINER-VALUE><SHORT-NAME>CanConfigSet</SHORT-NAME>
<SUB-CONTAINERS><ECUC-CONTAINER-VALUE><SHORT-NAME>ChoiceA</SHORT-NAME>
<DEFINITION-REF>/Can_43_FLEXCAN_v1/Can/CanConfigSet/ChoiceA</DEFINITION-REF>
<PARAMETER-VALUES><ECUC-NUMERICAL-PARAM-VALUE><VALUE>3</VALUE></ECUC-NUMERICAL-PARAM-VALUE>
</PARAMETER-VALUES><REFERENCE-VALUES><ECUC-REFERENCE-VALUE><VALUE-REF>/Can/CanConfigSet/Other</VALUE-REF>
</ECUC-REFERENCE-VALUE></REFERENCE-VALUES></ECUC-CONTAINER-VALUE></SUB-CONTAINERS>
</ECUC-CONTAINER-VALUE></CONTAINERS></ECUC-MODULE-CONFIGURATION-VALUES></ELEMENTS>
</AR-PACKAGE></AR-PACKAGES></AUTOSAR>'''


class WorkflowHelperTests(unittest.TestCase):
    def test_ecuc_roundtrip_preserves_choice_list_and_refs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before, after = root / 'before', root / 'after'
            before.mkdir(); after.mkdir()
            (before / 'Can.ecvd').write_bytes(ECUC)
            (after / 'Can.ecvd').write_bytes(ECUC.replace(b'><', b'>\n<'))
            self.assertEqual(compare(before, after)['status'], 'pass')
            (after / 'Can.ecvd').write_bytes(ECUC.replace(b'ChoiceA', b'ChoiceB'))
            self.assertEqual(compare(before, after)['status'], 'roundtrip_mismatch')
            (after / 'Can.ecvd').write_bytes(ECUC.replace(b'/Can/CanConfigSet/Other', b'/Wrong/Other'))
            self.assertEqual(compare(before, after)['status'], 'roundtrip_mismatch')
            (after / 'Can.ecvd').unlink()
            with self.assertRaisesRegex(ValueError, 'contain'):
                compare(before, after)

    def test_cli_classifies_target_error_despite_zero_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'log.bin'
            log.write_text('!MESSAGE [TOOL] The resource "CanIf" from group has the following error: invalid name\n', encoding='utf-8')
            status = classify([log], ['utf-8'], {'canif'}, 'config', 0, [])['status']
            self.assertEqual(status, 'config_error')
            self.assertEqual(classify([log], ['utf-8'], set(), 'config', 0, [])['status'], 'needs_review')
            log.write_text('Done\n', encoding='utf-8')
            self.assertEqual(classify([log], ['utf-8'], {'canif'}, 'config', 0, ['missing'])['status'], 'incomplete')

    def test_cli_creates_manifest_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = root / 'expected.mex'
            source = root / 'source.mex'
            source.write_text('baseline', encoding='utf-8')
            command = [sys.executable, '-c', f'from pathlib import Path; Path({str(expected)!r}).write_text("ok")']
            script = Path(__file__).resolve().parents[1] / 'scripts/s32ds_cli.py'
            result = subprocess.run([sys.executable, str(script), '--evidence', str(root / 'evidence'),
                                     '--kind', 'config', '--module', 'Can', '--expected', str(expected), '--input', str(source),
                                     '--version-label', 'synthetic', '--', *command], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            runs = list((root / 'evidence').iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / 'manifest.json').is_file())
            self.assertTrue((runs[0] / 'stdout.bin').is_file())
            self.assertEqual(next((runs[0] / 'inputs').iterdir()).read_text(encoding='utf-8'), 'baseline')


if __name__ == '__main__':
    unittest.main()
