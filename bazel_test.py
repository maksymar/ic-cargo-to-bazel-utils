#!/usr/bin/python3
import bazel
import unittest


class TestBazel(unittest.TestCase):

    def test_loads(self):
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

rust_proc_macro(
    name = "fe-derive",
    srcs = glob(["src/**"]),
    crate_name = "fe_derive",
    edition = "2018",
    deps = [
        "@crate_index//:hex",
        "@crate_index//:num-bigint-dig",
    ],
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

rust_test(
    name = "sha224_test",
    srcs = ["tests/sha224.rs"],
    edition = "2018",
    deps = [
        ":sha",
        "@crate_index//:openssl",
    ],
)

rust_canister(
    name = "ecdsa-canister",
    srcs = ["src/main.rs"],
    deps = DEPENDENCIES,
)
'''
        self.assertEqual(bazel.loads(text), [
            {
                'rule': 'filegroup',
                'name': 'sources',
            },
            {
                'rule': 'rust_binary',
                'name': 'log_analyzer_bench',
                'srcs': '["benches/speed.rs"]',
            },
            {
                'rule': 'rust_library',
                'name': 'der_utils',
                'srcs': 'glob(["src/**"])',
                'crate_name': 'ic_crypto_internal_threshold_sig_bls12381_der',
            },
            {
                'rule': 'rust_proc_macro',
                'name': 'fe-derive',
                'srcs': 'glob(["src/**"])',
                'crate_name': 'fe_derive',
            },
            {
                'rule': 'rust_test',
                'name': 'der_utils_test',
                'crate': ':der_utils',
            },
            {
                'rule': 'rust_test_suite',
                'name': 'tests',
                'srcs': 'glob(["tests/**"])',
            },
            {
                'rule': 'rust_test',
                'name': 'sha224_test',
                'srcs': '["tests/sha224.rs"]',
            },
            {
                'rule': 'rust_canister',
                'name': 'ecdsa-canister',
                'srcs': '["src/main.rs"]',
            }
        ])

    def test_is_bazelized_bin_or_lib_name(self):
        crate = 'phantom_newtype'
        data = bazel.loads('''
rust_library(
    name = "phantom_newtype",
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertFalse(bazel.is_bazelized_test(crate, data))

    def test_is_bazelized_bin_or_lib_crate_name(self):
        crate = 'ic-crypto-internal-threshold-sig-bls12381-der'
        data = bazel.loads('''
rust_library(
    name = "der_utils",
    crate_name = "ic_crypto_internal_threshold_sig_bls12381_der",
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertFalse(bazel.is_bazelized_test(crate, data))

    def test_is_bazelized_rust_canister(self):
        crate = 'ecdsa-canister'
        data = bazel.loads('''
rust_canister(
    name = "ecdsa-canister",
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertFalse(bazel.is_bazelized_test(crate, data))

    def test_is_bazelized_test(self):
        crate = 'ic-crypto-internal-bls12381-serde-miracl'
        data = bazel.loads('''
rust_library(
    name = "miracl",
    crate_name = "ic_crypto_internal_bls12381_serde_miracl",
)

rust_test(
    name = "miracl_test",
    crate = ":miracl",
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertTrue(bazel.is_bazelized_test(crate, data))

    def test_is_bazelized_integration_test_glob(self):
        crate = 'ic-cycles-account-manager'
        data = bazel.loads('''
rust_library(
    name = "cycles_account_manager",
    crate_name = "ic_cycles_account_manager",
)

rust_test(
    name = "cycles_account_manager_integration_tests",
    srcs = glob(["tests/**/*.rs"]),
    edition = "2018",
    deps = [":cycles_account_manager"] + DEPENDENCIES + DEV_DEPENDENCIES,
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertTrue(bazel.is_bazelized_test(crate, data))

    def test_is_bazelized_integration_test(self):
        crate = 'ic-crypto-sha'
        data = bazel.loads('''
rust_library(
    name = "sha",
    srcs = glob(["src/**"]),
    crate_name = "ic_crypto_sha",
    edition = "2018",
    deps = ["//rs/crypto/internal/crypto_lib/sha2"],
)

rust_test(
    name = "sha224_test",
    srcs = ["tests/sha224.rs"],
    edition = "2018",
    deps = [
        ":sha",
        "@crate_index//:openssl",
    ],
)
''')
        self.assertTrue(bazel.is_bazelized_bin_or_lib(crate, data))
        self.assertTrue(bazel.is_bazelized_test(crate, data))


if __name__ == '__main__':
    unittest.main()
