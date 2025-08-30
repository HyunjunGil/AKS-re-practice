from flask import Flask, request, jsonify, session
from flask_cors import CORS
import redis
import mysql.connector
import json
from datetime import datetime
import os
from kafka import KafkaProducer, KafkaConsumer
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from contextlib import contextmanager
import logging
from logging.config import dictConfig


# 로깅 설정
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """데이터베이스 설정 클래스"""
    host: str
    user: str
    password: str
    database: str
    connect_timeout: int = 10
    ssl_disabled: bool = False
    ssl_verify_cert: bool = False


@dataclass
class RedisConfig:
    """Redis 설정 클래스"""
    host: str
    port: int
    password: str
    decode_responses: bool = True
    ssl: bool = True
    ssl_cert_reqs: Optional[str] = None
    ssl_ca_certs: Optional[str] = None


@dataclass
class KafkaConfig:
    """Kafka 설정 클래스"""
    bootstrap_servers: str
    username: str
    password: str
    security_protocol: str = 'SASL_PLAINTEXT'
    sasl_mechanism: str = 'PLAIN'


class DatabaseManager:
    """데이터베이스 연결 및 관리 클래스"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
    
    def get_connection(self):
        """데이터베이스 연결 반환"""
        try:
            return mysql.connector.connect(
                host=self.config.host,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                connect_timeout=self.config.connect_timeout,
                ssl_disabled=self.config.ssl_disabled,
                ssl_verify_cert=self.config.ssl_verify_cert,
            )
        except Exception as e:
            logger.error(f"MariaDB 연결 오류: {str(e)}")
            raise
    
    @contextmanager
    def get_cursor(self, dictionary: bool = False):
        """컨텍스트 매니저를 사용한 커서 관리"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor, conn
        finally:
            cursor.close()
            conn.close()


class RedisManager:
    """Redis 연결 및 관리 클래스"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
    
    def get_connection(self):
        """Redis 연결 반환"""
        try:
            return redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                decode_responses=self.config.decode_responses,
                ssl=self.config.ssl,
                ssl_cert_reqs=self.config.ssl_cert_reqs,
                ssl_ca_certs=self.config.ssl_ca_certs
            )
        except Exception as e:
            logger.error(f"Redis 연결 오류: {str(e)}")
            raise
    
    @contextmanager
    def get_client(self):
        """컨텍스트 매니저를 사용한 Redis 클라이언트 관리"""
        client = self.get_connection()
        try:
            yield client
        finally:
            client.close()


class KafkaManager:
    """Kafka 연결 및 관리 클래스"""
    
    def __init__(self, config: KafkaConfig):
        self.config = config
    
    def get_producer(self):
        """Kafka Producer 반환"""
        return KafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_plain_username=self.config.username,
            sasl_plain_password=self.config.password
        )
    
    def get_consumer(self, topic: str, group_id: str = 'default'):
        """Kafka Consumer 반환"""
        return KafkaConsumer(
            topic,
            bootstrap_servers=self.config.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            security_protocol=self.config.security_protocol,
            sasl_mechanism=self.config.sasl_mechanism,
            sasl_plain_username=self.config.username,
            sasl_plain_password=self.config.password,
            group_id=group_id,
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )


class MessageService:
    """메시지 관련 비즈니스 로직 클래스"""
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db_manager = db_manager
        self.redis_manager = redis_manager
    
    def save_message(self, user_id: str, message_text: str) -> Dict[str, Any]:
        """메시지 저장"""
        try:
            with self.db_manager.get_cursor() as (cursor, conn):
                sql = "INSERT INTO messages (message, created_at, user_id) VALUES (%s, %s, %s)"
                cursor.execute(sql, (message_text, datetime.utcnow(), user_id))
                conn.commit()
                message_id = cursor.lastrowid
            
            # Redis에 캐시로 저장
            self._cache_message(user_id, message_id, message_text)
            
            return {"status": "success", "message_id": message_id}
            
        except Exception as e:
            logger.error(f"메시지 저장 오류: {str(e)}")
            raise
    
    def get_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자별 메시지 조회"""
        # Redis에서 먼저 조회 시도
        redis_messages = self._get_messages_from_cache(user_id)
        if redis_messages:
            return redis_messages
        
        # DB에서 조회
        db_messages = self._get_messages_from_db(user_id)
        
        # Redis에 캐시로 저장
        self._cache_messages(user_id, db_messages)
        
        return db_messages
    
    def search_messages(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """메시지 검색"""
        logger.info(f"메시지 검색 시작: user_id={user_id}, query={query}")
        
        # Redis에서 먼저 검색
        redis_results = self._search_messages_from_cache(user_id, query)
        if redis_results:
            logger.info(f"Redis에서 검색 결과 {len(redis_results)}개 반환")
            return redis_results
        
        logger.info("Redis에서 검색 결과 없음, DB에서 검색 진행")
        
        # DB에서 검색
        db_results = self._search_messages_from_db(user_id, query)
        logger.info(f"DB에서 검색 결과 {len(db_results)}개 발견")
        
        # Redis에 캐시로 저장
        self._cache_messages(user_id, db_results)
        
        return db_results
    
    def _cache_message(self, user_id: str, message_id: int, message_text: str):
        """단일 메시지를 Redis에 캐시"""
        try:
            with self.redis_manager.get_client() as client:
                message_data = {
                    'id': message_id,
                    'message': message_text,
                    'created_at': datetime.utcnow().isoformat(),
                    'user_id': user_id,
                    'source': 'redis'  # source 정보 추가
                }
                cache_key = f"user_messages:{user_id}:{message_id}"
                client.setex(cache_key, 3600, json.dumps(message_data))
                logger.info(f"새 메시지를 Redis에 캐시로 저장: {cache_key}")
        except Exception as e:
            logger.warning(f"Redis 캐시 저장 오류: {str(e)}")
    
    def _cache_messages(self, user_id: str, messages: List[Dict[str, Any]]):
        """여러 메시지를 Redis에 캐시"""
        try:
            with self.redis_manager.get_client() as client:
                for message in messages:
                    # source 정보를 redis로 변경하여 캐시
                    message_copy = message.copy()
                    message_copy['source'] = 'redis'
                    cache_key = f"user_messages:{user_id}:{message['id']}"
                    client.setex(cache_key, 3600, json.dumps(message_copy))
                logger.info(f"DB 조회 결과 {len(messages)}개를 Redis에 캐시로 저장")
        except Exception as e:
            logger.warning(f"Redis 캐시 저장 오류: {str(e)}")
    
    def _get_messages_from_cache(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Redis에서 메시지 조회"""
        try:
            with self.redis_manager.get_client() as client:
                user_message_keys = client.keys(f"user_messages:{user_id}:*")
                
                if not user_message_keys:
                    return None
                
                redis_messages = []
                for key in user_message_keys:
                    message_data = client.get(key)
                    if message_data:
                        message = json.loads(message_data)
                        # source 정보 추가
                        message['source'] = 'redis'
                        redis_messages.append(message)
                
                if redis_messages:
                    # 날짜순으로 정렬 (최신순)
                    redis_messages.sort(key=lambda x: x['created_at'], reverse=True)
                    self._format_dates(redis_messages)
                    logger.info(f"Redis에서 메시지 {len(redis_messages)}개 조회")
                    return redis_messages
                
        except Exception as e:
            logger.warning(f"Redis 조회 오류: {str(e)}")
        
        return None
    
    def _get_messages_from_db(self, user_id: str) -> List[Dict[str, Any]]:
        """DB에서 메시지 조회"""
        with self.db_manager.get_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT * FROM messages WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            messages = cursor.fetchall()
        
        self._format_dates(messages)
        # source 정보 추가
        for message in messages:
            message['source'] = 'database'
        return messages
    
    def _search_messages_from_cache(self, user_id: str, query: str) -> Optional[List[Dict[str, Any]]]:
        """Redis에서 메시지 검색"""
        try:
            with self.redis_manager.get_client() as client:
                user_message_keys = client.keys(f"user_messages:{user_id}:*")
                
                redis_results = []
                for key in user_message_keys:
                    message_data = client.get(key)
                    if message_data:
                        message = json.loads(message_data)
                        if query.lower() in message['message'].lower():
                            # source 정보 추가
                            message['source'] = 'redis'
                            redis_results.append(message)
                
                if redis_results:
                    self._format_dates(redis_results)
                    logger.info(f"Redis에서 검색 결과 {len(redis_results)}개 발견")
                    return redis_results
                
        except Exception as e:
            logger.warning(f"Redis 검색 오류: {str(e)}")
        
        return None
    
    def _search_messages_from_db(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """DB에서 메시지 검색"""
        with self.db_manager.get_cursor(dictionary=True) as (cursor, conn):
            sql = "SELECT * FROM messages WHERE user_id = %s AND message LIKE %s ORDER BY created_at DESC"
            cursor.execute(sql, (user_id, f"%{query}%"))
            results = cursor.fetchall()
        
        self._format_dates(results)
        # source 정보 추가
        for message in results:
            message['source'] = 'database'
        return results
    
    def _format_dates(self, messages: List[Dict[str, Any]]):
        """메시지 날짜 형식 변환"""
        for message in messages:
            if message.get('created_at'):
                if hasattr(message['created_at'], 'isoformat'):
                    message['created_at'] = message['created_at'].isoformat()
                else:
                    message['created_at'] = str(message['created_at'])


class UserService:
    """사용자 관련 비즈니스 로직 클래스"""
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db_manager = db_manager
        self.redis_manager = redis_manager
    
    def register_user(self, username: str, password: str) -> Dict[str, Any]:
        """사용자 회원가입"""
        try:
            with self.db_manager.get_cursor() as (cursor, conn):
                # 사용자명 중복 체크
                cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    return {"status": "error", "message": "이미 존재하는 사용자명입니다"}
                
                # 비밀번호 해시화
                hashed_password = generate_password_hash(password)
                
                # 사용자 정보 저장
                sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
                cursor.execute(sql, (username, hashed_password))
                conn.commit()
            
            return {"status": "success", "message": "회원가입이 완료되었습니다"}
            
        except Exception as e:
            logger.error(f"회원가입 오류: {str(e)}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """사용자 인증"""
        try:
            with self.db_manager.get_cursor(dictionary=True) as (cursor, conn):
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                return username
            
            return None
            
        except Exception as e:
            logger.error(f"사용자 인증 오류: {str(e)}")
            raise
    
    def save_session_to_redis(self, username: str):
        """Redis에 세션 정보 저장"""
        try:
            with self.redis_manager.get_client() as client:
                session_data = {
                    'user_id': username,
                    'login_time': datetime.now().isoformat()
                }
                client.set(f"session:{username}", json.dumps(session_data))
                client.expire(f"session:{username}", 3600)
        except Exception as e:
            logger.warning(f"Redis 세션 저장 오류: {str(e)}")
    
    def clear_session_from_redis(self, username: str):
        """Redis에서 세션 정보 삭제"""
        try:
            with self.redis_manager.get_client() as client:
                client.delete(f"session:{username}")
        except Exception as e:
            logger.warning(f"Redis 세션 삭제 오류: {str(e)}")


class LoggingService:
    """로깅 관련 서비스 클래스"""
    
    def __init__(self, redis_manager: RedisManager, kafka_manager: KafkaManager):
        self.redis_manager = redis_manager
        self.kafka_manager = kafka_manager
    
    def log_to_redis(self, action: str, details: str):
        """Redis에 로그 저장"""
        try:
            with self.redis_manager.get_client() as client:
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': action,
                    'details': details
                }
                client.lpush('api_logs', json.dumps(log_entry))
                client.ltrim('api_logs', 0, 99)  # 최근 100개 로그만 유지
        except Exception as e:
            logger.error(f"Redis logging error: {str(e)}")
    
    def log_api_stats_async(self, endpoint: str, method: str, status: str, user_id: str):
        """API 통계를 비동기로 Kafka에 로깅"""
        def _log():
            try:
                producer = self.kafka_manager.get_producer()
                log_data = {
                    'timestamp': datetime.now().isoformat(),
                    'endpoint': endpoint,
                    'method': method,
                    'status': status,
                    'user_id': user_id,
                    'message': f"{user_id}가 {method} {endpoint} 호출 ({status})"
                }
                producer.send('api-logs', log_data)
                producer.flush()
            except Exception as e:
                logger.error(f"Kafka logging error: {str(e)}")
        
        Thread(target=_log).start()


class CacheService:
    """캐시 관련 서비스 클래스"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
    
    def get_cache_status(self, user_id: str) -> Dict[str, Any]:
        """캐시 상태 조회"""
        try:
            with self.redis_manager.get_client() as client:
                # 사용자별 캐시된 메시지 개수
                user_message_keys = client.keys(f"user_messages:{user_id}:*")
                cached_count = len(user_message_keys)
                
                # 전체 캐시 키 개수
                total_keys = len(client.keys("*"))
                
                # 캐시 TTL 정보
                cache_info = {}
                for key in user_message_keys[:5]:  # 최대 5개만 확인
                    ttl = client.ttl(key)
                    cache_info[key] = ttl
                
                return {
                    "status": "success",
                    "user_cached_messages": cached_count,
                    "total_cache_keys": total_keys,
                    "sample_cache_ttl": cache_info
                }
        except Exception as e:
            logger.error(f"캐시 상태 조회 오류: {str(e)}")
            raise
    
    def clear_user_cache(self, user_id: str) -> Dict[str, Any]:
        """사용자별 캐시 클리어"""
        try:
            with self.redis_manager.get_client() as client:
                # 사용자별 캐시된 메시지 삭제
                user_message_keys = client.keys(f"user_messages:{user_id}:*")
                deleted_count = 0
                
                for key in user_message_keys:
                    client.delete(key)
                    deleted_count += 1
                
                return {
                    "status": "success",
                    "message": f"캐시가 클리어되었습니다. 삭제된 키: {deleted_count}개"
                }
        except Exception as e:
            logger.error(f"캐시 클리어 오류: {str(e)}")
            raise


# 데코레이터
def login_required(f):
    """로그인 필요 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "로그인이 필요합니다"}), 401
        return f(*args, **kwargs)
    return decorated_function


# Flask 앱 생성
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# 설정 로드
db_config = DatabaseConfig(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)

redis_config = RedisConfig(
    host=os.getenv('REDIS_HOST', 'my-redis-master'),
    port=int(os.getenv('REDIS_PORT', '6379')),
    password=os.getenv('REDIS_PASSWORD')
)

kafka_config = KafkaConfig(
    bootstrap_servers=os.getenv('KAFKA_SERVERS', 'my-kafka:9092'),
    username=os.getenv('KAFKA_USERNAME', 'user1'),
    password=os.getenv('KAFKA_PASSWORD', '')
)

# 서비스 인스턴스 생성
db_manager = DatabaseManager(db_config)
redis_manager = RedisManager(redis_config)
kafka_manager = KafkaManager(kafka_config)

message_service = MessageService(db_manager, redis_manager)
user_service = UserService(db_manager, redis_manager)
logging_service = LoggingService(redis_manager, kafka_manager)
cache_service = CacheService(redis_manager)


# API 엔드포인트
@app.route('/db/message', methods=['POST'])
@login_required
def save_message():
    """메시지 저장"""
    try:
        user_id = session['user_id']
        data = request.json
        message_text = data.get('message', '')
        
        if not message_text:
            return jsonify({"status": "error", "message": "메시지 내용이 필요합니다"}), 400
        
        result = message_service.save_message(user_id, message_text)
        
        # 로깅
        logging_service.log_to_redis('db_insert', f"Message saved: {message_text[:30]}...")
        logging_service.log_api_stats_async('/db/message', 'POST', 'success', user_id)
        
        return jsonify(result)
        
    except Exception as e:
        if 'user_id' in session:
            logging_service.log_api_stats_async('/db/message', 'POST', 'error', session['user_id'])
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/db/messages', methods=['GET'])
@login_required
def get_messages():
    """메시지 조회"""
    try:
        user_id = session['user_id']
        messages = message_service.get_messages(user_id)
        
        source = "redis" if len(messages) > 0 and messages[0].get('source') == 'redis' else "database"
        
        logging_service.log_api_stats_async('/db/messages', 'GET', 'success', user_id)
        
        return jsonify({
            "status": "success",
            "source": source,
            "results": messages,
            "count": len(messages)
        })
        
    except Exception as e:
        if 'user_id' in session:
            logging_service.log_api_stats_async('/db/messages', 'GET', 'error', session['user_id'])
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/db/messages/search', methods=['GET'])
@login_required
def search_messages():
    """메시지 검색"""
    try:
        user_id = session['user_id']
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({"status": "error", "message": "검색어가 필요합니다"}), 400
        
        results = message_service.search_messages(user_id, query)
        
        source = "redis" if len(results) > 0 and results[0].get('source') == 'redis' else "database"
        
        logging_service.log_api_stats_async('/db/messages/search', 'GET', 'success', user_id)
        
        return jsonify({
            "status": "success",
            "source": source,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        if 'user_id' in session:
            logging_service.log_api_stats_async('/db/messages/search', 'GET', 'error', session['user_id'])
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/register', methods=['POST'])
def register():
    """회원가입"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "사용자명과 비밀번호는 필수입니다"}), 400
        
        result = user_service.register_user(username, password)
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    """로그인"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "사용자명과 비밀번호는 필수입니다"}), 400
        
        user_id = user_service.authenticate_user(username, password)
        
        if user_id:
            session['user_id'] = user_id
            user_service.save_session_to_redis(user_id)
            
            return jsonify({
                "status": "success",
                "message": "로그인 성공",
                "username": user_id
            })
        
        return jsonify({"status": "error", "message": "잘못된 인증 정보"}), 401
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"status": "error", "message": "로그인 처리 중 오류가 발생했습니다"}), 500


@app.route('/logout', methods=['POST'])
def logout():
    """로그아웃"""
    try:
        if 'user_id' in session:
            username = session['user_id']
            user_service.clear_session_from_redis(username)
            session.pop('user_id', None)
        
        return jsonify({"status": "success", "message": "로그아웃 성공"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/logs/redis', methods=['GET'])
def get_redis_logs():
    """Redis 로그 조회"""
    try:
        with redis_manager.get_client() as client:
            logs = client.lrange('api_logs', 0, -1)
            return jsonify([json.loads(log) for log in logs])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/cache/status', methods=['GET'])
@login_required
def get_cache_status():
    """캐시 상태 조회"""
    try:
        user_id = session['user_id']
        result = cache_service.get_cache_status(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    """캐시 클리어"""
    try:
        user_id = session['user_id']
        result = cache_service.clear_user_cache(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/logs/kafka', methods=['GET'])
@login_required
def get_kafka_logs():
    """Kafka 로그 조회"""
    try:
        consumer = kafka_manager.get_consumer('api-logs', 'api-logs-viewer')
        
        logs = []
        try:
            for message in consumer:
                logs.append({
                    'timestamp': message.value['timestamp'],
                    'endpoint': message.value['endpoint'],
                    'method': message.value['method'],
                    'status': message.value['status'],
                    'user_id': message.value['user_id'],
                    'message': message.value['message']
                })
                if len(logs) >= 100:
                    break
        finally:
            consumer.close()
        
        # 시간 역순으로 정렬
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify(logs)
        
    except Exception as e:
        logger.error(f"Kafka log retrieval error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    logger.info("=== Flask 앱 시작 ===")
    app.run(host='0.0.0.0', port=5000, debug=True) 