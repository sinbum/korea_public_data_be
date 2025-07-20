FROM python:3.11-slim

# 환경변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs /app/uploads /app/tmp && \
    chown -R appuser:appuser /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (개발환경에서는 볼륨으로 덮어씀)
COPY . .

# 권한 설정
RUN chown -R appuser:appuser /app

# 비root 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]