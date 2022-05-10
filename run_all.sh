#!/bin/bash

SOURCE_DIR=../ic/rs
OUTPUT_DIR=./output
GRAPHVIZ_VIEW=no    # yes/no
SKIP_3RD_PARTY=yes  # yes/no

# All
PACKAGE=all
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --skip_3rd_party ${SKIP_3RD_PARTY}

# ic-execution-environment
PACKAGE=ic-execution-environment
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --skip_3rd_party ${SKIP_3RD_PARTY}

# ic-types
PACKAGE=ic-types
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --skip_3rd_party ${SKIP_3RD_PARTY}

# ic-ic00-types
PACKAGE=ic-ic00-types
./main.py \
  --source_dir ${SOURCE_DIR} \
  --root_package ${PACKAGE} \
  --csv_path ${OUTPUT_DIR}/${PACKAGE}.csv \
  --graphviz_path ${OUTPUT_DIR}/${PACKAGE}.gv \
  --graphviz_view ${GRAPHVIZ_VIEW} \
  --skip_3rd_party ${SKIP_3RD_PARTY}
