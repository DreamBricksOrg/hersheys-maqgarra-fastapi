from core.redis import redis
class RedisService:

    @staticmethod
    async def add_to_redis_set(key: str, value: str):
        await redis.sadd(key, value)
    
    @staticmethod
    async def get_list(key: str):
        list_members = await redis.smembers(key)
        if list_members is None:
            return None
        print(list_members)
        return list(list_members)
    
    @staticmethod
    async def is_value_present(key: str, value: str):        
        return await redis.sismember(key, value)
        
    @staticmethod
    async def remove_from_redis_set(key: str, value: str):
        await redis.srem(key, value)

        
    
    