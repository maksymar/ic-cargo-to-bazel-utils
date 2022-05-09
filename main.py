#!/usr/bin/python3
import os
import csv
import copy
import toml
import argparse
import graphviz
from pathlib import Path


FAKE_ROOT = 'fake-root'
RED = (255, 0, 0)
YELLOW = (255, 255, 0)


def read(path):
    with open(path, 'r') as f:
        return f.read()


def build_graph(source_dir, ic_packages_only=True):
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
        if ic_packages_only and not package_name.startswith('ic-'):
            continue
        children = info.get('dependencies', {}).keys()
        # Skip dependencies without 'ic-*' prefix.
        if ic_packages_only:
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
    graph[FAKE_ROOT] = {'children': roots}
    print(f'Root nodes linked to "{FAKE_ROOT}": {len(roots)}')

    all_packages_keywords = [
        'None',
        'none',
        'default',
        '.',
        'all',
        '',
    ]
    if str(target_package).strip() in all_packages_keywords:
        return graph

    # Extract target package subtree.
    path = []
    mark_subtree(graph, FAKE_ROOT, target_package, path)
    subtree = remove_unwanted_nodes(graph)
    subtree[FAKE_ROOT] = {'children': [target_package]}

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
    result = height + 1
    # Skip fake root node.
    if current != FAKE_ROOT:
        info['height'] = result
    return result


def add_parent_count(graph):
    # Count number of parents for each child.
    counter = {}
    for parent in graph:
        for child in graph[parent].get('children', []):
            if counter.get(child) is None:
                counter[child] = 0
            counter[child] += 1
    # Add parent count data to each node.
    for package_name in graph:
        # Skip fake root node.
        if package_name == FAKE_ROOT:
            continue
        graph[package_name]['parent_count'] = counter.get(package_name, 0)


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
        # Skip fake root node.
        if package_name == FAKE_ROOT:
            continue

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
        # Skip fake root node.
        if package_name == FAKE_ROOT:
            continue
        for child in graph[package_name].get('children', []):
            dot.edge(package_name, child)

    # print(dot.source)  # DEBUG
    return dot


def write_csv(graph, path):
    # Generate table.
    data = []
    for package_name in graph:
        # Skip fake root node.
        if package_name == FAKE_ROOT:
            continue
        info = graph[package_name]
        data.append({
            'name': package_name,
            'bazel': 'yes' if info.get('bazel_path') else 'no',
            'height': info.get('height'),
            'parents': info.get('parent_count'),
        })
    # Sort by parents (desc).
    data = sorted(data, key=lambda x: x['parents']
                  if x['parents'] is not None else 0, reverse=True)
    # Sort by height (asc, empty at the bottom).
    MAX_HEIGHT = 1000*1000*1000
    data = sorted(
        data, key=lambda x: x['height'] if x['height'] is not None else MAX_HEIGHT, reverse=False)
    # Write to file.
    with open(path, 'w+') as f:
        columns = data[0].keys()
        writer = csv.DictWriter(f, columns)
        writer.writeheader()
        writer.writerows(data)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main():
    # Parse agruments.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-sd', '--source_dir', help='source directory', default='../ic/rs/')
    parser.add_argument('-rp', '--root_package',
                        help='root package', default=None)
    parser.add_argument(
        '-gp', '--graphviz_path', help='graphviz output files', default='./output/graph.gv')
    parser.add_argument(
        '-gv', '--graphviz_view', help='graphviz view', type=str2bool, default=False)
    parser.add_argument(
        '-csv', '--csv_path', help='CSV output file', default='./output/packages.csv')
    parser.add_argument(
        '-ic', '--ic_only', help='show only packages with "ic-" prefix', type=str2bool, default=True)
    args = parser.parse_args()

    # Generate graph of package dependencies.
    graph = build_graph(args.source_dir, ic_packages_only=args.ic_only)
    subtree = extract_subtree(graph, args.root_package)
    bazel_n, total, ratio = calculate_progress(subtree)
    print(
        f'Packages converted to Bazel: {bazel_n} / {total} ({100*ratio:>5.01f}%)')

    # Calculate attributes (height, parents, color).
    add_height(subtree, FAKE_ROOT)
    add_height_color(subtree, RED, YELLOW)
    add_parent_count(subtree)

    # Write CSV output.
    write_csv(subtree, args.csv_path)

    # Generate Graphviz.
    dot = to_graphviz(subtree)
    dot.render(args.graphviz_path, view=args.graphviz_view)


if __name__ == '__main__':
    main()
