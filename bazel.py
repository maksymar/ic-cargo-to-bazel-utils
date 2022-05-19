#!/usr/bin/python3
import re


NAME = re.compile('\s+name = "(.+)"')
CRATE_NAME = re.compile('\s+crate_name = "(.+)"')
CRATE = re.compile('\s+crate = "(.+)"')


def loads(text):
    lines = text.split('\n')

    result = []
    entry = {}
    for line in lines:
        if line == 'rust_library(':
            entry['rule'] = 'rust_library'
            continue

        if line == 'rust_binary(':
            entry['rule'] = 'rust_binary'
            continue

        if line == 'rust_test(':
            entry['rule'] = 'rust_test'
            continue

        if line == 'rust_test_suite(':
            entry['rule'] = 'rust_test_suite'
            continue

        if match := NAME.match(line):
            entry['name'] = match.group(1)
            continue

        if match := CRATE_NAME.match(line):
            entry['crate_name'] = match.group(1)
            continue

        if match := CRATE.match(line):
            entry['crate'] = match.group(1)
            continue

        if line == ')':
            if entry.get('rule') in ['rust_library', 'rust_binary', 'rust_test', 'rust_test_suite']:
                result.append(entry)

            entry = {}
            continue

    return result
