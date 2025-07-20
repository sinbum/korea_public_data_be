#!/bin/bash

# 볼륨 초기화 스크립트
# 필요한 디렉토리와 권한 설정

set -e

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 볼륨 초기화 시작...${NC}"

# 필요한 디렉토리 생성
echo -e "${YELLOW}📁 디렉토리 생성 중...${NC}"

DIRECTORIES=(
    "volumes/mongodb/data"
    "volumes/mongodb/config"
    "volumes/mongodb/init"
    "volumes/redis/data"
    "volumes/redis/config"
    "volumes/backups/mongodb"
    "volumes/backups/redis"
    "volumes/logs"
    "volumes/uploads"
    "volumes/tmp"
)

for dir in "${DIRECTORIES[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✅ 생성됨: $dir${NC}"
    else
        echo -e "${BLUE}ℹ️  이미 존재: $dir${NC}"
    fi
done

# 권한 설정 (Linux/macOS)
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}🔐 권한 설정 중...${NC}"
    
    # MongoDB 권한 (999:999는 MongoDB 컨테이너의 기본 UID:GID)
    sudo chown -R 999:999 volumes/mongodb/ 2>/dev/null || {
        echo -e "${YELLOW}⚠️  MongoDB 권한 설정 실패 (sudo 권한 필요)${NC}"
        echo -e "${BLUE}💡 수동으로 실행하세요: sudo chown -R 999:999 volumes/mongodb/${NC}"
    }
    
    # Redis 권한 (999:1000은 Redis 컨테이너의 기본 UID:GID)
    sudo chown -R 999:1000 volumes/redis/ 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Redis 권한 설정 실패 (sudo 권한 필요)${NC}"
        echo -e "${BLUE}💡 수동으로 실행하세요: sudo chown -R 999:1000 volumes/redis/${NC}"
    }
    
    # 애플리케이션 디렉토리 권한
    chmod -R 755 volumes/logs volumes/uploads volumes/tmp volumes/backups 2>/dev/null || true
fi

# Redis 설정 파일이 없으면 기본 설정 생성
if [ ! -f "volumes/redis/redis.conf" ]; then
    echo -e "${YELLOW}📝 Redis 설정 파일 생성 중...${NC}"
    cat > volumes/redis/redis.conf << 'EOF'
# Redis 기본 설정
port 6379
bind 0.0.0.0
protected-mode no
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
loglevel notice
timeout 300
tcp-keepalive 300
tcp-backlog 511
EOF
    echo -e "${GREEN}✅ Redis 설정 파일 생성 완료${NC}"
fi

# MongoDB 초기화 스크립트가 없으면 생성
if [ ! -f "volumes/mongodb/init/init.js" ]; then
    echo -e "${YELLOW}📝 MongoDB 초기화 스크립트 생성 중...${NC}"
    # 이미 생성되었으므로 스킵
    echo -e "${GREEN}✅ MongoDB 초기화 스크립트 이미 존재${NC}"
fi

# .gitignore에 볼륨 데이터 추가
echo -e "${YELLOW}📝 .gitignore 업데이트 중...${NC}"
cat >> .gitignore << 'EOF'

# 볼륨 데이터 (로컬 관리)
volumes/mongodb/data/
volumes/redis/data/
volumes/logs/*.log
volumes/tmp/*
volumes/uploads/*
!volumes/mongodb/init/
!volumes/redis/redis.conf
EOF

echo -e "${GREEN}✅ .gitignore 업데이트 완료${NC}"

# README 파일에 볼륨 정보 추가할지 확인
if ! grep -q "volumes/" README.md 2>/dev/null; then
    echo -e "${YELLOW}📝 README.md에 볼륨 정보를 추가하시겠습니까? (y/N): ${NC}"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat >> README.md << 'EOF'

## 📁 볼륨 관리

### 볼륨 구조
```
volumes/
├── mongodb/           # MongoDB 데이터
│   ├── data/         # 데이터베이스 파일
│   ├── config/       # 설정 파일
│   └── init/         # 초기화 스크립트
├── redis/            # Redis 데이터
│   ├── data/         # Redis 데이터 파일
│   └── redis.conf    # Redis 설정
├── backups/          # 백업 파일
│   ├── mongodb/      # MongoDB 백업
│   └── redis/        # Redis 백업
├── logs/             # 애플리케이션 로그
├── uploads/          # 업로드된 파일
└── tmp/              # 임시 파일
```

### 볼륨 관리 명령어
```bash
# 볼륨 초기화
./scripts/init-volumes.sh

# 데이터 백업
./scripts/backup.sh

# 데이터 복원
./scripts/restore.sh mongodb 20240301_143000
./scripts/restore.sh redis 20240301_143000
```
EOF
        echo -e "${GREEN}✅ README.md 업데이트 완료${NC}"
    fi
fi

# 스크립트 실행 권한 부여
echo -e "${YELLOW}🔐 스크립트 실행 권한 설정 중...${NC}"
chmod +x scripts/*.sh 2>/dev/null || true

# 완료 메시지
echo -e "${GREEN}🎉 볼륨 초기화 완료!${NC}"
echo -e "${BLUE}📋 다음 단계:${NC}"
echo -e "  1. ${YELLOW}docker-compose up -d${NC} - 서비스 시작"
echo -e "  2. ${YELLOW}./scripts/backup.sh${NC} - 정기 백업"
echo -e "  3. ${YELLOW}docker-compose logs -f api${NC} - 로그 확인"
echo ""
echo -e "${BLUE}📊 볼륨 현황:${NC}"
du -sh volumes/* 2>/dev/null || echo "볼륨 데이터 없음"