#!/usr/bin/python3
import os
import csv
import copy
import toml
import graphviz
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
        if graph[package_name].get('traversing_status') == 'found':
            subtree[package_name] = copy.deepcopy(graph[package_name])
            del subtree[package_name]['traversing_status']
    return subtree


def extract_subtree(graph, target_package):
    # Get roots.
    roots = set(graph.keys())
    for package_name in graph:
        for child in graph[package_name]['children']:
            roots.discard(child)

    # Link all the roots to a fake root.
    FAKE_ROOT = 'none'
    graph[FAKE_ROOT] = {'children': roots}
    print(f'Root nodes linked to "{FAKE_ROOT}": {len(roots)}')

    if target_package is None or len(str(target_package).strip()) == 0:
        # Add extra fake root for 'target_package' entry point.
        graph[target_package] = graph[FAKE_ROOT]
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


def add_height(graph, current):
    info = graph.get(current)
    height = -1
    # Skip packages with Bazel.
    if info is None or info.get('bazel_path') is not None:
        return height
    for child in info.get('children', []):
        height = max(height, add_height(graph, child))
    info['height'] = height + 1
    return info['height']


def add_parent_count(graph):
    # Count number of parents for each child.
    counter = {}
    for parent in graph:
        for child in graph[parent].get('children', []):
            if counter.get(child) is None:
                counter[child] = 0
            counter[child] += 1
    # Add parent count data to each node.
    for project_name in graph:
        graph[project_name]['parent_count'] = counter.get(project_name, 0)


def interpolate_rgb(rgb_lo, rgb_hi, param):
    def interpolate(a, b, param):
        return int(a * (1 - param) + b * param)

    r = interpolate(rgb_lo[0], rgb_hi[0], param)
    g = interpolate(rgb_lo[1], rgb_hi[1], param)
    b = interpolate(rgb_lo[2], rgb_hi[2], param)
    return f'#{r:02X}{g:02X}{b:02X}'


def add_height_color(graph, color_lo, color_hi):
    max_height = max([graph[x].get('height', -1) for x in graph])
    if max_height is None or max_height <= 0:
        return
    for package_name in graph:
        info = graph[package_name]
        height = info.get('height')
        if height is None:
            continue
        param = height / max_height
        info['color'] = interpolate_rgb(color_lo, color_hi, param)


def to_graphviz(graph):
    nodes_n = len(graph.keys())
    edges_n = sum([len(graph[x].get('children', [])) for x in graph])
    print(f'Plotting {nodes_n} nodes with {edges_n} edges...')

    dot = graphviz.Digraph()

    # Create nodes.
    for package_name in graph.keys():
        node_text = f'{package_name}'
        fillcolor = 'grey'  # default

        # Display height.
        height = graph[package_name].get('height')
        if height is not None:
            node_text += f'\nheight:{height}'

        # Display parent count.
        parents = graph[package_name].get('parent_count')
        if parents is not None:
            node_text += f'\nparents:{parents}'

        # Display bazel status and color.
        bazel_path = graph[package_name].get('bazel_path')
        if bazel_path:
            node_text += f'\nbazel:yes'
            fillcolor = 'green'

        # Display not converted node color.
        color = graph[package_name].get('color')
        if color is not None:
            #node_text += f'\ncolor:{color}'
            fillcolor = color

        dot.node(package_name, node_text, style='filled', fillcolor=fillcolor)

    # Create edges.
    for package_name in graph.keys():
        for child in graph[package_name].get('children', []):
            dot.edge(package_name, child)

    # print(dot.source)  # DEBUG
    return dot


def write_csv(graph, path):
    # Generate table.
    data = []
    for package_name in graph:
        info = graph[package_name]
        data.append({
            'name': package_name,
            'bazel': 'yes' if info.get('bazel_path') else 'no',
            'height': info.get('height'),
            'parents': info.get('parent_count'),
        })
    # Sort by parents (desc).
    data = sorted(data, key=lambda x: x['parents'], reverse=True)
    # Sort by height (asc, empty at the bottom).
    data = sorted(
        data, key=lambda x: 1000 if x['height'] is None else x['height'], reverse=False)
    # Write to file.
    with open(path, 'w+') as f:
        columns = data[0].keys()
        writer = csv.DictWriter(f, columns)
        writer.writeheader()
        writer.writerows(data)


def main():
    SOURCE_DIR = '../ic/rs/'
    ROOT_PACKAGE = 'none'  # 'none' for all the packages
    #ROOT_PACKAGE = 'ic-types'
    #ROOT_PACKAGE = 'ic-execution-environment'
    GRAPH_FILES = './output/graph.gv'
    CSV_FILE = './output/packages.csv'

    graph = build_graph(SOURCE_DIR)
    subtree = extract_subtree(graph, ROOT_PACKAGE)
    bazel_n, total, ratio = calculate_progress(subtree)
    print(
        f'Packages converted to Bazel: {bazel_n} / {total} ({100*ratio:>5.01f}%)')

    add_height(subtree, ROOT_PACKAGE)
    RED = (255, 0, 0)
    YELLOW = (255, 255, 0)
    add_height_color(subtree, RED, YELLOW)
    add_parent_count(subtree)

    write_csv(subtree, CSV_FILE)

    dot = to_graphviz(subtree)
    dot.render(GRAPH_FILES, view=True)


if __name__ == '__main__':
    main()
