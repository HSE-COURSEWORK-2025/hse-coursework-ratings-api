import aioredis
import logging
from redis import Redis
from app.settings import settings  # Путь до ваших настроек, если необходимо

logger = logging.getLogger(__name__)


class RedisClientAsync:
    _instance = None
    _redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClientAsync, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """
        Подключение к Redis. Если клиент ещё не проинициализирован, создаём его.
        """
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    f"redis://{settings.REDIS_HOST}", decode_responses=True,
                )
                logger.info(f"Подключение к Redis: redis://{settings.REDIS_HOST}")
            except Exception as e:
                logger.error(f"Ошибка подключения к Redis: {e}")
                raise

    async def disconnect(self):
        """
        Отключение от Redis и сброс клиента.
        """
        if self._redis:
            await self._redis.close()
            logger.info("Отключение от Redis.")
            self._redis = None

    def __getattr__(self, name):
        """
        Перенаправление всех запросов (кроме явно определённых методов)
        к объекту redis. Если redis не подключён, генерируется исключение.
        """
        if self._redis is None:
            raise Exception(
                "Redis не подключен. Вызовите connect() перед использованием."
            )
        return getattr(self._redis, name)

    def __repr__(self):
        return f"<RedisClient connected={self._redis is not None}>"


redis_client_async: aioredis.Redis = RedisClientAsync()


class RedisClientSync:
    _instance = None
    _redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClientSync, cls).__new__(cls)
        return cls._instance

    def connect(self):
        """
        Подключение к Redis. Если клиент ещё не проинициализирован, создаём его.
        """
        if self._redis is None:
            try:
                self._redis = Redis.from_url(f"redis://{settings.REDIS_HOST}", decode_responses=True)
                # Тестовое соединение
                self._redis.ping()
                logger.info(f"Синхронное подключение к Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Ошибка синхронного подключения к Redis: {e}")
                raise

    def disconnect(self):
        """
        Закрытие соединения с Redis.
        """
        if self._redis:
            self._redis.close()
            logger.info("Отключение от Redis.")
            self._redis = None

    def __getattr__(self, name):
        """
        Проксирует методы к внутреннему Redis-объекту.
        """
        if self._redis is None:
            raise Exception("Redis не подключен. Вызовите connect() перед использованием.")
        return getattr(self._redis, name)

    def __repr__(self):
        return f"<RedisSyncClient connected={self._redis is not None}>"


redis_client_sync: RedisClientSync = RedisClientSync()
redis_client_sync.connect()
