#!/usr/bin/python3
import bazel
import unittest


class TestBazel(unittest.TestCase):

    def test_upper(self):
        text = '''
load("@rules_rust//rust:defs.bzl", "rust_library", "rust_test")

filegroup(
    name = "sources",
    srcs = glob(
        ["**"],
        exclude = ["target/**"],
    ),
    visibility = ["//visibility:public"],
)

rust_binary(
    name = "log_analyzer_bench",
    srcs = ["benches/speed.rs"],
    edition = "2018",
    deps = [
        ":log_analyzer",
        "@crate_index//:criterion",
    ],
)

rust_library(
    name = "der_utils",
    srcs = glob(["src/**"]),
    crate_name = "ic_crypto_internal_threshold_sig_bls12381_der",
    edition = "2018",
)

rust_test(
    name = "der_utils_test",
    crate = ":der_utils",
)

rust_test_suite(
    name = "tests",
    srcs = glob(["tests/**"]),
    edition = "2018",
    deps = [
        ":log_analyzer",
        "@crate_index//:chrono",
        "@crate_index//:lazy_static",
        "@crate_index//:regex",
    ],
)
'''
        self.assertEqual(bazel.loads(text), [
            {
                'rule': 'rust_binary',
                'name': 'log_analyzer_bench',
            },
            {
                'rule': 'rust_library',
                'name': 'der_utils',
                'crate_name': 'ic_crypto_internal_threshold_sig_bls12381_der',
            },
            {
                'rule': 'rust_test',
                'name': 'der_utils_test',
                'crate': ':der_utils',
            },
            {
                'rule': 'rust_test_suite',
                'name': 'tests',
            }
        ])


if __name__ == '__main__':
    unittest.main()
