import secrets
import base64

secret_key = secrets.token_hex(32)
encoded_key = base64.b64encode(secret_key.encode()).decode()
print(encoded_key) 

mariadb_raw_password = "hyunjun-mariadb"
mariadb_encoded_password = base64.b64encode(mariadb_raw_password.encode()).decode()
print("MYSQL_PASSWORD:", mariadb_encoded_password)

redis_raw_password = "hyunjun-redis"
redis_encoded_password = base64.b64encode(redis_raw_password.encode()).decode()
print("REDIS_PASSWORD:", redis_encoded_password)

kafka_raw_password = "hyunjun-kafka"
kafka_encoded_password = base64.b64encode(kafka_raw_password.encode()).decode()
print("KAFKA_PASSWORD:", kafka_encoded_password)
