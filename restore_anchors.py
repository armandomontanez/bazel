#!/usr/bin/env python3
"""Restore custom heading anchors from .md source docs to their .mdx counterparts.

Reads anchors in {:#anchor-name} format from site/en/**/*.md files and applies
them as {#anchor-name} to the corresponding docs/**/*.mdx files.
"""

import argparse
from collections import defaultdict
import os
import re
import sys
from pathlib import Path

ANCHOR_RE = re.compile(r'^(#+\s+.+?)\s+\{:#([^}]+)\}\s*$')


def _extract_anchors(md_path):
    """Return a list of (heading_text, anchor_id) from a .md file."""
    anchors = []
    with open(md_path, encoding='utf-8') as f:
        for line in f:
            m = ANCHOR_RE.match(line)
            if m:
                anchors.append((m.group(1).rstrip(), m.group(2)))
    return anchors


def _normalize_heading(text):
    """Strip differing content for comparison."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'{{[^}]+}}', '', text)
    return re.sub(r'^#+\s+', '', text).strip()


def _parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--src-md-root',
        type=Path,
        default=Path('site/en'),
    )
    parser.add_argument(
        '--dest-mdx-root',
        type=Path,
        default=Path('docs'),
    )
    return parser.parse_args()


def _apply_anchors(mdx_path, anchors):
    """Add {#anchor} to matching headings in an .mdx file. Returns count of changes."""
    with open(mdx_path, encoding='utf-8') as f:
        lines = f.readlines()

    anchor_map = defaultdict(list)
    for heading_text, anchor_id in anchors:
        key = _normalize_heading(heading_text)
        anchor_map[key].append(anchor_id)

    changed = 0
    new_lines = []
    for line in lines:
        heading_match = re.match(r'^(#+\s+)(.+?)\s*$', line)
        if heading_match:
            prefix = heading_match.group(1)
            rest = heading_match.group(2).strip()
            if re.search(r'\{#[^}]+\}', rest):
                new_lines.append(line)
                continue
            key = _normalize_heading(rest)
            if key in anchor_map:
                new_lines.append(f'{prefix}{rest} {{#{anchor_map[key].pop(0)}}}\n')
                changed += 1
                continue
        new_lines.append(line)

    if changed:
        with open(mdx_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return changed, sum((len(v) for v in anchor_map.values()))


def main(src_md_root: Path, dest_mdx_root: Path):
    if not src_md_root.is_dir() or not dest_mdx_root.is_dir():
        print(
            f'Error: run from the bazel repo root (expected {src_md_root}/ and {dest_mdx_root}/)',
            file=sys.stderr,
        )
        sys.exit(1)

    total_files = 0
    total_restored = 0
    total_unmatched = 0

    for md_path in sorted(src_md_root.rglob('*.md')):
        anchors = _extract_anchors(md_path)
        if not anchors:
            continue

        rel = md_path.relative_to(src_md_root).with_suffix('.mdx')
        mdx_path = dest_mdx_root / rel

        if not mdx_path.exists():
            print(f'  skip (no .mdx): {md_path}')
            continue

        restored, unmatched = _apply_anchors(mdx_path, anchors)
        total_files += 1
        total_restored += restored
        total_unmatched += unmatched

        status = f'{restored} restored'
        if unmatched:
            status += f', {unmatched} unmatched'
        print(f'  {rel}: {status}')

    print(f'\n{total_files} files processed, {total_restored} anchors restored, {total_unmatched} unmatched')


if __name__ == '__main__':
    main(**vars(_parse_arguments()))
