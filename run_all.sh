#!/bin/bash

SOURCE_DIR=../ic/rs
OUTPUT_DIR=./output
GRAPHVIZ_VIEW=no      # yes/no
IC_PACKAGES_ONLY=yes  # yes/no

# All
PACKAGE=all
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --ic_only ${IC_PACKAGES_ONLY}

# ic-execution-environment
PACKAGE=ic-execution-environment
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --ic_only ${IC_PACKAGES_ONLY}

# ic-types
PACKAGE=ic-types
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --ic_only ${IC_PACKAGES_ONLY}
