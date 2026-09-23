# -*- coding: utf-8 -*-
"""
将缩进大纲文本转换为 MeterSphere 可导入的 XMind（Zen）文件。

大纲规则（对应 MeterSphere「用例导入 XMind」规范）：
  - 第 1 个有效行 = 思维导图根节点（不导入系统，仅作项目名）
  - 每级缩进 2 个空格；根的子节点起为「模块」，模块最多支持 8 层
  - 用例节点：「tc: 用例名称」或「tc-p0: 用例名称」（p0/p1/p2/p3 为用例等级）
  - 用例节点的子节点：
      pc: 前置条件（非必填，不允许有子节点）
      rc: 备注（非必填，不允许有子节点）
      tag: 标签1,标签2（非必填，半角逗号分隔，不允许有子节点）
      其他子节点均为「步骤」，步骤的子节点为该步骤的「预期结果」
  - 以 # 开头的行视为注释，不参与解析

用法：
  python -X utf8 build_xmind.py [--strict] <大纲.txt> <输出.xmind>
"""
import argparse
import json
import os
import re
import struct
import sys
import uuid
import zipfile
import zlib

PREFIX_RE = re.compile(r'^(tc|pc|rc|tag)(-[a-z0-9]+)?\s*:')
CASE_RE = re.compile(r'^tc(-([a-z0-9]+))?\s*:\s*(.+)$', re.IGNORECASE)
META_RE = re.compile(r'^(pc|rc|tag)\s*:\s*(\S.*)$', re.IGNORECASE)
STEP_RE = re.compile(r'^步骤([1-9][0-9]*)[：:]\s*(\S.*)$')
PLACEHOLDER_RE = re.compile(r'^(同上|正常|正确|没问题|待确认|待补充|TODO|TBD)[。.!！]?$', re.IGNORECASE)


def load_outline(path):
    """解析缩进大纲，返回 (root_node, source_name)。"""
    root = None
    stack = []  # (depth, node)
    with open(path, encoding='utf-8-sig') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip('\r\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            if '\t' in line[:len(line) - len(line.lstrip())]:
                raise ValueError(f'第 {lineno} 行缩进不能包含 Tab')
            indent = len(line) - len(line.lstrip(' '))
            if indent % 2 != 0:
                raise ValueError(f'第 {lineno} 行缩进不是 2 的倍数：{line[:40]}')
            depth = indent // 2
            title = line.strip()
            node = {'title': title, 'children': []}
            if root is None:
                if depth != 0:
                    raise ValueError(f'第 {lineno} 行根节点缩进必须为 0')
                root = node
                stack = [(0, node)]
                continue
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if not stack or stack[-1][0] != depth - 1:
                raise ValueError(f'第 {lineno} 行层级跳跃：{title[:40]}')
            stack[-1][1]['children'].append(node)
            stack.append((depth, node))
    if root is None:
        raise ValueError('大纲为空，未找到根节点')
    return root


def check_prefix(title):
    """校验以 tc/pc/rc/tag 开头的节点必须符合规范格式。"""
    low = title.lower()
    if low.startswith(('tc', 'pc', 'rc', 'tag')) and not PREFIX_RE.match(low):
        raise ValueError(
            f'节点「{title[:40]}」以 tc/pc/rc/tag 开头但不符合「前缀: 内容」格式，'
            '请调整标题，避免被 MeterSphere 误判为用例/前置条件/备注/标签节点')


def is_case(title):
    return title.lower().startswith('tc')


def is_meta(title):
    return title.lower().startswith(('pc', 'rc', 'tag'))


def validate(root, strict=False):
    """结构校验 + 统计。返回 (module_count, case_count, priority_counts)。"""
    stats = {'p0': 0, 'p1': 0, 'p2': 0, 'p3': 0, 'none': 0}
    module_count = 0
    case_count = 0
    case_titles = set()

    def walk(node, module_depth):
        nonlocal module_count, case_count
        title = node['title']
        check_prefix(title)
        if node is root:
            for child in node['children']:
                walk(child, 0)
            return
        if is_case(title):
            match = CASE_RE.match(title.upper())
            if not match:
                raise ValueError(f'用例节点格式错误：{title[:40]}')
            level = (match.group(2) or '').lower()
            if level and level not in ('p0', 'p1', 'p2', 'p3'):
                raise ValueError(f'用例等级不合法：{title[:40]}')
            if strict:
                if module_depth == 0:
                    raise ValueError(f'用例必须位于模块下：{title[:40]}')
                if not level:
                    raise ValueError(f'正式用例缺少优先级：{title[:40]}')
                case_title = match.group(3).strip().casefold()
                if case_title in case_titles:
                    raise ValueError(f'用例名称重复，请补充对象或条件：{title[:40]}')
                case_titles.add(case_title)
            stats[level or 'none'] += 1
            case_count += 1
            steps = 0
            metadata = set()
            for child in node['children']:
                child_low = child['title'].lower()
                if child_low.startswith(('pc', 'rc', 'tag')):
                    if not PREFIX_RE.match(child_low):
                        raise ValueError(f'用例「{title[:30]}」下的标注节点格式错误：{child["title"][:30]}')
                    if child['children']:
                        raise ValueError(f'前置条件/备注/标签节点不允许有子节点：{child["title"][:30]}')
                    if strict:
                        meta = META_RE.fullmatch(child['title'])
                        if not meta:
                            raise ValueError(f'元数据前缀不合法或内容为空：{child["title"][:40]}')
                        key = meta.group(1).lower()
                        if key in metadata:
                            raise ValueError(f'用例「{title[:30]}」的 {key} 重复')
                        metadata.add(key)
                        if key == 'tag':
                            tags = [tag.strip() for tag in meta.group(2).split(',')]
                            if '，' in meta.group(2) or any(not tag for tag in tags) or len(set(tags)) != len(tags):
                                raise ValueError(f'标签须用半角逗号分隔且非空、不重复：{child["title"][:40]}')
                else:
                    steps += 1
                    if strict:
                        step = STEP_RE.fullmatch(child['title'])
                        if not step or int(step.group(1)) != steps:
                            raise ValueError(f'步骤须从1连续编号且动作非空：{child["title"][:40]}')
                    if not child['children']:
                        raise ValueError(f'用例「{title[:30]}」的步骤缺少预期结果：{child["title"][:30]}')
                    for exp in child['children']:
                        if exp['children']:
                            raise ValueError(f'预期结果下不允许再有子节点：{exp["title"][:30]}')
                        if strict and (not exp['title'].strip() or PLACEHOLDER_RE.fullmatch(exp['title'].strip())):
                            raise ValueError(f'预期为空或使用占位描述：{exp["title"][:40]}')
            if steps == 0:
                raise ValueError(f'用例「{title[:30]}」缺少步骤节点')
            if strict and metadata != {'pc', 'rc', 'tag'}:
                raise ValueError(f'用例「{title[:30]}」缺少元数据：{", ".join(sorted({"pc", "rc", "tag"} - metadata))}')
            return
        if is_meta(title):
            raise ValueError(f'标注节点（pc/rc/tag）不能出现在用例之外：{title[:40]}')
        module_count += 1
        if strict and not node['children']:
            raise ValueError(f'存在没有用例的空模块：{title[:40]}')
        if module_depth >= 8:
            raise ValueError(f'模块层级超过 8 层：{title[:40]}')
        for child in node['children']:
            walk(child, module_depth + 1)

    walk(root, 0)
    if strict and case_count == 0:
        raise ValueError('正式交付必须至少包含一条用例')
    return module_count, case_count, stats


def to_topic(node, is_root=False):
    topic = {'id': uuid.uuid4().hex, 'class': 'topic', 'title': node['title']}
    if is_root:
        topic['structureClass'] = 'org.xmind.ui.map.unbalanced'
    if node['children']:
        topic['children'] = {'attached': [to_topic(c) for c in node['children']]}
    return topic


def make_thumbnail():
    """生成合法的 1x1 白色 PNG，占位缩略图。"""
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
    return b'\x89PNG\r\n\x1a\n' + ihdr + idat + chunk(b'IEND', b'')


def build(root, out_path):
    sheet_id = uuid.uuid4().hex
    sheet = {
        'id': sheet_id,
        'class': 'sheet',
        'title': root['title'],
        'rootTopic': to_topic(root, is_root=True),
        'topicPositioning': 'fixed',
    }
    content = json.dumps([sheet], ensure_ascii=False, indent=1).encode('utf-8')
    metadata = json.dumps(
        {'creator': {'name': 'XMind', 'version': '12.0.2'}, 'activeSheetId': sheet_id},
        ensure_ascii=False).encode('utf-8')
    manifest = json.dumps(
        {'file-entries': {'content.json': {}, 'metadata.json': {},
                          'Thumbnails/thumbnail.png': {}}},
        ensure_ascii=False).encode('utf-8')

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('content.json', content)
        zf.writestr('metadata.json', metadata)
        zf.writestr('manifest.json', manifest)
        zf.writestr('Thumbnails/thumbnail.png', make_thumbnail())

    with zipfile.ZipFile(out_path) as zf:
        if zf.testzip() is not None:
            raise ValueError('XMind ZIP 完整性校验失败')
        back = json.loads(zf.read('content.json').decode('utf-8'))
        if back != [sheet]:
            raise ValueError('XMind 完整主题树回读不一致')
        saved_manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        if not set(saved_manifest['file-entries']).issubset(zf.namelist()):
            raise ValueError('XMind 缺少 manifest 声明的条目')
        if json.loads(zf.read('metadata.json').decode('utf-8'))['activeSheetId'] != sheet_id:
            raise ValueError('XMind 活动 Sheet 不一致')
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Build an XMind outline; no business or importer validation.')
    parser.add_argument('--strict', action='store_true', help='Require delivery fields and numbered steps.')
    parser.add_argument('outline')
    parser.add_argument('output')
    args = parser.parse_args()
    outline, out_path = args.outline, args.output
    if os.path.normcase(os.path.abspath(outline)) == os.path.normcase(os.path.abspath(out_path)):
        raise ValueError('输出路径不能覆盖输入大纲')
    root = load_outline(outline)
    module_count, case_count, stats = validate(root, strict=args.strict)
    build(root, out_path)
    print(f'BUILD OK -> {out_path}')
    print(f'  root        : {root["title"]}')
    print(f'  modules     : {module_count}')
    print(f'  cases       : {case_count} '
          f'(p0={stats["p0"]}, p1={stats["p1"]}, p2={stats["p2"]}, p3={stats["p3"]}, no-level={stats["none"]})')
    print(f'  steps+exp   : parsed and validated')
    print(f'VALIDATION MODE: {"strict" if args.strict else "basic"}')
    print('VERIFY OK: ZIP entries and complete topic tree round-trip verified')
    print('NOT VERIFIED: business coverage, test execution, MeterSphere import compatibility')
    return 0


if __name__ == '__main__':
    sys.exit(main())
