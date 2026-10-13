import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mex_tool import diff, inspect, patched_bytes


class MexTests(unittest.TestCase):
    def setUp(self):
        self.data = (b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\r\n'
                     b'<configuration xmlns="urn:synthetic:mex" version="15">\r\n'
                     b'<!--preserve--><common><processor>S32K312</processor>'
                     b'<package>synthetic-package</package><mcu_data>synthetic-sdk</mcu_data>'
                     b'<cores selected="M7_0"/></common><tools>'
                     b'<periphs name="Peripherals" enabled="true"><functional_groups>'
                     b'<functional_group name="fg"><instances><instance name="Uart" mode="ip">'
                     b'<config_set><setting name="SyntheticBaud" value="9600"/></config_set>'
                     b'</instance></instances></functional_group></functional_groups>'
                     b'</periphs><future_extension x="preserve"/></tools></configuration>\r\n')

    def plan(self, old='value="9600"', new='value="115200"', data=None):
        return {'sha256': hashlib.sha256(data or self.data).hexdigest(),
                'replacements': [{'old': old, 'new': new}]}

    def test_exact_byte_preservation(self):
        out = patched_bytes(self.data, self.plan())
        self.assertEqual(out, self.data.replace(b'value="9600"', b'value="115200"'))

    def test_stale_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            patched_bytes(self.data + b' ', self.plan())

    def test_repeated_match_rejected(self):
        with self.assertRaisesRegex(ValueError, 'match once'):
            patched_bytes(self.data, self.plan('name=', 'other='))

    def test_overlapping_edits_rejected(self):
        plan = self.plan()
        plan['replacements'].append({'old': '9600', 'new': '19200'})
        with self.assertRaisesRegex(ValueError, 'overlap'):
            patched_bytes(self.data, plan)

    def test_target_migration_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            patched_bytes(self.data, self.plan('S32K312', 'S32K311'))

    def test_reference_device_cannot_be_patched(self):
        data = self.data.replace(b'S32K312', b'S32K344')
        with self.assertRaisesRegex(ValueError, 'only S32K'):
            patched_bytes(data, self.plan(data=data))

    def test_invalid_xml_rejected(self):
        with self.assertRaises(ET.ParseError):
            patched_bytes(self.data, self.plan('value="9600"', 'value="<"'))

    def test_line_ending_conversion_rejected(self):
        with self.assertRaisesRegex(ValueError, 'newline style'):
            patched_bytes(self.data, self.plan('<!--preserve-->', '<!--preserve-->\n'))

    def test_invalid_plan_rejected(self):
        with self.assertRaisesRegex(ValueError, 'JSON object'):
            patched_bytes(self.data, [])

    def test_core_subtree_change_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            patched_bytes(self.data, self.plan('<cores selected="M7_0"/>',
                                              '<cores selected="M7_0"><core id="changed"/></cores>'))

    def test_summary_and_structural_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.mex', Path(tmp) / 'b.mex'
            a.write_bytes(self.data)
            b.write_bytes(patched_bytes(self.data, self.plan()))
            self.assertTrue(inspect(a)['in_scope'])
            self.assertEqual(inspect(a)['tools'][0]['functional_groups'][0]['instances'][0]['name'], 'Uart')
            self.assertEqual(diff(a, b)['change_count'], 1)
            b.write_bytes(self.data.replace(b'\r\n', b'\n').replace(
                b'name="SyntheticBaud" value="9600"', b'value="9600" name="SyntheticBaud"'))
            self.assertEqual(diff(a, b)['change_count'], 0)

    def test_cli_dry_run_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            src, plan, out = path / 'source.mex', path / 'plan.json', path / 'out.mex'
            src.write_bytes(self.data)
            plan.write_text(json.dumps(self.plan()), encoding='utf-8')
            cmd = [sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/mex_tool.py'),
                   'patch', str(src), str(plan)]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertFalse(out.exists())
            self.assertEqual(subprocess.run(cmd + ['--output', str(out)], capture_output=True).returncode, 0)
            saved = out.read_bytes()
            self.assertEqual(subprocess.run(cmd + ['--output', str(out)], capture_output=True).returncode, 2)
            self.assertEqual(out.read_bytes(), saved)
            self.assertEqual(src.read_bytes(), self.data)


if __name__ == '__main__':
    unittest.main()
