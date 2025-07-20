#!/bin/bash

# 백업 스크립트
# MongoDB와 Redis 데이터를 백업

set -e

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 현재 날짜와 시간
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./volumes/backups"

echo -e "${GREEN}🔄 백업 시작: $TIMESTAMP${NC}"

# MongoDB 백업
echo -e "${YELLOW}📊 MongoDB 백업 중...${NC}"
if docker-compose exec -T mongodb mongodump --host localhost --port 27017 --db korea_public_api --out /backups/mongodb_$TIMESTAMP; then
    echo -e "${GREEN}✅ MongoDB 백업 완료: mongodb_$TIMESTAMP${NC}"
else
    echo -e "${RED}❌ MongoDB 백업 실패${NC}"
    exit 1
fi

# Redis 백업
echo -e "${YELLOW}🔴 Redis 백업 중...${NC}"
if docker-compose exec -T redis redis-cli BGSAVE; then
    # RDB 파일 복사
    docker-compose exec -T redis cp /data/dump.rdb /data/dump_$TIMESTAMP.rdb
    docker cp korea_redis:/data/dump_$TIMESTAMP.rdb $BACKUP_DIR/redis_$TIMESTAMP.rdb
    echo -e "${GREEN}✅ Redis 백업 완료: redis_$TIMESTAMP.rdb${NC}"
else
    echo -e "${RED}❌ Redis 백업 실패${NC}"
    exit 1
fi

# 백업 파일 목록 출력
echo -e "${GREEN}📁 백업 파일 목록:${NC}"
ls -la $BACKUP_DIR/ | grep $TIMESTAMP

# 오래된 백업 파일 정리 (30일 이상)
echo -e "${YELLOW}🧹 오래된 백업 파일 정리 중...${NC}"
find $BACKUP_DIR -name "*_*" -type f -mtime +30 -delete 2>/dev/null || true
find $BACKUP_DIR -name "mongodb_*" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true

echo -e "${GREEN}✅ 백업 완료!${NC}"