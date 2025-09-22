#!/bin/bash
# cppforge-sync
set -e
set -o pipefail
set -x

cmake $(dirname $(realpath $0))/..
cmake --build . -j --verbose --target package
ctest --output-on-failure