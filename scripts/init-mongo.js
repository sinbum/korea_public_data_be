// MongoDB 초기화 스크립트
// 개발 환경에서 사용할 사용자 계정과 데이터베이터베이스 생성

// admin 데이터베이스로 전환
db = db.getSiblingDB('admin');

// API 사용자를 위한 데이터베이스 생성
db = db.getSiblingDB('korea_public_api');

// API 사용자 생성
try {
    db.createUser({
        user: 'api_user',
        pwd: 'api_prod_password_2024',
        roles: [
            { role: 'readWrite', db: 'korea_public_api' },
            { role: 'dbAdmin', db: 'korea_public_api' }
        ]
    });
    print('API user created successfully');
} catch (error) {
    print('API user creation failed or already exists: ' + error);
}

// 컬렉션 생성 및 인덱스 설정
try {
    // announcements 컬렉션 생성
    db.createCollection('announcements');
    
    // 인덱스 생성 (백그라운드)
    db.announcements.createIndex({ 'announcement_data.business_id': 1 }, { background: true });
    db.announcements.createIndex({ 'announcement_data.business_name': 1 }, { background: true });
    db.announcements.createIndex({ 'is_active': 1, 'announcement_data.announcement_date': -1 }, { background: true });
    db.announcements.createIndex({ 'is_active': 1, 'announcement_data.end_date': 1 }, { background: true });
    db.announcements.createIndex({ 'created_at': -1 }, { background: true });
    
    print('Announcements collection and indexes created successfully');
} catch (error) {
    print('Collections and indexes creation failed: ' + error);
}

print('MongoDB initialization completed successfully');
