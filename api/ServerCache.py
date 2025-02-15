import asyncio
import time
from collections import OrderedDict


class ServerCache:
    def __init__(self, ttl: int = 300, max_cache_size: int = 100):
        """
        Initializes the cache with TTL and maximum cache size.

        :param ttl: The time-to-live for the cache, default is 300 seconds (5 minutes).
        :param max_cache_size: The maximum number of items in the cache.
        """
        self.ttl = ttl
        self.max_cache_size = max_cache_size
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()

    async def get(self, key: str):
        """
        Retrieves the cached value. Returns the cached value if it hasn't expired, otherwise returns None.

        :param key: The cache key.
        :return: The cached value or None (if the cache has expired or the key is not found).
        """
        async with self.lock:
            if key in self.cache:
                timestamp, result = self.cache[key]
                if time.time() < timestamp:
                    self.cache.move_to_end(key)  # Mark
                    return result
                else:
                    # Cache expired
                    del self.cache[key]
            return None

    async def set(self, key: str, result):
        """
        Sets a cache item and evicts the least recently used item if the cache exceeds the maximum size.

        :param key: The cache key.
        :param result: The value to be cached.
        """
        async with self.lock:  # thread safety
            expiry_time = time.time() + self.ttl
            self.cache[key] = (expiry_time, result)

            if len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)  # Pop the least
