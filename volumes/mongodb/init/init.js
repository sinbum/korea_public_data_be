// MongoDB 초기화 스크립트
// 데이터베이스 및 컬렉션 생성

// 데이터베이스 선택
db = db.getSiblingDB('korea_public_api');

// 사용자 생성 (개발환경용)
db.createUser({
  user: 'api_user',
  pwd: 'api_password',
  roles: [
    {
      role: 'readWrite',
      db: 'korea_public_api'
    }
  ]
});

// 컬렉션 생성 및 인덱스 설정
print('Creating collections and indexes...');

// 사업공고 컬렉션
db.createCollection('announcements');
db.announcements.createIndex({ "announcement_data.business_id": 1 }, { unique: true });
db.announcements.createIndex({ "announcement_data.business_name": "text" });
db.announcements.createIndex({ "announcement_data.business_type": 1 });
db.announcements.createIndex({ "is_active": 1 });
db.announcements.createIndex({ "created_at": -1 });

// 콘텐츠 컬렉션
db.createCollection('contents');
db.contents.createIndex({ "content_data.content_id": 1 }, { unique: true });
db.contents.createIndex({ "content_data.title": "text" });
db.contents.createIndex({ "content_data.category": 1 });
db.contents.createIndex({ "is_active": 1 });

// 통계 컬렉션
db.createCollection('statistics');
db.statistics.createIndex({ "statistical_data.stat_id": 1 }, { unique: true });
db.statistics.createIndex({ "statistical_data.year": 1, "statistical_data.month": 1 });
db.statistics.createIndex({ "is_active": 1 });

// 사업정보 컬렉션
db.createCollection('businesses');
db.businesses.createIndex({ "business_data.business_id": 1 }, { unique: true });
db.businesses.createIndex({ "business_data.business_name": "text" });
db.businesses.createIndex({ "business_data.business_type": 1 });
db.businesses.createIndex({ "is_active": 1 });

// API 요청 로그 컬렉션
db.createCollection('api_request_logs');
db.api_request_logs.createIndex({ "created_at": 1 }, { expireAfterSeconds: 2592000 }); // 30일 후 자동 삭제

print('Database initialization completed!');
print('Collections created: announcements, contents, statistics, businesses, api_request_logs');
print('User created: api_user with readWrite permissions');