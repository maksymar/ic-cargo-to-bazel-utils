#!/usr/bin/python3
import os
import csv
import copy
import toml
import bazel
import argparse
import graphviz
from pathlib import Path


FAKE_ROOT = 'fake-root'
RED = (255, 0, 0)
YELLOW = (255, 255, 0)


def read(path):
    with open(path, 'r') as f:
        return f.read()


def dev_name(name):
    return f'{name}-[dev]'


def build_graph(source_dir, skip_3rd_party, dev_dependencies):
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
            entry['build_bazel'] = bazel.loads(read(path))

    # Collect all package names.
    if skip_3rd_party:
        packages = [
            x.get('cargo_toml', {}).get('package', {}).get('name')
            for x in data
        ]
        packages = set([x for x in packages if x is not None])

    # Build graph.
    graph = {}
    for entry in data:
        info = entry.get('cargo_toml', {})
        package_name = info.get('package', {}).get('name')
        if package_name is None:
            continue

        build_bazel = entry.get('build_bazel', [])

        children = list(info.get('dependencies', {}).keys())
        # Skip 3rd party package dependencies.
        if skip_3rd_party:
            children = [x for x in children if x in packages]
        children = sorted(children, reverse=False)  # Stabilaze data.
        graph[package_name] = {
            'bazelized': bazel.is_bazelized_bin_or_lib(package_name, build_bazel),
            'children': children,
        }

        children_dev = list(info.get('dev-dependencies', {}).keys())
        if dev_dependencies and len(children_dev) > 0:
            # Skip 3rd party package dependencies.
            if skip_3rd_party:
                children_dev = [x for x in children_dev if x in packages]
            # Stabilaze data.
            children_dev = sorted(children_dev, reverse=False)
            package_name_dev = dev_name(package_name)
            graph[package_name_dev] = {
                'bazelized': bazel.is_bazelized_test(package_name, build_bazel),
                'children': children_dev,
            }
            graph[package_name_dev]['children'] += [package_name]

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
    # Add dev-node on top if exists.
    new_root = dev_name(target_package)
    if graph.get(new_root) is not None:
        target_package = new_root

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

    # Add fake root to a subtree.
    subtree[FAKE_ROOT] = {'children': [target_package]}

    return subtree


def calculate_progress(graph):
    bazel_n = sum([1 for x in graph if graph[x].get('bazelized') is True])
    total = len(graph.keys())
    ratio = bazel_n / total
    return (bazel_n, total, ratio)


def add_height(graph, current):
    info = graph.get(current)
    height = -1
    # Skip packages with Bazel.
    if info is None or info.get('bazelized', False):
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
    for package_name in graph:
        # Skip fake root node.
        if package_name == FAKE_ROOT:
            continue
        for child in graph[package_name].get('children', []):
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
        if graph[package_name].get('bazelized'):
            node_text += f'\nbazel:yes'
            fillcolor = 'green'

        # Display not converted node color.
        color = graph[package_name].get('color')
        if color is not None:
            # node_text += f'\ncolor:{color}'
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
            'bazel': 'yes' if info.get('bazelized') else 'no',
            'height': info.get('height'),
            'parents': info.get('parent_count'),
        })
        # Sort by name (asc).
        data = sorted(data, key=lambda x: x['name'], reverse=False)
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
        '-s3p', '--skip_3rd_party', help='skip 3rd party package dependencies', type=str2bool, default=True)
    parser.add_argument(
        '-dev', '--dev_dependencies', help='show dev-dependencies', type=str2bool, default=True)
    args = parser.parse_args()

    # Generate graph of package dependencies.
    graph = build_graph(
        args.source_dir, skip_3rd_party=args.skip_3rd_party, dev_dependencies=args.dev_dependencies)
    subtree = extract_subtree(graph, args.root_package)
    print(f'Root package: {args.root_package}')

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
