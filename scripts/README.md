Scripts directory

이 디렉토리는 루트에 흩어져 있던 스크립트들을 목적별로 정리합니다.

구조
- scripts/python/: 일반 파이썬 스크립트
- scripts/python/experiments/: 실험/프로토타입 성격의 스크립트
- scripts/hooks/: Git hooks 및 정적 점검 스크립트

실행 예시
```bash
python3 scripts/python/debug_current_api.py
python3 scripts/python/experiments/test_data_transformation.py
```

Pre-commit 연동(선택)
루트에 산재 파일이 다시 생기는 것을 방지하기 위해 pre-commit 훅을 제공합니다.

1) 설치
```bash
pip install pre-commit
pre-commit install
```

2) 커스텀 훅은 .pre-commit-config.yaml에서 scripts/hooks/check-root-files.sh 를 호출합니다.
커밋 시 루트에 금지된 패턴의 파일이 있으면 실패합니다.


