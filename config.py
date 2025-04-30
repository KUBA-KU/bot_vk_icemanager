import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config():
    # Load configuration from environment variables or config file.
#
# Returns:
# dict: Configuration parameters
    config = {
        "group_id": os.environ.get("VK_GROUP_ID"),
        "token": os.environ.get("VK_API_TOKEN"),  # Используем VK_API_TOKEN вместо VK_TOKEN
        "command_cooldown": os.environ.get("COMMAND_COOLDOWN", 3),
        "log_peer_id": os.environ.get("VK_LOG_CHAT_ID")  # ID беседы для логирования
    }
    
    # Всегда загружаем конфигурацию из файла, переменные окружения имеют более высокий приоритет
    try:
        with open("config.json", "r", encoding="utf-8") as config_file:
            file_config = json.load(config_file)
            
            # Update configs from file if not set in env
            if not config["group_id"]:
                config["group_id"] = file_config.get("group_id")
            if not config["token"]:
                config["token"] = file_config.get("token")
            if not config["command_cooldown"] or config["command_cooldown"] == 3:
                config["command_cooldown"] = file_config.get("command_cooldown", 3)
            
            # Всегда проверяем log_peer_id, это важно для логирования
            if not config["log_peer_id"] and "log_peer_id" in file_config:
                config["log_peer_id"] = file_config.get("log_peer_id")
                logger.info(f"Загружен ID беседы для логирования: {config['log_peer_id']}")
            
        logger.info("Configuration loaded from config.json")
    except FileNotFoundError:
        logger.warning("Config file not found, using environment variables only")
    except json.JSONDecodeError:
        logger.error("Config file contains invalid JSON")
        raise
    
    # Convert command_cooldown to int
    config["command_cooldown"] = int(config["command_cooldown"])
    
    # Проверяем наличие обязательных параметров
    if not config["group_id"]:
        raise ValueError("VK_GROUP_ID обязателен, но не предоставлен")
    if not config["token"]:
        raise ValueError("VK_API_TOKEN обязателен, но не предоставлен")
    
    log_status = "настроено" if config.get("log_peer_id") else "отключено"
    logger.info(f"Configuration loaded successfully: group_id={config['group_id']}, command_cooldown={config['command_cooldown']}, logging={log_status}")
    return config