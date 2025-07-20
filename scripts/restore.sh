#!/bin/bash

# 복원 스크립트
# 백업된 데이터를 복원

set -e

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKUP_DIR="./volumes/backups"

# 사용법 출력
usage() {
    echo "사용법: $0 [mongodb|redis] [백업_타임스탬프]"
    echo "예시: $0 mongodb 20240301_143000"
    echo "예시: $0 redis 20240301_143000"
    echo ""
    echo "사용 가능한 백업 목록:"
    ls -la $BACKUP_DIR/ | grep -E "(mongodb_|redis_)" || echo "백업 파일이 없습니다."
    exit 1
}

# 인자 확인
if [ $# -ne 2 ]; then
    usage
fi

TYPE=$1
TIMESTAMP=$2

case $TYPE in
    mongodb)
        BACKUP_PATH="$BACKUP_DIR/mongodb_$TIMESTAMP"
        if [ ! -d "$BACKUP_PATH" ]; then
            echo -e "${RED}❌ MongoDB 백업을 찾을 수 없습니다: $BACKUP_PATH${NC}"
            usage
        fi
        
        echo -e "${YELLOW}⚠️  주의: 기존 MongoDB 데이터가 모두 삭제됩니다!${NC}"
        read -p "계속하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "복원이 취소되었습니다."
            exit 1
        fi
        
        echo -e "${YELLOW}📊 MongoDB 복원 중...${NC}"
        if docker-compose exec -T mongodb mongorestore --host localhost --port 27017 --db korea_public_api --drop /backups/mongodb_$TIMESTAMP/korea_public_api; then
            echo -e "${GREEN}✅ MongoDB 복원 완료${NC}"
        else
            echo -e "${RED}❌ MongoDB 복원 실패${NC}"
            exit 1
        fi
        ;;
        
    redis)
        BACKUP_FILE="$BACKUP_DIR/redis_$TIMESTAMP.rdb"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo -e "${RED}❌ Redis 백업을 찾을 수 없습니다: $BACKUP_FILE${NC}"
            usage
        fi
        
        echo -e "${YELLOW}⚠️  주의: 기존 Redis 데이터가 모두 삭제됩니다!${NC}"
        read -p "계속하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "복원이 취소되었습니다."
            exit 1
        fi
        
        echo -e "${YELLOW}🔴 Redis 복원 중...${NC}"
        
        # Redis 서비스 중지
        docker-compose stop redis
        
        # 백업 파일 복사
        cp "$BACKUP_FILE" "./volumes/redis/data/dump.rdb"
        
        # Redis 서비스 시작
        docker-compose start redis
        
        # 잠시 대기 후 확인
        sleep 5
        if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
            echo -e "${GREEN}✅ Redis 복원 완료${NC}"
        else
            echo -e "${RED}❌ Redis 복원 실패${NC}"
            exit 1
        fi
        ;;
        
    *)
        echo -e "${RED}❌ 잘못된 타입: $TYPE${NC}"
        usage
        ;;
esac

echo -e "${GREEN}✅ 복원 완료!${NC}"