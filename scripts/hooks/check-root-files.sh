#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

# 금지 패턴: 루트에 남으면 안 되는 파일들 (필요시 추가)
forbidden=(
  "debug_*.py"
  "test_*.py"
  "*.log"
  "*validation*.json"
)

violations=()
for pattern in "${forbidden[@]}"; do
  while IFS= read -r -d '' f; do
    # 허용 목록 예외 처리
    case "$f" in
      ./tests/*|./scripts/*|./logs/*|./reports/*|./docs/*|./app/*|./monitoring/*|./nginx/*)
        continue;;
    esac
    violations+=("$f")
  done < <(find . -maxdepth 1 -type f -name "$pattern" -print0)
done

if [ ${#violations[@]} -gt 0 ]; then
  echo "[ERROR] 루트에 정리되지 않은 파일이 있습니다:" >&2
  for v in "${violations[@]}"; do echo " - $v" >&2; done
  echo "\n해당 파일을 적절한 디렉토리로 이동하세요 (scripts/, logs/, reports/ 등)." >&2
  exit 1
fi

exit 0


