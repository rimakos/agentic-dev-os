#!/bin/sh
# Run every test suite from any folder: sh tests/run.sh
# Each Python folder is its own discovery root, so a folder needs no __init__.py and may have a dash in its name.
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
failed=0
for folder in tests/*/; do
  ls "$folder"test_*.py >/dev/null 2>&1 || continue
  echo "== $folder"
  python3 -m unittest discover -s "$folder" -p 'test_*.py' || failed=1
done
if [ -d tests/guard ] && node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 18) ? 0 : 1)' 2>/dev/null; then
  echo "== tests/guard/"
  node --test 'tests/guard/*.test.ts' || failed=1
else
  echo "== tests/guard/ skipped (needs the folder and Node >= 22.18)"
fi
exit $failed
