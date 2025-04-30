import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from bot import VkBot
from config import load_config
from database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Обработчик сигналов для корректного завершения
def signal_handler(sig, frame):
    logger.info("Получен сигнал завершения, выключаемся...")
    sys.exit(0)

def main():
    # Основная точка входа для приложения VK бота.
    logger.info("Запуск приложения VK Bot...")
    
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    init_db()
    
    # Инициализация и запуск бота
    try:
        bot = VkBot(
            group_id=config["group_id"],
            token=config["token"],
            command_cooldown=config["command_cooldown"],
            log_peer_id=config.get("log_peer_id")
        )
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запуск цикла опроса бота
        logger.info("Бот запущен и работает. Нажмите CTRL+C для остановки.")
        bot.start_polling()
        
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
