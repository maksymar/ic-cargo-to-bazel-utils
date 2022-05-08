#!/usr/bin/python3
import os
import copy
import toml
import graphviz
from pathlib import Path


def read(path):
    with open(path, 'r') as f:
        return f.read()


def build_graph(source_folder):
    # Collect Cargo.toml paths.
    data = [
        {
            'cargo_path': path,
            'cargo_toml': toml.loads(read(path)),
            'bazel_path': None,
        }
        for path in Path(source_folder).rglob('Cargo.toml')
    ]

    # Collect BUILD.bazel paths.
    for entry in data:
        path = str(entry['cargo_path']).replace('Cargo.toml', 'BUILD.bazel')
        if os.path.exists(path):
            entry['bazel_path'] = path

    # Build graph.
    graph = {}
    for entry in data:
        info = entry.get('cargo_toml', {})
        package_name = info.get('package', {}).get('name', '')
        # Skip packages without 'ic-*' prefix.
        if not package_name.startswith('ic-'):
            continue
        children = info.get('dependencies', {}).keys()
        # Skip dependencies without 'ic-*' prefix.
        children = [x for x in children if x.startswith('ic-')]
        children = sorted(children, reverse=False)  # Stabilaze data.
        graph[package_name] = {
            'bazel_path': entry.get('bazel_path'),
            'children': children,
        }

    # Get roots.
    roots = set(graph.keys())
    for package_name in graph:
        for child in graph[package_name]['children']:
            roots.discard(child)

    # Link all the roots to a fake root.
    FAKE_ROOT = 'fake-root'
    graph[FAKE_ROOT] = {'children': roots}
    print(f'Root nodes linked to "{FAKE_ROOT}": {len(roots)}')

    return graph


def main():
    ROOT = '../ic/rs/'

    graph = build_graph(ROOT)
    # print(graph)


if __name__ == '__main__':
    main()
