import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_xmind as builder


def node(title, *children):
    return {'title': title, 'children': list(children)}


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.case = node('tc-p0: Reject cross-tenant request',
                         node('pc: User A belongs to tenant A'),
                         node('步骤1：Submit request for tenant B', node('Request is rejected; no record is created')),
                         node('rc: CASE-001; RULE-001; PRD 3.2'),
                         node('tag: service,security,api'))
        self.root = node('Project', node('Module', self.case))

    def test_strict_valid(self):
        self.assertEqual(builder.validate(self.root, strict=True),
                         (1, 1, {'p0': 1, 'p1': 0, 'p2': 0, 'p3': 0, 'none': 0}))

    def test_basic_legacy(self):
        root = node('Project', node('Module', node('tc: Legacy', node('Action', node('Expected')))))
        self.assertEqual(builder.validate(root)[1], 1)
        with self.assertRaises(ValueError):
            builder.validate(root, strict=True)

    def test_invalid_delivery_cases(self):
        variants = []
        for prefix in ('pc:', 'rc:', 'tag:'):
            case = copy.deepcopy(self.case)
            case['children'] = [c for c in case['children'] if not c['title'].startswith(prefix)]
            variants.append(case)
        for title in ('pc:', 'pc-p0: value', 'tag: a，b', 'tag: a,,b', 'tag: a,a'):
            case = copy.deepcopy(self.case)
            index = 3 if title.startswith('tag') else 0
            case['children'][index]['title'] = title
            variants.append(case)
        for title in ('步骤2：Action', '步骤1：'):
            case = copy.deepcopy(self.case)
            case['children'][1]['title'] = title
            variants.append(case)
        for title in ('同上', '正常', 'TBD', ''):
            case = copy.deepcopy(self.case)
            case['children'][1]['children'][0]['title'] = title
            variants.append(case)
        case = copy.deepcopy(self.case)
        case['children'].append(node('rc: duplicate'))
        variants.append(case)
        for case in variants:
            with self.subTest(case=case), self.assertRaises(ValueError):
                builder.validate(node('Project', node('Module', case)), strict=True)

    def test_invalid_structure(self):
        roots = [node('Empty'), node('Project', self.case),
                 node('Project', node('Module')),
                 node('Project', node('Module', self.case, copy.deepcopy(self.case)))]
        case = copy.deepcopy(self.case)
        case['title'] = 'tc-none: Invalid priority'
        roots.append(node('Project', node('Module', case)))
        case = copy.deepcopy(self.case)
        case['children'][1]['children'] = []
        roots.append(node('Project', node('Module', case)))
        for root in roots:
            with self.subTest(root=root), self.assertRaises(ValueError):
                builder.validate(root, strict=True)

    def test_module_depth_limit(self):
        root = self.case
        for i in range(8):
            root = node(f'Module {i}', root)
        builder.validate(node('Project', root), strict=True)
        with self.assertRaises(ValueError):
            builder.validate(node('Project', node('Too deep', root)), strict=True)

    def test_parser_and_round_trip(self):
        with tempfile.TemporaryDirectory(prefix='test-xmind-') as folder:
            source = Path(folder) / 'outline.txt'
            source.write_text('\ufeffProject\n  Module\n    tc: Legacy\n      Action\n        Expected\n', encoding='utf-8')
            root = builder.load_outline(source)
            builder.validate(root)
            output = Path(folder) / 'result.xmind'
            builder.build(root, output)
            with zipfile.ZipFile(output) as archive:
                topic = json.loads(archive.read('content.json'))[0]['rootTopic']
                self.assertEqual(topic['children']['attached'][0]['children']['attached'][0]['title'], 'tc: Legacy')
            for text in ('Project\n\tModule\n', 'Project\n   Module\n', 'Project\n    Module\n'):
                source.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    builder.load_outline(source)

    def test_strict_cli(self):
        with tempfile.TemporaryDirectory(prefix='test-xmind-cli-') as folder:
            source = Path(folder) / 'outline.txt'
            source.write_text('Project\n  Module\n    tc-p0: Reject request\n'
                              '      pc: Authenticated user\n      步骤1：Submit request\n'
                              '        Request is rejected; no record is created\n'
                              '      rc: CASE-001; RULE-001; PRD 3.2\n'
                              '      tag: service,security,api\n', encoding='utf-8')
            output = Path(folder) / 'result.xmind'
            command = [sys.executable, '-X', 'utf8', builder.__file__, '--strict', str(source)]
            result = subprocess.run(command + [str(output)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            self.assertIn('NOT VERIFIED:', result.stdout)
            original = source.read_bytes()
            result = subprocess.run(command + [str(source)], capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
