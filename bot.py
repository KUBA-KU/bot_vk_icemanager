import logging
import time
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, List, Tuple, Callable, Any, Optional, Union

import database as db
from commands import CommandRegistry
from utils import parse_command, parse_time, format_time_delta

logger = logging.getLogger(__name__)

# Иерархия ролей для проверки прав доступа
ROLE_HIERARCHY = {
    "user": 1,            # Пользователь
    "moderator": 2,       # Модератор
    "senior_moderator": 3, # Старший модератор
    "admin": 4,           # Администратор
    "creator": 5          # Создатель
}

class VkBot:
    # Основной класс VK бота.
    # Обрабатывает команды, взаимодействует с базой данных и обрабатывает события.
    def __init__(self, group_id: str, token: str, command_cooldown: int = 3, log_peer_id: Optional[str] = None):
        # Инициализация VK бота.
#
# Аргументы:
# group_id: ID группы ВКонтакте
# token: API токен VK
# command_cooldown: Задержка между командами в секундах
# log_peer_id: ID беседы для логирования действий модерации
        self.group_id = group_id
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.command_cooldown = command_cooldown
        self.log_peer_id = log_peer_id
        
        # Логируем информацию о настройке логирования для отладки
        if self.log_peer_id:
            logger.info(f"Логирование настроено. ID беседы для логов: {self.log_peer_id}")
        else:
            logger.warning("Логирование отключено: не указан ID беседы для логов")
        
        # Переменные состояния
        self.last_command_time = {}  # Для защиты от спама: {user_id: timestamp}
        self.quiet_mode = False  # Тихий режим: бот не отвечает пользователям без привилегий
        
        # Пул потоков для параллельных операций
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Очередь удаления сообщений
        self.delete_queue = []
        self.delete_lock = threading.Lock()
        
        # Register commands
        self.commands = CommandRegistry(self)
        
        logger.info(f"VK Bot initialized with group_id: {group_id}")

    def send_message(self, peer_id: int, message: str) -> Optional[int]:
        # Send a message to a conversation.
#
# Args:
# peer_id: Conversation ID
# message: Message text
#
# Returns:
# Message ID or None if sending failed
        try:
            result = self.vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=vk_api.utils.get_random_id()
            )
            logger.info(f"Message sent to peer_id {peer_id}: {message[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return None

    def delete_message(self, peer_id: int, message_id: int) -> bool:
        # Удаляет сообщение из беседы.
#
# Аргументы:
# peer_id: ID беседы
# message_id: ID сообщения
#
# Возвращает:
# True при успешном удалении, False в противном случае
        # для беседы
        if peer_id > 2000000000:
            # пробуем через cmids (работает почти всегда)
            try:
                # хз почему, но вк через раз удаляет нормально, приходится делать так
                self.vk.messages.delete(
                    delete_for_all=1,
                    cmids=int(message_id),
                    peer_id=peer_id
                )
                # если дошло до этой строчки, значит все ок
                logger.info(f"Сообщение {message_id} удалено (беседа {peer_id})")
                return True
            except Exception as err:
                logger.warning(f"Не удалось удалить сообщение (способ 1): {str(err)}")
            
            # вк иногда требует список
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=[int(message_id)],
                    peer_id=peer_id
                )
                logger.info(f"Сообщение {message_id} удалено списком (беседа {peer_id})")
                return True
            except Exception as err:
                logger.warning(f"Не удалось удалить сообщение (способ 2): {str(err)}")
            
            # если все плохо, пробуем через строку
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=str(message_id),
                    peer_id=peer_id
                )
                logger.info(f"Сообщение {message_id} удалено строкой (беседа {peer_id})")
                return True
            except Exception as err:
                # ну все, приехали
                logger.error(f"Все способы удаления сообщения не сработали: {str(err)}")
                return False
        else:
            # для личных сообщений
            try:
                self.vk.messages.delete(
                    delete_for_all=1,
                    message_ids=message_id,
                    peer_id=peer_id
                )
                logger.info(f"Удалено личное сообщение {message_id}")
                return True
            except Exception as e:
                logger.error(f"Критическая ошибка удаления: {str(e)}")
                return False
            
    def send_log_message(self, action: str, admin_id: int, target_id: Optional[int] = None, 
                        peer_id: Optional[int] = None, details: Optional[str] = None) -> bool:
        # Отправляет лог в специальную беседу для модераторов.
#
# Аргументы:
# action: Тип действия (kick, ban, warn и т.д.)
# admin_id: ID админа/модера
# target_id: ID юзера, над которым было действие
# peer_id: ID беседы
# details: Доп. инфа (причина бана, длительность мута)
#
# Возвращает:
# True если отправилось, False если что-то пошло не так
        # проверяем, включено ли логирование
        if not self.log_peer_id:
            logger.warning("Логирование выключено (нет ID беседы для логов)")
            return False
            
        try:
            # инфа о модере
            admin_info = self.vk.users.get(user_ids=admin_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
            
            # инфа о юзере, если есть
            target_name = "N/A"
            if target_id:
                try:
                    target_info = self.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
                    target_name = f"{target_info['first_name']} {target_info['last_name']}"
                except:
                    # если не смогли получить имя
                    target_name = f"ID: {target_id}"
            
            # инфа о беседе, если есть
            chat_info = ""
            if peer_id:
                try:
                    chat_id = peer_id - 2000000000
                    chat_name = f"Беседа #{chat_id}"
                    chat_info = f"\n📢 Беседа: {chat_name}"
                except:
                    chat_info = f"\n📢 Беседа: ID {peer_id}"
            
            # иконки для разных действий
            action_emojis = {
                "kick": "🚪",
                "ban": "🚫",
                "unban": "✅",
                "warn": "⚠️",
                "unwarn": "🔄",
                "mute": "🔇",
                "unmute": "🔊",
                "set_role": "🔰",
                "remove_role": "⛔",
                "quiet": "🤫",
                "delete": "🗑️",
                "message": "💬",
                "start": "🚀",
                "masskick": "👥🚪"
            }
            
            # человеческие названия действий
            action_readable = {
                "kick": "Исключение",
                "ban": "Блокировка",
                "unban": "Разблокировка",
                "warn": "Предупреждение",
                "unwarn": "Снятие предупреждения",
                "mute": "Отключение чата",
                "unmute": "Включение чата",
                "set_role": "Назначение роли",
                "remove_role": "Снятие роли",
                "quiet": "Режим тишины",
                "delete": "Удаление сообщения",
                "message": "Сообщение",
                "start": "Активация бота",
                "masskick": "Массовое исключение"
            }
            
            # собираем лог-сообщение
            emoji = action_emojis.get(action, "ℹ️")
            action_text = action_readable.get(action, action.capitalize())
            
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            
            # шаблон лог-сообщения
            log_message = (
                f"{emoji} {action_text}\n\n"
                f"👮 Модератор: [id{admin_id}|{admin_name}]\n"
            )
            
            # добавляем инфу о юзере если есть
            if target_id:
                log_message += f"👤 Пользователь: [id{target_id}|{target_name}]\n"
                
            # добавляем детали если есть
            if details:
                log_message += f"📋 Детали: {details}\n"
                
            # и инфу о беседе + время
            log_message += f"{chat_info}\n⏱ Время: {timestamp}"
            
            # отправляем в лог-беседу
            result = self.send_message(int(self.log_peer_id), log_message)
            return result is not None
            
        except Exception as e:
            logger.error(f"Не удалось отправить лог: {str(e)}")
            return False

    def is_conversation_member(self, peer_id: int, user_id: int) -> bool:
        # Check if a user is a member of a conversation.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
#
# Returns:
# True if user is a member, False otherwise
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            items = conv_members.get("items", [])
            return any(item.get("member_id") == user_id for item in items)
        except Exception as e:
            logger.error(f"Error fetching conversation members: {str(e)}")
            return False

    def get_conversation_owner(self, peer_id: int) -> Optional[int]:
        # Получить ID создателя беседы.
#
# Аргументы:
# peer_id: ID беседы
#
# Возвращает:
# ID создателя или None, если не найден
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            items = conv_members.get("items", [])
            for item in items:
                if item.get("is_owner", False):
                    return item.get("member_id")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении информации о создателе беседы: {str(e)}")
            return None

    def is_conversation_owner(self, peer_id: int, user_id: int) -> bool:
        # Check if a user is the owner of a conversation.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
#
# Returns:
# True if user is the owner, False otherwise
        owner_id = self.get_conversation_owner(peer_id)
        return owner_id == user_id

    def get_conversation_members(self, peer_id: int) -> List[Dict[str, Any]]:
        # Get all members of a conversation.
#
# Args:
# peer_id: Conversation ID
#
# Returns:
# List of conversation members
        try:
            conv_members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            profiles = conv_members.get("profiles", [])
            return [
                {
                    "id": profile["id"],
                    "first_name": profile["first_name"],
                    "last_name": profile["last_name"],
                    "online": profile.get("online", 0)
                }
                for profile in profiles
            ]
        except Exception as e:
            logger.error(f"Error fetching conversation members: {str(e)}")
            return []

    def get_online_members(self, peer_id: int) -> List[Dict[str, Any]]:
        # Get online members of a conversation.
#
# Args:
# peer_id: Conversation ID
#
# Returns:
# List of online conversation members
        members = self.get_conversation_members(peer_id)
        return [member for member in members if member.get("online", 0) == 1]

    def kick_user(self, peer_id: int, user_id: int) -> bool:
        # Kick a user from a conversation.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
#
# Returns:
# Success status
        try:
            self.vk.messages.removeChatUser(
                chat_id=peer_id - 2000000000,  # Convert peer_id to chat_id
                user_id=user_id
            )
            logger.info(f"Kicked user {user_id} from chat {peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to kick user: {str(e)}")
            return False

    def check_access(self, user_id: int, required_role: str, peer_id: Optional[int] = None) -> bool:
        # Check if a user has the required role.
#
# Args:
# user_id: User ID
# required_role: Required role
# peer_id: Conversation ID (optional, for conversation-specific roles)
#
# Returns:
# True if user has sufficient permissions, False otherwise
        # Если указан peer_id, проверяем роль пользователя в этой беседе
        if peer_id is not None:
            user_role = db.get_role(user_id, peer_id)
        else:
            # Если не указан peer_id, используем глобальную роль
            user = db.get_user(user_id)
            if not user:
                return False
            user_role = user["role"]
            
        return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def has_rights(self, peer_id: int, user_id: int, required_role: str) -> bool:
        # Check if a user has the required rights.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# required_role: Required role
#
# Returns:
# True if user has sufficient rights, False otherwise
        # Conversation owner always has all rights
        is_owner = self.is_conversation_owner(peer_id, user_id)
        has_role_access = self.check_access(user_id, required_role, peer_id)
        return is_owner or has_role_access

    def check_cooldown(self, user_id: int) -> bool:
        # Check if a user is on cooldown.
#
# Args:
# user_id: User ID
#
# Returns:
# True if user is not on cooldown, False otherwise
        now = time.time()
        if user_id in self.last_command_time and now - self.last_command_time[user_id] < self.command_cooldown:
            logger.info(f"User {user_id} is on cooldown.")
            return False
        self.last_command_time[user_id] = now
        return True

    def is_muted(self, user_id: int) -> bool:
        # Check if a user is muted.
#
# Args:
# user_id: User ID
#
# Returns:
# True if user is muted, False otherwise
        mute_until = db.get_mute(user_id)
        now = int(time.time())
        return mute_until > now

    def is_banned(self, user_id: int) -> bool:
        # Check if a user is banned.
#
# Args:
# user_id: User ID
#
# Returns:
# True if user is banned, False otherwise
        return db.get_ban(user_id) is not None
        
    def extract_user_id_from_mention(self, mention: str) -> Optional[int]:
        # Извлечь ID пользователя из различных форматов (упоминание, ID, ссылка).
#
# Аргументы:
# mention: Текст упоминания, ID или ссылка
#
# Возвращает:
# ID пользователя или None, если не найден
        try:
            # Если есть пробелы, обрабатываем только первое слово
            first_word = mention.split()[0] if ' ' in mention else mention
            
            # Проверяем, является ли строка числом (прямое указание ID)
            if first_word.isdigit():
                return int(first_word)
                
            # Обрабатываем упоминание формата [id123456789|Имя]
            if first_word.startswith("[") and "|" in first_word and "]" in first_word:
                # Извлекаем часть между "id" и "|"
                start_idx = first_word.find("id") + 2
                end_idx = first_word.find("|")
                if start_idx > 1 and end_idx > start_idx:
                    user_id_str = first_word[start_idx:end_idx]
                    if user_id_str.isdigit():
                        return int(user_id_str)
            
            # Проверка на случай, когда указана ссылка на профиль вида vk.com/id123456 или https://vk.com/id123456
            vk_url_patterns = [
                r"(?:https?://)?(?:www\.)?vk\.com/id(\d+)",  # https://vk.com/id123456
                r"(?:https?://)?(?:www\.)?vk\.me/id(\d+)",    # https://vk.me/id123456
                r"(?:https?://)?(?:www\.)?vk\.com/.*"         # Другие форматы ссылок vk.com/username
            ]
            
            for pattern in vk_url_patterns:
                import re
                match = re.match(pattern, first_word)
                if match:
                    # Если найден ID в формате vk.com/id123456
                    if len(match.groups()) > 0 and match.group(1).isdigit():
                        return int(match.group(1))
                    else:
                        # Пытаемся получить ID из короткого имени (screen_name)
                        try:
                            # Извлекаем screen_name из ссылки
                            parts = first_word.split("/")
                            screen_name = parts[-1]
                            if screen_name:
                                user_info = self.vk.users.get(user_ids=screen_name)
                                if user_info and len(user_info) > 0:
                                    return user_info[0]["id"]
                        except Exception as e:
                            logger.error(f"Ошибка при получении ID из ссылки: {str(e)}")
            
            # Проверка на случай, когда пользователь указал просто @username
            if first_word.startswith("@"):
                screen_name = first_word[1:]
                try:
                    user_info = self.vk.users.get(user_ids=screen_name)
                    if user_info and len(user_info) > 0:
                        return user_info[0]["id"]
                except Exception as e:
                    logger.error(f"Ошибка при получении ID из @username: {str(e)}")
            
            # Если не смогли распознать по первой части сообщения и есть пробелы, 
            # попробуем поискать во всей строке
            if ' ' in mention:
                # Попробуем найти в тексте упоминание [id123|Name]
                import re
                id_match = re.search(r'\[id(\d+)\|[^\]]+\]', mention)
                if id_match:
                    return int(id_match.group(1))
                
                # Попробуем найти имя пользователя после символа @
                at_match = re.search(r'@(\w+)', mention)
                if at_match:
                    screen_name = at_match.group(1)
                    try:
                        user_info = self.vk.users.get(user_ids=screen_name)
                        if user_info and len(user_info) > 0:
                            return user_info[0]["id"]
                    except Exception as e:
                        logger.error(f"Ошибка при получении ID из @username в полном тексте: {str(e)}")
                    
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении ID из упоминания: {str(e)}")
            return None
            
    def get_user_id_from_reply(self, message) -> Optional[int]:
        # Получить ID пользователя из ответа на сообщение.
#
# Аргументы:
# message: Объект сообщения
#
# Возвращает:
# ID пользователя или None, если не найден
        try:
            # Проверяем, есть ли у сообщения поле reply_message
            if "reply_message" in message:
                reply = message["reply_message"]
                if "from_id" in reply:
                    return reply["from_id"]
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении ID из ответа: {str(e)}")
            return None

    def handle_message(self, event):
        # Обрабатывает входящее сообщение.
#
# Аргументы:
# event: Событие от VK API
        message = event.obj.message
        peer_id = message['peer_id']
        user_id = message['from_id']
        text = message.get('text', '').strip()
        
        # добавляем юзера если его нет
        db.add_user(user_id)
        
        # счётчик сообщений
        db.update_message_count(user_id)
        
        # это команда или обычное сообщение
        if text.startswith('/'):
            # отдаём на обработку команд
            self.handle_command(peer_id, user_id, text, message)
        else:
            # логи сообщений для админов
            if self.log_peer_id and peer_id > 2000000000:  # не логируем личку
                log_text = text
                # обрезаем если длинное
                if len(log_text) > 100:
                    log_text = log_text[:97] + "..."
                
                # отправляем в лог-беседу
                self.send_log_message(
                    action="message",
                    admin_id=user_id,  # тут просто отправитель
                    peer_id=peer_id,
                    details=log_text
                )
            
            # проверка на мут пользователя
            if self.is_muted(user_id) and not self.check_access(user_id, "moderator"):
                mute_until = db.get_mute(user_id)
                time_left = mute_until - int(time.time())
                # если мут ещё активен
                if time_left > 0:
                    # удаляем сообщение
                    message_id = message.get('id')
                    if message_id:
                        # пробуем удалить
                        if not self.delete_message(peer_id, message_id):
                            logger.error(f"Не могу удалить сообщение {message_id}")
                    
                    # пишем напоминание о муте
                    self.send_message(
                        peer_id, 
                        f"[id{user_id}|Пользователь], вы в муте. "
                        f"Осталось: {format_time_delta(time_left)}"
                    )

    def handle_command(self, peer_id: int, user_id: int, text: str, message=None):
        # Обрабатывает команды от пользователей.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# text: Текст команды
# message: Объект сообщения для обработки ответов
        # парсим команду
        command, args = parse_command(text)
        
        # проверка на тихий режим
        is_owner = self.is_conversation_owner(peer_id, user_id)
        if self.quiet_mode and not self.check_access(user_id, "moderator") and not is_owner:
            logger.info(f"Игнор команды от {user_id} в тихом режиме")
            return
            
        # антиспам защита
        if not self.check_cooldown(user_id):
            self.send_message(peer_id, f"[id{user_id}|Пользователь], харош спамить!")
            return
            
        # проверка на существование команды
        if not self.commands.has_command(command):
            return
        
        # достаем ID из ответа на сообщение
        cmd_requires_target = ["warn", "unwarn", "getwarn", "warnhistory", "kick", "ban", "unban", 
                             "mute", "unmute", "getmute", "setnick", "removenick", "getnick", 
                             "getacc", "chek", "getban", "reg", "addmoder", "addsenmoder", 
                             "addadmin", "removerole", "removeadmin", "stats"]
        
        if message and command in cmd_requires_target:
            # если есть ответ и нет явного ID/упоминания
            if "reply_message" in message and (not args or (not args[0].isdigit() and not args.startswith("[") and not args.startswith("@"))):
                target_id = self.get_user_id_from_reply(message)
                if target_id:
                    # команды только с ID (без доп. параметров)
                    if command in ["unwarn", "getwarn", "warnhistory", "kick", "unban", "unmute", "getmute", "removenick", "getnick", "chek", "getban", "reg", "stats"]:
                        args = str(target_id) + (" " + args if args else "")
                    # команды с ID + дополнительными параметрами
                    elif args and command in ["warn", "ban", "mute", "setnick", "addmoder", "addsenmoder", "addadmin", "removerole", "removeadmin"]:
                        args = str(target_id) + " " + args
                    else:
                        # если нужны доп параметры но их нет
                        if command in ["warn", "ban", "mute", "setnick", "addmoder", "addsenmoder", "addadmin", "removerole", "removeadmin"]:
                            msg = "❗ Укажи "
                            if command == "warn" or command == "ban":
                                msg += "причину."
                            elif command == "mute":
                                msg += "длительность и причину."
                            elif command == "setnick":
                                msg += "никнейм."
                            elif command in ["addmoder", "addsenmoder", "addadmin", "removerole", "removeadmin"]:
                                msg += "причину назначения или снятия роли."
                            self.send_message(peer_id, msg)
                            return
                        else:
                            args = str(target_id)
            
        # обработка упоминаний @username и [id123|name]
        if args and command in cmd_requires_target:
            parts = args.split(" ", 1)
            first_arg = parts[0]
            
            # проверяем форматы упоминаний
            if (first_arg.startswith("[") and "|" in first_arg) or first_arg.startswith("@"):
                target_id = self.extract_user_id_from_mention(first_arg)
                if target_id:
                    # заменяем упоминание на ID
                    if len(parts) > 1:
                        args = str(target_id) + " " + parts[1]
                    else:
                        args = str(target_id)
            
        # выполняем команду (не блокируя основной поток)
        self.executor.submit(
            self.commands.execute_command,
            command, peer_id, user_id, args
        )

    def process_events(self):
        # Основной цикл обработки событий от VK API.
        try:
            for event in self.longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    # отдельный поток чтобы не блокировать основной
                    self.executor.submit(self.handle_message, event)
                    
                # можно добавить обработку других событий по мере надобности
                # например MessageEdit, ChatLeave и т.д.
        except Exception as e:
            logger.error(f"Блин, ошибка в событиях: {str(e)}")
            # перезапуск через 5 сек при обрыве
            time.sleep(5)

    def process_delete_queue(self):
        # Обработчик очереди сообщений на удаление.
        while True:
            try:
                # не чаще раза в секунду
                time.sleep(1)  
                
                # забираем на обработку то что есть сейчас
                with self.delete_lock:
                    messages_to_delete = self.delete_queue.copy()
                    self.delete_queue = []
                
                # удаляем все из очереди
                for peer_id, message_id in messages_to_delete:
                    self.delete_message(peer_id, message_id)
            except Exception as e:
                logger.error(f"Не могу разобрать очередь удаления: {str(e)}")
                time.sleep(5)

    def start_polling(self):
        # Запуск бота.
        # поток для очереди удаления
        threading.Thread(
            target=self.process_delete_queue, 
            daemon=True
        ).start()
        
        # основной цикл
        while True:
            try:
                self.process_events()
            except Exception as e:
                logger.error(f"Основной цикл упал: {str(e)}")
                time.sleep(5)  # пауза перед перезапуском
