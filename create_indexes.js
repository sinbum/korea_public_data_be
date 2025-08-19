
// MongoDB 인덱스 생성 스크립트
// mongo shell에서 실행

use korea_public_api;

// 기존 인덱스 확인
db.announcements.getIndexes();

// 성능 최적화 인덱스 생성
db.announcements.createIndex(
    {"is_active": 1, "created_at": -1},
    {name: "active_recent_idx"}
);

db.announcements.createIndex(
    {"announcement_data.business_id": 1, "is_active": 1},
    {name: "business_id_active_idx"}
);

db.announcements.createIndex(
    {"announcement_data.business_type": 1, "is_active": 1, "created_at": -1},
    {name: "type_active_recent_idx"}
);

db.announcements.createIndex(
    {"announcement_data.status": 1, "is_active": 1},
    {name: "status_active_idx"}
);

// 인덱스 생성 확인
db.announcements.getIndexes();
