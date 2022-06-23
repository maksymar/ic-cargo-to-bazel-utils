# ic-cargo-to-bazel-utils

## Goal

Help with Cargo-to-Bazel migration for the [Internet Computer](https://github.com/dfinity/ic) repository, namely with:

- understanding the progress
- optimizing the migration, by pointing to the next package for conversion
  - graph visualization
  - node height colors
    - `green` converted to Bazel
    - from `red` (leafs) to `yellow` (dependants) to be converted
  - parent count
  - CSV table with node height & parent count

## Usage

```bash
# Create folder for experiments
$ mkdir bazel-migration-order
$ cd bazel-migration-order

# Clone repositories
$ git clone git@github.com:dfinity/ic.git
$ git clone git@github.com:maksymar/ic-cargo-to-bazel-utils.git

# Run inspection
$ cd ic-cargo-to-bazel-utils
$ ./run_all.sh

# Inspect output:
Root package: all-dev
Packages with bazel / no bazel / total / progress: 169 / 185 / 354 /  47.7%

Root package: ic-execution-environment-dev
Packages with bazel / no bazel / total / progress: 87 / 17 / 104 /  83.7%

# Inspect CSV reports:
# ./output/all.csv
# ./output/all-dev.csv

# Inspect PDF charts:
# ./output/ic-execution-enviroment.gv.pdf
```

## Examples

### ic-ic00-types (no 3rd party dependencies)

![Example](./images/ic-ic00-types.png)

### ic-ic00-types (with 3rd party dependencies)
![Example](./images/ic-ic00-types-3p.png)

### ic-types
![Example](./images/ic-types.png)

### ic-metrics-[dev]
![Example](./images/ic-metrics-[dev].png)

### ic-execution-environment
![Example](./images/ic-execution-environment.png)
