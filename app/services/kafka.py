import json
import logging
from aiokafka import AIOKafkaProducer
from app.settings import settings  # Путь до ваших настроек

logger = logging.getLogger(__name__)

class KafkaClient:
    _instance = None
    _producer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaClient, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        """
        Подключение к Kafka. Если продюсер ещё не проинициализирован, создаём его.
        """
        if self._producer is None:
            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,  # например: "localhost:9092"
                    value_serializer=lambda v: json.dumps(v).encode("utf-8")
                )
                await self._producer.start()
                logger.info(f"Подключение к Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
            except Exception as e:
                logger.error(f"Ошибка подключения к Kafka: {e}")
                raise

    async def disconnect(self):
        """
        Отключение от Kafka и сброс продюсера.
        """
        if self._producer:
            await self._producer.stop()
            logger.info("Отключение от Kafka.")
            self._producer = None

    def __getattr__(self, name):
        """
        Перенаправление всех вызовов (кроме явно определённых методов) к объекту продюсера.
        Если продюсер не подключён, генерируется исключение.
        """
        if self._producer is None:
            raise Exception("Kafka продюсер не подключен. Вызовите connect() перед использованием.")
        return getattr(self._producer, name)

    def __repr__(self):
        return f"<KafkaClient connected={self._producer is not None}>"

kafka_client = KafkaClient()
