"""
Caching utilities for improved performance
"""
import json
import hashlib
from functools import wraps
from typing import Any, Optional, Callable, Dict
import redis
from config.settings import settings

# Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client with lazy initialization"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


class CacheManager:
    """Cache management utilities"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from function arguments"""
        # Create a string representation of arguments
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        # Hash for consistent key length
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                return json.loads(cached_value)
        except (redis.RedisError, json.JSONDecodeError):
            pass
        return None
    
    def set(self, key: str, value: Any, expiry_seconds: int = 300) -> bool:
        """Set value in cache"""
        try:
            serialized_value = json.dumps(value, default=str)
            return self.redis_client.setex(key, expiry_seconds, serialized_value)
        except (redis.RedisError, TypeError):
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError:
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0
    
    def clear_user_cache(self, user_id: int) -> int:
        """Clear all cache entries for a specific user"""
        pattern = f"cache:*user_id:{user_id}*"
        return self.delete_pattern(pattern)
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        try:
            return self.redis_client.incr(key, amount)
        except redis.RedisError:
            return None
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiry time for a key"""
        try:
            return self.redis_client.expire(key, seconds)
        except redis.RedisError:
            return False


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(expiry_seconds: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator to cache function results
    
    Args:
        expiry_seconds: Cache expiry time in seconds
        key_prefix: Optional prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache_manager._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, expiry_seconds)
            return result
        
        # Add cache management methods to the decorated function
        wrapper.cache_clear = lambda: cache_manager.delete_pattern(f"cache:*{prefix}*")
        wrapper.cache_key = lambda *args, **kwargs: cache_manager._generate_cache_key(
            prefix, *args, **kwargs
        )
        
        return wrapper
    return decorator


def cache_user_result(expiry_seconds: int = 300):
    """
    Decorator specifically for user-related cache that includes user_id in key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id from arguments
            user_id = None
            if args and hasattr(args[0], 'id'):
                user_id = args[0].id
            elif 'user_id' in kwargs:
                user_id = kwargs['user_id']
            elif len(args) > 1 and isinstance(args[1], int):
                user_id = args[1]
            
            # Generate cache key with user_id
            prefix = f"{func.__name__}_user_{user_id}" if user_id else func.__name__
            cache_key = cache_manager._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, expiry_seconds)
            return result
        
        return wrapper
    return decorator


class RateLimiter:
    """Rate limiting utilities using Redis"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
    
    def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int = 60,
        cost: int = 1
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            cost: Cost of this request (default 1)
        
        Returns:
            Tuple of (is_allowed, info_dict)
        """
        try:
            pipe = self.redis_client.pipeline()
            now = int(time.time())
            
            # Sliding window key
            window_key = f"rate_limit:{key}:{now // window_seconds}"
            
            # Get current count
            pipe.get(window_key)
            current_str = pipe.execute()[0]
            current = int(current_str) if current_str else 0
            
            if current + cost <= limit:
                # Allow request and increment counter
                pipe.incr(window_key, cost)
                pipe.expire(window_key, window_seconds * 2)  # Double window for cleanup
                pipe.execute()
                
                return True, {
                    'allowed': True,
                    'current': current + cost,
                    'limit': limit,
                    'remaining': limit - (current + cost),
                    'reset_time': (now // window_seconds + 1) * window_seconds
                }
            else:
                # Deny request
                return False, {
                    'allowed': False,
                    'current': current,
                    'limit': limit,
                    'remaining': 0,
                    'reset_time': (now // window_seconds + 1) * window_seconds
                }
        except redis.RedisError:
            # If Redis is down, allow request (fail open)
            return True, {'allowed': True, 'error': 'cache_unavailable'}


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(key_func: Callable, limit: int, window_seconds: int = 60):
    """
    Decorator for rate limiting
    
    Args:
        key_func: Function to generate rate limit key from request
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from fastapi import HTTPException, status
            
            # Generate rate limit key
            limit_key = key_func(*args, **kwargs)
            
            # Check rate limit
            allowed, info = rate_limiter.is_allowed(limit_key, limit, window_seconds)
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(info.get('remaining', 0)),
                        "X-RateLimit-Reset": str(info.get('reset_time', 0))
                    }
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Import time for rate limiter
import time