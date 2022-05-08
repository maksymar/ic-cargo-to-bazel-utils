#!/usr/bin/python3
import os
import copy
import toml
from pathlib import Path


def read(path):
    with open(path, 'r') as f:
        return f.read()


def build_graph(source_dir):
    # Collect Cargo.toml paths.
    data = [
        {
            'cargo_path': path,
            'cargo_toml': toml.loads(read(path)),
            'bazel_path': None,
        }
        for path in Path(source_dir).rglob('Cargo.toml')
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

    return graph


def mark_subtree(graph, current, target, path, is_found=False):
    info = graph.get(current)
    if info is None or info.get('traversing_status') == 'found':
        return
    path += [current]  # Add current to path.
    if info.get('traversing_status') == 'searching':
        raise ValueError(f'Unexpected graph cycle, see path: {path}')
    info['traversing_status'] = 'searching'
    is_found = is_found or current == target
    for child in info.get('children', []):
        mark_subtree(graph, child, target, path, is_found)
    info['traversing_status'] = 'found' if is_found else 'not-found'
    path.pop()         # Remove current from path.


def remove_unwanted_nodes(graph):
    subtree = {}
    for package_name in graph:
        if graph[package_name].get('traversing_status') != 'found':
            continue
        entry = copy.deepcopy(graph[package_name])
        del entry['traversing_status']
        subtree[package_name] = entry
    return subtree


def extract_subtree(graph, target_package):
    # Get roots.
    roots = set(graph.keys())
    for package_name in graph:
        for child in graph[package_name]['children']:
            roots.discard(child)

    # Link all the roots to a fake root.
    FAKE_ROOT = 'fake-root'
    graph[FAKE_ROOT] = {'children': roots}
    print(f'Root nodes linked to "{FAKE_ROOT}": {len(roots)}')

    if target_package is None or len(str(target_package).strip()) == 0:
        return graph

    # Extract target package subtree.
    path = []
    mark_subtree(graph, FAKE_ROOT, target_package, path)
    subtree = remove_unwanted_nodes(graph)

    return subtree


def calculate_progress(graph):
    bazel_n = sum([1 for x in graph if graph[x].get('bazel_path') is not None])
    total = len(graph.keys())
    ratio = bazel_n / total
    return (bazel_n, total, ratio)


def main():
    SOURCE_DIR = '../ic/rs/'
    ROOT_PACKAGE = None  # 'ic-types'

    graph = build_graph(SOURCE_DIR)
    subtree = extract_subtree(graph, ROOT_PACKAGE)
    bazel_n, total, ratio = calculate_progress(subtree)
    print(
        f'Packages converted to Bazel: {bazel_n} / {total} ({100*ratio:>5.01f}%)')


if __name__ == '__main__':
    main()
