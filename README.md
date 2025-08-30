# K8s 마이크로서비스 데모

이 프로젝트는 Kubernetes 환경에서 Redis, MariaDB, Kafka를 활용하는 마이크로서비스 데모입니다.

## 주요 기능

### 1. 사용자 관리
- 회원가입: 새로운 사용자 등록
- 로그인/로그아웃: 세션 기반 인증
- Redis를 활용한 세션 관리

### 2. 메시지 관리 (MariaDB)
- 메시지 저장: 사용자가 입력한 메시지를 DB에 저장
- 메시지 조회: 저장된 메시지 목록 표시
- 샘플 데이터 생성: 테스트용 샘플 메시지 생성
- 페이지네이션: 대량의 데이터 효율적 처리

### 3. 검색 기능
- 메시지 검색: 특정 키워드로 메시지 검색
- 전체 메시지 조회: 모든 저장된 메시지 표시
- Redis 캐시를 활용한 검색 성능 최적화

### 4. 로깅 시스템
- Redis 로깅: API 호출 로그 저장 및 조회
- Kafka 로깅: API 통계 데이터 수집

## 데이터베이스 구조

### MariaDB
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT,
    created_at DATETIME,
    user_id VARCHAR(255)
);
```

### Redis 데이터 구조
- 세션 저장: `session:{username}`
- API 로그: `api_logs` (List 타입)
- 검색 캐시: `search:{query}`

## API 엔드포인트

### 사용자 관리
- POST /register: 회원가입
- POST /login: 로그인
- POST /logout: 로그아웃

### 메시지 관리
- POST /db/message: 메시지 저장
- GET /db/messages: 전체 메시지 조회
- GET /db/messages/search: 메시지 검색

### 로그 관리
- GET /logs/redis: Redis 로그 조회
- GET /logs/kafka: Kafka 로그 조회

## 환경 변수 설정
```yaml
- MYSQL_HOST: MariaDB 호스트
- MYSQL_USER: MariaDB 사용자
- MYSQL_PASSWORD: MariaDB 비밀번호
- REDIS_HOST: Redis 호스트
- REDIS_PASSWORD: Redis 비밀번호
- KAFKA_SERVERS: Kafka 서버
- KAFKA_USERNAME: Kafka 사용자
- KAFKA_PASSWORD: Kafka 비밀번호
- FLASK_SECRET_KEY: Flask 세션 암호화 키
```

## 보안 기능
- 비밀번호 해시화 저장
- 세션 기반 인증
- Redis를 통한 세션 관리
- API 접근 제어

## 성능 최적화
- Redis 캐시를 통한 검색 성능 향상
- 비동기 로깅으로 API 응답 시간 개선
- 페이지네이션을 통한 대용량 데이터 처리

## 모니터링
- API 호출 로그 저장 및 조회
- 사용자 행동 추적
- 시스템 성능 모니터링

## Kafka 연결 테스트

### API 엔드포인트를 통한 테스트
- `GET /kafka/test`: 종합 연결 테스트
- `GET /kafka/status`: 클러스터 상태 조회

### Azure Event Hubs 환경 변수 설정
```yaml
# Azure Event Hubs 연결 시
- KAFKA_SERVERS: your-namespace.servicebus.windows.net:9093
- KAFKA_USERNAME: $ConnectionString
- KAFKA_PASSWORD: Endpoint=sb://your-namespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=your-key
- SECURITY_PROTOCOL: SASL_SSL
- SASL_MECHANISM: PLAIN
```

## Azure Event Hubs 호환성
이 프로젝트는 **confluent-kafka** 라이브러리를 사용하여 Azure Event Hubs와의 호환성을 보장합니다.

### 호환성 장점
- **프로토콜 호환**: Kafka 프로토콜을 통한 완벽한 호환성
- **성능 최적화**: C 기반 라이브러리로 높은 처리량
- **안정성**: 프로덕션 환경에서 검증된 라이브러리
- **마이그레이션 용이**: 로컬 Kafka에서 Azure Event Hubs로 쉽게 전환 가능

### 마이그레이션 가이드
1. **환경 변수 변경**: 위의 Azure Event Hubs 환경 변수로 설정
2. **보안 프로토콜 변경**: `SASL_SSL`로 변경 (포트 9093)
3. **연결 문자열 설정**: Azure Portal에서 제공하는 연결 문자열 사용
4. **테스트 실행**: `/kafka/test` 엔드포인트로 연결 상태 확인
