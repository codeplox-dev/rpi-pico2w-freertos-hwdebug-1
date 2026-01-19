#!/usr/bin/env bash
# Run C++ linters (cppcheck, clang-tidy)

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Running cppcheck..."
cppcheck --enable=warning,style,performance --error-exitcode=1 \
    --suppress=missingIncludeSystem \
    -I src src/*.cpp src/*.hpp 2>&1 || true

echo ""
echo "Running clang-tidy..."
clang-tidy src/*.cpp src/*.hpp \
    --checks='-*,readability-*,bugprone-*,modernize-*,performance-*' \
    --warnings-as-errors='' \
    -- -std=c++17 -I src 2>&1 || true
