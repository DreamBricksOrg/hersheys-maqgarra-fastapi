from core.redis import redis
class RedisService:

    @staticmethod
    def add_to_redis_set(key: str, value: str):
        redis.sadd(key, value)
    
    @staticmethod
    def get_list(key: str):
        return list(redis.smembers(key))
    
    @staticmethod
    def is_value_present(key: str, value: str):        
        return list(redis.sismember(key, value))
        
    @staticmethod
    def remove_from_redis_set(key: str, value: str):
        redis.srem(key, value)

        
    
    