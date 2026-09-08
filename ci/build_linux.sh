#!/bin/bash
# cppforge-sync
set -e
set -o pipefail
set -x

cmake $(dirname $(realpath $0))/..
# Building with -j causes devops agents to run out of memory
cmake --build . -j8 --verbose --target package
ctest --output-on-failure --repeat until-fail:10