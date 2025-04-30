import logging
import time
import re
import threading
from typing import Dict, List, Tuple, Callable, Any, Optional, Union

import database as db
from utils import parse_time, format_time_delta, ROLE_HIERARCHY

logger = logging.getLogger(__name__)

class CommandRegistry:
    # Реестр команд для VK бота.
    # Обрабатывает регистрацию и выполнение команд.
    def __init__(self, bot):
        # Инициализация реестра команд.
#
# Аргументы:
# bot: Экземпляр VK бота
        self.bot = bot
        self.commands = {}
        self.register_commands()
        logger.info("Command registry initialized")

    def register_command(self, name: str, handler: Callable, required_role: str = "user"):
        # Регистрация команды.
#
# Аргументы:
# name: Имя команды
# handler: Функция-обработчик команды
# required_role: Необходимая роль для выполнения команды
        self.commands[name] = {
            "handler": handler,
            "required_role": required_role
        }
        logger.info(f"Registered command: {name} (required role: {required_role})")

    def has_command(self, name: str) -> bool:
        # Проверка существования команды.
#
# Аргументы:
# name: Имя команды
#
# Возвращает:
# True если команда существует, False в противном случае
        return name in self.commands

    def execute_command(self, name: str, peer_id: int, user_id: int, args: str):
        # Выполнение команды.
#
# Аргументы:
# name: Имя команды
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        if not self.has_command(name):
            return
            
        command = self.commands[name]
        required_role = command["required_role"]
        
        # Check if user has required role
        if not self.bot.has_rights(peer_id, user_id, required_role):
            self.bot.send_message(
                peer_id, 
                f"❗ [id{user_id}|Пользователь], у вас недостаточно прав для использования этой команды."
            )
            return
            
        # Execute command
        try:
            command["handler"](peer_id, user_id, args)
            logger.info(f"Executed command {name} with args: {args}")
        except Exception as e:
            logger.error(f"Error executing command {name}: {str(e)}", exc_info=True)
            self.bot.send_message(
                peer_id, 
                f"❗ Произошла ошибка при выполнении команды: {str(e)}"
            )

    def register_commands(self):
        # Регистрация всех команд бота.
        # Команды пользователя
        self.register_command("help", self.cmd_help)
        self.register_command("start", self.cmd_start, "user")
        self.register_command("stats", self.cmd_stats)
        self.register_command("getid", self.cmd_getid)
        
        # Команды модератора
        self.register_command("chek", self.cmd_chek, "moderator")
        self.register_command("setnick", self.cmd_setnick, "moderator")
        self.register_command("removenick", self.cmd_removenick, "moderator")
        self.register_command("getnick", self.cmd_getnick, "moderator")
        self.register_command("getacc", self.cmd_getacc, "moderator")
        self.register_command("nlist", self.cmd_nlist, "moderator")
        self.register_command("nonick", self.cmd_nonick, "moderator")
        self.register_command("kick", self.cmd_kick, "moderator")
        self.register_command("warn", self.cmd_warn, "moderator")
        self.register_command("unwarn", self.cmd_unwarn, "moderator")
        self.register_command("getwarn", self.cmd_getwarn, "moderator")
        self.register_command("warnhistory", self.cmd_warnhistory, "moderator")
        self.register_command("warnlist", self.cmd_warnlist, "moderator")
        self.register_command("staff", self.cmd_staff, "moderator")
        self.register_command("reg", self.cmd_reg, "moderator")
        self.register_command("mute", self.cmd_mute, "moderator")
        self.register_command("unmute", self.cmd_unmute, "moderator")
        self.register_command("getmute", self.cmd_getmute, "moderator")
        self.register_command("mutelist", self.cmd_mutelist, "moderator")
        self.register_command("clear", self.cmd_clear, "moderator")
        self.register_command("getban", self.cmd_getban, "moderator")
        self.register_command("delete", self.cmd_delete, "moderator")
        
        # Команды старшего модератора
        self.register_command("ban", self.cmd_ban, "senior_moderator")
        self.register_command("unban", self.cmd_unban, "senior_moderator")
        self.register_command("addmoder", self.cmd_addmoder, "senior_moderator")
        self.register_command("removerole", self.cmd_removerole, "senior_moderator")
        self.register_command("zov", self.cmd_zov, "senior_moderator")
        self.register_command("online", self.cmd_online, "senior_moderator")
        self.register_command("onlinelist", self.cmd_onlinelist, "senior_moderator")
        self.register_command("banlist", self.cmd_banlist, "senior_moderator")
        self.register_command("inactivelist", self.cmd_inactivelist, "senior_moderator")
        self.register_command("masskick", self.cmd_masskick, "senior_moderator")
        
        # Команды администратора
        # Команда quiet доступна администраторам и создателям (проверка также в самой команде)
        self.register_command("quiet", self.cmd_quiet, "admin")
        self.register_command("addsenmoder", self.cmd_addsenmoder, "admin")
        
        # Команды создателя
        self.register_command("addadmin", self.cmd_addadmin, "creator")
        self.register_command("removeadmin", self.cmd_removeadmin, "creator")

    # ===================== Command Handlers =====================

    def cmd_help(self, peer_id: int, user_id: int, args: str):
        # Отображение информации о командах.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        # Определяем роль пользователя
        user_role = db.get_role(user_id, peer_id)
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
            
        header = f"🌟 Команды доступные для [id{user_id}|{user_name}] 🌟\n\n"
        
        user_cmds = (
            "👤 Основные команды:\n"
            "• /help — список команд\n"
            "• /start — активация бота\n"
            "• /stats — личная статистика\n"
            "• /getid — узнать свой ID\n\n"
        )
        
        usage_note = (
            "📌 Примечание: вместо ID пользователя можно:\n"
            "• Отвечать на сообщение пользователя\n"
            "• Упоминать пользователя через @username\n"
            "• Использовать упоминание [id123456|Имя]\n"
            "• Указать ссылку на профиль vk.com/id123456\n\n"
        )
        
        moder_cmds = (
            "👮 Команды модерации:\n"
            "• /kick @user — кик участника\n"
            "• /warn @user причина — выдать предупреждение\n"
            "• /unwarn @user — снять предупреждение\n"
            "• /getwarn @user — проверить предупреждения\n"
            "• /mute @user время причина — выдать мут\n"
            "• /unmute @user — снять мут\n"
            "• /getmute @user — проверить мут\n"
            "• /clear число — очистить сообщения\n"
            "• /delete ID — удалить сообщение\n\n"
            
            "👥 Управление беседой:\n"
            "• /setnick @user ник — установить никнейм\n"
            "• /removenick @user — удалить никнейм\n"
            "• /getnick @user — получить никнейм\n"
            "• /getacc ник — найти по никнейму\n"
            "• /staff — список персонала\n"
            "• /nlist — участники с никнеймами\n"
            "• /chek @user — проверить блокировку\n"
            "• /getban @user — информация о бане\n"
            "• /reg @user — дата регистрации\n\n"
        )
        
        senmoder_cmds = (
            "⭐ Команды ст. модератора:\n"
            "• /ban @user причина — забанить пользователя\n"
            "• /unban @user — разбанить пользователя\n"
            "• /addmoder @user — назначить модератором\n"
            "• /removerole @user — снять роль\n"
            "• /zov причина — позвать всех\n"
            "• /online — показать онлайн\n"
            "• /onlinelist — список онлайн\n"
            "• /banlist — список забаненных\n"
            "• /inactivelist дни — неактивные участники\n"
            "• /masskick ID1 ID2 — массовый кик\n\n"
        )
        
        admin_cmds = (
            "👑 Команды администратора:\n"
            "• /quiet — режим тишины\n"
            "• /addsenmoder @user — назначить ст. модератором\n\n"
        )
        
        creator_cmds = (
            "🔱 Команды создателя:\n"
            "• /addadmin @user — назначить администратором\n"
            "• /removeadmin @user — снять администратора\n\n"
        )
        
        # Составляем сообщение в зависимости от роли пользователя
        msg = header + user_cmds
        
        if ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get("moderator", 0):
            msg += usage_note + moder_cmds
            
        if ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get("senior_moderator", 0):
            msg += senmoder_cmds
            
        if ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get("admin", 0):
            msg += admin_cmds
            
        if ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get("creator", 0):
            msg += creator_cmds
        
        self.bot.send_message(peer_id, msg)
        
    def _get_role_name(self, role: str, with_emoji: bool = True) -> str:
        # Получить человекочитаемое название роли
#
# Аргументы:
# role: Код роли
# with_emoji: Включать ли эмодзи в название
#
# Возвращает:
# Человекочитаемое название роли
        role_emojis = {
            "creator": "🔱",
            "admin": "👑",
            "senior_moderator": "⭐",
            "moderator": "👮",
            "user": "👤"
        }
        
        role_names = {
            "creator": "Создатель",
            "admin": "Администратор",
            "senior_moderator": "Старший модератор",
            "moderator": "Модератор",
            "user": "Пользователь"
        }
        
        emoji = role_emojis.get(role, "👤") + " " if with_emoji else ""
        name = role_names.get(role, "Пользователь")
        
        return f"{emoji}{name}"

    def cmd_start(self, peer_id: int, user_id: int, args: str):
        # Инициализация бота в беседе.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        is_owner = self.bot.is_conversation_owner(peer_id, user_id)
        
        # Проверим, активирован ли бот уже в этой беседе
        conversation_staff = db.get_staff(peer_id)
        if conversation_staff:
            # Бот уже активирован
            self.bot.send_message(
                peer_id, 
                "🔔 Бот уже активирован в этой беседе!\n\n"
                "Для просмотра списка сотрудников используйте команду /staff\n"
                "Для просмотра доступных команд используйте /help"
            )
            return
        
        # Проверяем, имеет ли пользователь права для активации бота
        if is_owner or self.bot.check_access(user_id, "creator"):
            # Пользователь имеет права - активируем бота
            # Если пользователь - владелец беседы, делаем его создателем бота в этой беседе
            try:
                # Получаем информацию о пользователе
                user_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                user_name = "Пользователь"
                
            if is_owner:
                db.set_role(user_id, "creator", peer_id)
                # Отправляем сообщение об активации
                self.bot.send_message(
                    peer_id, 
                    f"🎉 Бот успешно активирован в этой беседе!\n\n"
                    f"👑 [id{user_id}|{user_name}] назначен создателем бота как владелец беседы.\n\n"
                    f"📋 Используйте команду /help для просмотра доступных команд."
                )
                
                # Логируем активацию бота
                self.bot.send_log_message(
                    action="start",
                    admin_id=user_id,
                    peer_id=peer_id,
                    details="Владелец беседы назначен создателем бота"
                )
            else:
                # Отправляем сообщение об активации
                self.bot.send_message(
                    peer_id, 
                    f"🎉 Бот успешно активирован в этой беседе!\n\n"
                    f"📋 Используйте команду /help для просмотра доступных команд."
                )
                
                # Логируем активацию бота
                self.bot.send_log_message(
                    action="start",
                    admin_id=user_id,
                    peer_id=peer_id,
                    details="Активация бота администратором"
                )
        else:
            # Пользователь не имеет необходимых прав
            # Получаем информацию о пользователе через VK API
            try:
                user_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                user_name = "Пользователь"
                
            self.bot.send_message(
                peer_id, 
                f"⛔ [id{user_id}|{user_name}], активация не удалась!\n\n"
                f"❗️ У бота недостаточно прав администратора в беседе.\n\n"
                f"👑 Попросите владельца беседы назначить бота администратором и затем введите команду /start снова."
            )

    def cmd_stats(self, peer_id: int, user_id: int, args: str):
        # Отображение статистики пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        # Проверяем, указан ли ID пользователя в аргументах
        target_id = user_id  # По умолчанию показываем статистику запросившего
        if args:
            extracted_id = self.bot.extract_user_id_from_mention(args)
            if extracted_id:
                target_id = extracted_id
            else:
                self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание или ID.")
                return
        
        user = db.get_user(target_id)
        if user:
            reg_date = time.strftime('%d.%m.%Y в %H:%M', time.localtime(user["reg_date"]))
            
            # Получаем роль в текущей беседе
            peer_role = db.get_role(target_id, peer_id)
            
            # Получаем эмодзи роли
            role_emoji = self._get_role_name(peer_role).split(' ')[0]
            
            # Получаем русское название роли
            role_name = self._get_role_name(peer_role, with_emoji=False)
            
            # Получаем информацию о пользователе через VK API включая дату регистрации (date)
            try:
                user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
                
                # Просто переменная с именем пользователя для сообщения
            except Exception as e:
                logger.error(f"Ошибка при получении данных пользователя: {str(e)}")
                user_name = user['nickname'] or f"ID: {target_id}"

            
            # Форматируем сообщение
            msg = (
                f"📊 Профиль пользователя [id{user['user_id']}|{user_name}]\n\n"
                f"🆔 ID: {user['user_id']}\n"
                f"👤 Никнейм: {user['nickname'] or '⚠️ не установлен'}\n"
                f"{role_emoji} Роль: {role_name}\n"
                f"💬 Сообщений: {user['messages_count']}\n"
                f"⚠️ Предупреждений: {user['warns']}/3\n"
                f"🕒 Регистрация в боте: {reg_date}"
            )
            self.bot.send_message(peer_id, msg)
        else:
            try:
                user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
                self.bot.send_message(peer_id, f"⚠️ Данные пользователя [id{target_id}|{user_name}] не найдены в базе.")
            except:
                self.bot.send_message(peer_id, f"⚠️ Данные пользователя ID: {target_id} не найдены в базе.")

    def cmd_getid(self, peer_id: int, user_id: int, args: str):
        # Получение ID пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        self.bot.send_message(peer_id, f"📌 Ваш ID: {user_id}")
        
    def cmd_chek(self, peer_id: int, user_id: int, args: str):
        # Проверка бана пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (ID проверяемого пользователя)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите ID пользователя.")
            return
        
        try:
            target_id = int(args.strip())
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректный ID пользователя.")
            return
        
        ban = db.get_ban(target_id)
        if ban:
            ban_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ban["ban_timestamp"]))
            self.bot.send_message(
                peer_id, 
                f"🚫 Пользователь [id{target_id}] забанен\n\n"
                f"📋 Причина: {ban['reason']}\n"
                f"⏱ Время бана: {ban_time}"
            )
        else:
            self.bot.send_message(peer_id, f"✅ Пользователь [id{target_id}] не имеет активных банов.")

    def cmd_setnick(self, peer_id: int, user_id: int, args: str):
        # Установка никнейма пользователю.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (ID целевого пользователя и никнейм)
        if not args or ' ' not in args:
            self.bot.send_message(peer_id, "❗ Укажите ID пользователя и никнейм.")
            return
        
        try:
            target_id, nickname = args.strip().split(' ', 1)
            target_id = int(target_id)
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректный ID пользователя.")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        if db.set_nickname(target_id, nickname):
            self.bot.send_message(
                peer_id, 
                f"✅ Никнейм успешно установлен!\n\n"
                f"👤 Пользователь: [id{target_id}]\n"
                f"📝 Новый никнейм: {nickname}"
            )
        else:
            self.bot.send_message(peer_id, f"❌ Не удалось установить никнейм для пользователя [id{target_id}].")

    def cmd_removenick(self, peer_id: int, user_id: int, args: str):
        # Remove nickname from a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите ID пользователя.")
            return
        
        try:
            target_id = int(args.strip())
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректный ID пользователя.")
            return
        
        if db.remove_nickname(target_id):
            self.bot.send_message(peer_id, f"Никнейм пользователя [id{target_id}] удален.")
        else:
            self.bot.send_message(peer_id, f"❗ Не удалось удалить никнейм пользователя [id{target_id}].")

    def cmd_getnick(self, peer_id: int, user_id: int, args: str):
        # Get nickname of a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите ID пользователя.")
            return
        
        try:
            target_id = int(args.strip())
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректный ID пользователя.")
            return
        
        user = db.get_user(target_id)
        if user and user["nickname"]:
            self.bot.send_message(peer_id, f"Никнейм пользователя [id{target_id}]: {user['nickname']}")
        else:
            self.bot.send_message(peer_id, f"У пользователя [id{target_id}] нет никнейма.")

    def cmd_getacc(self, peer_id: int, user_id: int, args: str):
        # Find user by nickname.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (nickname)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите никнейм для поиска.")
            return
        
        nickname = args.strip()
        users = db.find_user_by_nickname(nickname)
        
        if users:
            msg = f"👥 Найдены пользователи с никнеймом '{nickname}':\n\n"
            for user in users:
                role_name = self._get_role_name(user['role'], with_emoji=False)
                msg += f"• [id{user['user_id']}|{user['nickname']}] — {role_name}\n"
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, f"⚠️ Пользователи с никнеймом '{nickname}' не найдены.")

    def cmd_nlist(self, peer_id: int, user_id: int, args: str):
        # List users with nicknames.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        users = db.get_users_with_nicknames()
        
        if users:
            msg = "👥 Пользователи с никнеймами:\n\n"
            for user in users:
                role_name = self._get_role_name(user['role'], with_emoji=False)
                msg += f"• [id{user['user_id']}|{user['nickname']}] — {role_name}\n"
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "⚠️ Пользователи с никнеймами не найдены.")

    def cmd_nonick(self, peer_id: int, user_id: int, args: str):
        # List users without nicknames.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        users = db.get_users_without_nicknames()
        
        if users:
            msg = "👥 Пользователи без никнеймов:\n\n"
            for user in users:
                role_name = self._get_role_name(user['role'], with_emoji=False)
                # Пытаемся получить имя пользователя из VK API
                try:
                    user_info = self.bot.vk.users.get(user_ids=user['user_id'], fields='first_name,last_name')[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID: {user['user_id']}"
                    
                msg += f"• [id{user['user_id']}|{user_name}] — {role_name}\n"
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "✅ Все пользователи имеют никнеймы.")

    def cmd_kick(self, peer_id: int, user_id: int, args: str):
        # Исключить пользователя из беседы.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (ID/упоминание/ссылка на пользователя)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку) для исключения.")
            return
        
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о модераторе
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
        
        # Check if target is staff member
        if self.bot.check_access(target_id, "moderator") and not self.bot.check_access(user_id, "admin"):
            self.bot.send_message(peer_id, f"❗ Вы не можете исключить сотрудника [id{target_id}|{user_name}].")
            return
        
        success = self.bot.kick_user(peer_id, target_id)
        if success:
            # Отправляем сообщение в чат
            self.bot.send_message(
                peer_id, 
                f"🚪 Пользователь исключен\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"👮 Модератор: [id{user_id}|{admin_name}]"
            )
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="kick",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Исключен из беседы"
            )
        else:
            self.bot.send_message(peer_id, f"❗ Не удалось исключить пользователя [id{target_id}|{user_name}].")

    def cmd_warn(self, peer_id: int, user_id: int, args: str):
        # Выдача предупреждения пользователю.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (упоминание/ID/ссылка на пользователя и причина)
        if not args or ' ' not in args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку) и причину предупреждения.")
            return
        
        # Разделяем ввод на первую часть (идентификатор пользователя) и остальное (причина)
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
        reason = parts[1] if len(parts) > 1 else "Не указана"
        
        # Пытаемся извлечь ID из различных форматов (упоминание, ссылка, ID)
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Check if target is staff member
        if self.bot.check_access(target_id, "moderator") and not self.bot.check_access(user_id, "admin"):
            self.bot.send_message(peer_id, "⛔ Вы не можете выдать предупреждение сотруднику.")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Получаем информацию о пользователе
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о том, кто выдал предупреждение
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
            
        warn_count = db.add_warn(target_id, reason)
        self.bot.send_message(
            peer_id, 
            f"⚠️ Выдано предупреждение\n\n"
            f"👤 Пользователь: [id{target_id}|{user_name}]\n"
            f"👮 Модератор: [id{user_id}|{admin_name}]\n"
            f"📋 Причина: {reason}\n"
            f"🔢 Предупреждения: {warn_count}/3"
        )
        
        # Отправляем лог о выдаче предупреждения
        self.bot.send_log_message(
            action="warn",
            admin_id=user_id,
            target_id=target_id,
            peer_id=peer_id,
            details=f"Причина: {reason} (предупреждение {warn_count}/3)"
        )
        
        # Auto-ban if warn count exceeds threshold
        if warn_count >= 3:
            db.ban_user(target_id, f"Автобан: превышение лимита предупреждений ({warn_count})")
            self.bot.send_message(
                peer_id, 
                f"🚫 Пользователь [id{target_id}|{user_name}] автоматически забанен\n"
                f"📌 Причина: превышение лимита предупреждений ({warn_count}/3)"
            )
            
            # Try to kick user from chat
            self.bot.kick_user(peer_id, target_id)
            
            # Отправляем лог о автобане в специальную беседу
            self.bot.send_log_message(
                action="ban",
                admin_id=user_id,  # Формально баннит тот же модератор
                target_id=target_id,
                peer_id=peer_id,
                details=f"Автобан: превышение лимита предупреждений ({warn_count}/3)"
            )

    def cmd_unwarn(self, peer_id: int, user_id: int, args: str):
        # Снятие предупреждения с пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (упоминание/ID/ссылка на пользователя)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(args)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о модераторе
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
            
        warn_count = db.remove_warn(target_id)
        self.bot.send_message(
            peer_id, 
            f"✅ Снято предупреждение\n\n"
            f"👤 Пользователь: [id{target_id}|{user_name}]\n"
            f"👮 Модератор: [id{user_id}|{admin_name}]\n"
            f"🔢 Осталось предупреждений: {warn_count}/3"
        )
        
        # Отправляем лог в специальную беседу
        self.bot.send_log_message(
            action="unwarn",
            admin_id=user_id,
            target_id=target_id,
            peer_id=peer_id,
            details=f"Осталось предупреждений: {warn_count}/3"
        )

    def cmd_getwarn(self, peer_id: int, user_id: int, args: str):
        # Получение информации о предупреждениях пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (упоминание/ID/ссылка на пользователя)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(args)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        warn_count = db.get_warns(target_id)
        
        # Формируем сообщение со статусом
        emoji = "✅" if warn_count == 0 else "⚠️" 
        status = "чист" if warn_count == 0 else f"имеет {warn_count} предупреждений"
        
        self.bot.send_message(
            peer_id, 
            f"{emoji} Проверка предупреждений\n\n"
            f"👤 Пользователь: [id{target_id}|{user_name}]\n"
            f"🔢 Статус: {status}"
        )

    def cmd_warnhistory(self, peer_id: int, user_id: int, args: str):
        # Получение истории предупреждений пользователя.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (упоминание/ID/ссылка на пользователя)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(args)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
        
        warns = db.get_warn_history(target_id)
        
        if warns:
            msg = f"📋 История предупреждений\n\n"
            msg += f"👤 Пользователь: [id{target_id}|{user_name}]\n"
            msg += f"🔢 Всего предупреждений: {len(warns)}\n\n"
            
            for i, warn in enumerate(warns, 1):
                warn_time = time.strftime('%d.%m.%Y в %H:%M', time.localtime(warn["timestamp"]))
                msg += f"{i}. {warn_time}\n📌 Причина: {warn['reason']}\n\n"
                
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(
                peer_id, 
                f"✅ Чистая история\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"📋 Предупреждений нет"
            )

    def cmd_warnlist(self, peer_id: int, user_id: int, args: str):
        # List all warnings.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        warns = db.get_all_warns()
        
        if warns:
            msg = "Список предупреждений:\n"
            for i, warn in enumerate(warns[:20], 1):  # Limit to 20 warnings
                warn_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(warn["timestamp"]))
                
                # Получаем информацию о пользователе через VK API
                try:
                    user_info = self.bot.vk.users.get(user_ids=warn['user_id'], fields='first_name,last_name')[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = warn['nickname'] or f"ID: {warn['user_id']}"
                    
                msg += f"{i}. [id{warn['user_id']}|{user_name}] - {warn_time} - {warn['reason']}\n"
            
            if len(warns) > 20:
                msg += f"\nПоказано 20 из {len(warns)} предупреждений."
                
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "Предупреждения не найдены.")

    def cmd_staff(self, peer_id: int, user_id: int, args: str):
        # Вывод списка сотрудников беседы.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
        # Получаем сотрудников для конкретной беседы
        staff = db.get_staff(peer_id)
        
        # Получаем информацию о владельце беседы
        conversation_owner_id = self.bot.get_conversation_owner(peer_id)
        
        msg = "👥 Список сотрудников беседы\n\n"
        
        # Получаем информацию о владельце беседы, если он есть
        owner_name = None
        if conversation_owner_id:
            # Получаем информацию о пользователе через VK API
            try:
                owner_info = self.bot.vk.users.get(user_ids=conversation_owner_id, fields='first_name,last_name')[0]
                owner_name = f"{owner_info['first_name']} {owner_info['last_name']}"
            except:
                owner_name = "Пользователь"
            
            msg += f"👑 Создатель беседы:\n• [id{conversation_owner_id}|{owner_name}]\n\n"
        
        roles = {
            "creator": "🔱 Создатель бота",
            "admin": "👑 Администратор",
            "senior_moderator": "⭐ Старший модератор",
            "moderator": "👮 Модератор"
        }
        
        if staff:
            for role in ["creator", "admin", "senior_moderator", "moderator"]:
                # Получаем персонал с текущей ролью
                role_staff = [s for s in staff if s["role"] == role]
                
                # Пропускаем создателя беседы, если он уже был показан выше
                role_staff = [s for s in role_staff if not (s['user_id'] == conversation_owner_id and role == "creator")]
                
                if role_staff:
                    msg += f"{roles[role]}:\n"
                    for s in role_staff:
                        # Получаем информацию о пользователе через VK API
                        try:
                            user_info = self.bot.vk.users.get(user_ids=s['user_id'], fields='first_name,last_name')[0]
                            user_name = f"{user_info['first_name']} {user_info['last_name']}"
                        except:
                            user_name = s['nickname'] or "Пользователь"
                        
                        msg += f"• [id{s['user_id']}|{user_name}]\n"
                    msg += "\n"
            
            self.bot.send_message(peer_id, msg)
        else:
            # Если нет сотрудников, но есть создатель беседы, отправляем сообщение только о создателе
            if conversation_owner_id:
                self.bot.send_message(peer_id, msg)
            else:
                self.bot.send_message(peer_id, "⚠️ Сотрудники не найдены в этой беседе.")

    def cmd_reg(self, peer_id: int, user_id: int, args: str):
        # Get registration date for a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return

        # Извлекаем ID пользователя из упоминания или ссылки
        target_id = self.bot.extract_user_id_from_mention(args)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
            
            # Получаем дату регистрации в боте
            user = db.get_user(target_id)
            if user:
                bot_reg_date = time.strftime('%d.%m.%Y в %H:%M', time.localtime(user["reg_date"]))
            else:
                bot_reg_date = "Не зарегистрирован в боте"
                
            # Формируем сообщение с информацией
            self.bot.send_message(
                peer_id,
                f"📅 Информация о регистрации\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"🤖 Регистрация в боте: {bot_reg_date}"
            )
        except Exception as e:
            logger.error(f"Ошибка при получении данных о регистрации: {str(e)}")
            self.bot.send_message(peer_id, f"❗ Произошла ошибка при получении данных пользователя [id{target_id}].")

    def cmd_mute(self, peer_id: int, user_id: int, args: str):
        # Отключить пользователю возможность писать в чат на определенное время.
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды (упоминание/ID/ссылка, время мута, причина)
        args_parts = args.strip().split(' ', 2)
        if len(args_parts) < 3:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку), время мута (30m, 2h, 1d) и причину.")
            return
            
        # Пытаемся извлечь ID из различных форматов (упоминание, ссылка, ID)
        target_id = self.bot.extract_user_id_from_mention(args_parts[0])
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
            
        duration_str = args_parts[1]
        reason = args_parts[2]
        
        # Check if target is staff member
        if self.bot.check_access(target_id, "moderator") and not self.bot.check_access(user_id, "admin"):
            self.bot.send_message(peer_id, "❗ Вы не можете замьютить сотрудника.")
            return
        
        # Parse duration
        try:
            duration = parse_time(duration_str)
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректное время мута (например, 30m, 2h, 1d).")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Получаем информацию о пользователе
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о модераторе
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
            
        # Set mute
        mute_until = db.set_mute(target_id, duration, reason)
        mute_until_str = time.strftime('%d.%m.%Y в %H:%M', time.localtime(mute_until))
        
        self.bot.send_message(
            peer_id, 
            f"🔇 Пользователь замьючен\n\n"
            f"👤 Пользователь: [id{target_id}|{user_name}]\n"
            f"👮 Модератор: [id{user_id}|{admin_name}]\n"
            f"📋 Причина: {reason}\n"
            f"⏱ Длительность: {format_time_delta(duration)}\n"
            f"🕒 До: {mute_until_str}"
        )
        
        # Отправляем лог в специальную беседу
        self.bot.send_log_message(
            action="mute",
            admin_id=user_id,
            target_id=target_id,
            peer_id=peer_id,
            details=f"Причина: {reason}, Длительность: {format_time_delta(duration)}, До: {mute_until_str}"
        )

    def cmd_unmute(self, peer_id: int, user_id: int, args: str):
        # Unmute a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
        
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        success = db.remove_mute(target_id)
        if success:
            self.bot.send_message(peer_id, f"🔊 Мут снят с пользователя [id{target_id}].")
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="unmute",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Снят мут в беседе"
            )
        else:
            self.bot.send_message(peer_id, f"ℹ️ Пользователь [id{target_id}] не был в муте.")

    def cmd_getmute(self, peer_id: int, user_id: int, args: str):
        # Get mute information for a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
        
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
        
        mute_until = db.get_mute(target_id)
        now = int(time.time())
        
        if mute_until > now:
            time_left = mute_until - now
            mute_until_str = time.strftime('%d.%m.%Y в %H:%M', time.localtime(mute_until))
            self.bot.send_message(
                peer_id, 
                f"🔇 Информация о муте\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"🕒 До: {mute_until_str}\n"
                f"⏱ Осталось: {format_time_delta(time_left)}"
            )
        else:
            self.bot.send_message(peer_id, f"✅ Пользователь [id{target_id}|{user_name}] не в муте.")

    def cmd_mutelist(self, peer_id: int, user_id: int, args: str):
        # List muted users.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        muted_users = db.get_muted_users()
        
        if muted_users:
            msg = "🔇 Пользователи в муте:\n\n"
            now = int(time.time())
            
            for user in muted_users:
                # Получаем информацию о пользователе через VK API
                try:
                    user_info = self.bot.vk.users.get(user_ids=user['user_id'], fields='first_name,last_name')[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = user['nickname'] or f"ID: {user['user_id']}"
                
                time_left = user["mute_until"] - now
                msg += f"👤 [id{user['user_id']}|{user_name}] - "
                msg += f"осталось {format_time_delta(time_left)}\n"
            
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "✅ Нет пользователей в муте.")

    def cmd_clear(self, peer_id: int, user_id: int, args: str):
        # Clear messages.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (number of messages)
        try:
            count = int(args.strip()) if args else 10
            count = min(max(1, count), 50)  # Limit between 1 and 50
        except ValueError:
            count = 10
        
        self.bot.send_message(
            peer_id, 
            f"🔄 Начинаю очистку {count} сообщений..."
        )
        
        try:
            # Get conversation history
            history = self.bot.vk.messages.getHistory(
                peer_id=peer_id,
                count=count + 1  # +1 to include the command itself
            )
            
            # Extract message IDs
            message_ids = [item["id"] for item in history["items"]]
            
            # Delete messages
            if message_ids:
                self.bot.vk.messages.delete(
                    message_ids=message_ids,
                    delete_for_all=True
                )
                
                self.bot.send_message(
                    peer_id, 
                    f"✅ Удалено {len(message_ids)} сообщений."
                )
        except Exception as e:
            logger.error(f"Error clearing messages: {str(e)}")
            self.bot.send_message(
                peer_id, 
                f"❗ Произошла ошибка при очистке сообщений: {str(e)}"
            )

    def cmd_getban(self, peer_id: int, user_id: int, args: str):
        # Get ban information for a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
        
        ban = db.get_ban(target_id)
        if ban:
            ban_time = time.strftime('%d.%m.%Y в %H:%M', time.localtime(ban["ban_timestamp"]))
            self.bot.send_message(
                peer_id, 
                f"🚫 Информация о блокировке\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"📋 Причина: {ban['reason']}\n"
                f"⏱ Время бана: {ban_time}"
            )
        else:
            self.bot.send_message(peer_id, f"✅ Пользователь [id{target_id}|{user_name}] не заблокирован.")

    def cmd_delete(self, peer_id: int, user_id: int, args: str):
        # Delete a message.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (message ID)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите ID сообщения.")
            return
        
        try:
            message_id = int(args.strip())
        except ValueError:
            self.bot.send_message(peer_id, "❗ Укажите корректный ID сообщения.")
            return
        
        if self.bot.delete_message(peer_id, message_id):
            self.bot.send_message(peer_id, f"✅ Сообщение {message_id} удалено.")
        else:
            self.bot.send_message(peer_id, f"❗ Не удалось удалить сообщение {message_id}.")

    def cmd_ban(self, peer_id: int, user_id: int, args: str):
        # Ban a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID/mention/link and reason)
        if not args or ' ' not in args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку) и причину бана.")
            return
        
        # Разделяем ввод на первую часть (идентификатор пользователя) и остальное (причина)
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
        reason = parts[1] if len(parts) > 1 else "Не указана"
        
        # Пытаемся извлечь ID из различных форматов (упоминание, ссылка, ID)
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о модераторе
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
        
        # Check if target is staff member
        if self.bot.check_access(target_id, "moderator") and not self.bot.check_access(user_id, "admin"):
            self.bot.send_message(peer_id, f"❗ Вы не можете забанить сотрудника [id{target_id}|{user_name}].")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Ban user
        if db.ban_user(target_id, reason):
            ban_time = time.strftime('%d.%m.%Y в %H:%M', time.localtime(int(time.time())))
            self.bot.send_message(
                peer_id, 
                f"🚫 Пользователь заблокирован\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"👮 Модератор: [id{user_id}|{admin_name}]\n"
                f"📋 Причина: {reason}\n"
                f"⏱ Время бана: {ban_time}"
            )
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="ban",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details=f"Причина: {reason}"
            )
            
            # Try to kick user from chat
            self.bot.kick_user(peer_id, target_id)
        else:
            self.bot.send_message(peer_id, f"❗ Не удалось забанить пользователя [id{target_id}|{user_name}].")

    def cmd_unban(self, peer_id: int, user_id: int, args: str):
        # Unban a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Получаем информацию о пользователе через VK API
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID: {target_id}"
            
        # Получаем информацию о модераторе
        try:
            admin_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            admin_name = f"{admin_info['first_name']} {admin_info['last_name']}"
        except:
            admin_name = f"ID: {user_id}"
        
        success = db.unban_user(target_id)
        if success:
            self.bot.send_message(
                peer_id,
                f"✅ Пользователь разблокирован\n\n"
                f"👤 Пользователь: [id{target_id}|{user_name}]\n"
                f"👮 Модератор: [id{user_id}|{admin_name}]\n"
                f"📝 Действие: Разблокировка в системе бота"
            )
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="unban",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Снята блокировка пользователя"
            )
        else:
            self.bot.send_message(peer_id, f"❗ Пользователь [id{target_id}|{user_name}] не был заблокирован.")

    def cmd_addmoder(self, peer_id: int, user_id: int, args: str):
        # Add moderator role to a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Получаем информацию о пользователе через VK API для отображения имени
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
        
        # Устанавливаем роль для конкретной беседы
        success = db.set_role(target_id, "moderator", peer_id)
        if success:
            self.bot.send_message(
                peer_id, 
                f"👮 Новый модератор\n\n"
                f"👤 [id{target_id}|{user_name}] назначен модератором в этой беседе."
            )
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="set_role",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Назначен модератором"
            )
        else:
            self.bot.send_message(
                peer_id, 
                f"❗ Не удалось назначить [id{target_id}|{user_name}] модератором."
            )

    def cmd_removerole(self, peer_id: int, user_id: int, args: str):
        # Remove role from a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Проверяем роль пользователя в этой беседе
        target_role = db.get_role(target_id, peer_id)
        if target_role == "user":
            self.bot.send_message(peer_id, f"❗ Пользователь [id{target_id}] не имеет специальной роли в этой беседе.")
            return
        
        # Проверяем, имеет ли инициатор более высокую роль, чем цель
        initiator_role = db.get_role(user_id, peer_id)
        if ROLE_HIERARCHY.get(target_role, 0) >= ROLE_HIERARCHY.get(initiator_role, 0):
            self.bot.send_message(peer_id, "❗ Вы не можете снять роль с пользователя вашего или более высокого ранга.")
            return
        
        # Получаем информацию о пользователе через VK API для отображения имени
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
        
        # Снимаем роль в конкретной беседе
        success = db.set_role(target_id, "user", peer_id)
        if success:
            self.bot.send_message(
                peer_id, 
                f"🔄 Изменение роли\n\n"
                f"👤 [id{target_id}|{user_name}]\n"
                f"📝 Действие: Роль снята, пользователь стал обычным участником в этой беседе"
            )
            
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="remove_role",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details=f"Снята роль: {target_role}"
            )
        else:
            self.bot.send_message(
                peer_id, 
                f"❗ Не удалось снять роль с пользователя [id{target_id}]."
            )

    def cmd_zov(self, peer_id: int, user_id: int, args: str):
        # Mention all users in the conversation.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        members = self.bot.get_conversation_members(peer_id)
        
        if not members:
            self.bot.send_message(peer_id, "❗ Не удалось получить список участников беседы.")
            return
        
        # Получаем информацию об инициаторе вызова
        try:
            user_info = self.bot.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            caller_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            caller_name = "Пользователь"
        
        # Проверяем, указана ли причина вызова
        reason = args.strip() if args else None
        
        # Mention up to 50 members to avoid message size limits
        mentions = []
        for member in members[:50]:
            # Используем имя и фамилию для упоминаний
            try:
                member_info = self.bot.vk.users.get(user_ids=member['id'], fields='first_name,last_name')[0]
                member_name = f"{member_info['first_name']} {member_info['last_name']}"
                mentions.append(f"[id{member['id']}|{member_name}]")
            except:
                mentions.append(f"[id{member['id']}|@id{member['id']}]")
        
        message = f"🔔 Вы были вызваны [id{user_id}|{caller_name}]\n\n"
        message += "🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤\n\n"
        
        if reason:
            message += f"❗ Причина вызова: {reason}\n\n"
        
        message += f"{' '.join(mentions)}"
        
        self.bot.send_message(peer_id, message)

    def cmd_online(self, peer_id: int, user_id: int, args: str):
        # Show online users count.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        online_members = self.bot.get_online_members(peer_id)
        total_members = self.bot.get_conversation_members(peer_id)
        
        percent = round(len(online_members) / len(total_members) * 100) if total_members else 0
        self.bot.send_message(
            peer_id, 
            f"🟢 Онлайн: {len(online_members)} из {len(total_members)} участников ({percent}%)"
        )

    def cmd_onlinelist(self, peer_id: int, user_id: int, args: str):
        # List online users.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        online_members = self.bot.get_online_members(peer_id)
        
        if online_members:
            msg = "Пользователи онлайн:\n"
            for member in online_members:
                msg += f"[id{member['id']}|{member['first_name']} {member['last_name']}]\n"
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "Нет пользователей онлайн.")

    def cmd_banlist(self, peer_id: int, user_id: int, args: str):
        # List banned users.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        banned_users = db.get_banned_users()
        
        if banned_users:
            msg = "🚫 Список заблокированных пользователей:\n\n"
            for i, user in enumerate(banned_users[:20], 1):  # Limit to 20 users
                # Получаем информацию о пользователе через VK API
                try:
                    user_info = self.bot.vk.users.get(user_ids=user['user_id'], fields='first_name,last_name')[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = user['nickname'] or f"ID: {user['user_id']}"
                    
                ban_time = time.strftime('%d.%m.%Y в %H:%M', time.localtime(user["ban_timestamp"]))
                msg += f"{i}. [id{user['user_id']}|{user_name}] - {ban_time} - {user['reason']}\n"
            
            if len(banned_users) > 20:
                msg += f"\nПоказано 20 из {len(banned_users)} пользователей."
                
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, "✅ Нет заблокированных пользователей.")

    def cmd_inactivelist(self, peer_id: int, user_id: int, args: str):
        # List inactive users.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments
        try:
            days = int(args.strip()) if args else 30
            days = max(1, days)  # Minimum 1 day
        except ValueError:
            days = 30
        
        inactive_users = db.get_inactive_users(days)
        
        if inactive_users:
            msg = f"⏱ Неактивные пользователи (более {days} дней):\n\n"
            for i, user in enumerate(inactive_users[:20], 1):  # Limit to 20 users
                # Получаем информацию о пользователе через VK API
                try:
                    user_info = self.bot.vk.users.get(user_ids=user['user_id'], fields='first_name,last_name')[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = user['nickname'] or f"ID: {user['user_id']}"
                    
                last_activity = time.strftime('%d.%m.%Y', time.localtime(user["last_activity"]))
                msg += f"{i}. [id{user['user_id']}|{user_name}] - последняя активность: {last_activity}\n"
            
            if len(inactive_users) > 20:
                msg += f"\nПоказано 20 из {len(inactive_users)} пользователей."
                
            self.bot.send_message(peer_id, msg)
        else:
            self.bot.send_message(peer_id, f"✅ Нет неактивных пользователей (более {days} дней).")

    def cmd_masskick(self, peer_id: int, user_id: int, args: str):
        # Mass kick users.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (space-separated user IDs)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите ID пользователей для исключения (через пробел).")
            return
        
        target_ids = []
        for id_str in args.strip().split():
            try:
                target_id = int(id_str)
                target_ids.append(target_id)
            except ValueError:
                pass
        
        if not target_ids:
            self.bot.send_message(peer_id, "❗ Не указано ни одного корректного ID пользователя.")
            return
        
        # Limit to 20 users at once
        target_ids = target_ids[:20]
        
        # Start kicking
        self.bot.send_message(peer_id, f"🔄 Начинаю исключение {len(target_ids)} пользователей...")
        
        kicked_count = 0
        for target_id in target_ids:
            # Check if target is staff member
            if self.bot.check_access(target_id, "moderator") and not self.bot.check_access(user_id, "admin"):
                continue
                
            if self.bot.kick_user(peer_id, target_id):
                kicked_count += 1
        
        self.bot.send_message(
            peer_id, 
            f"✅ Исключено {kicked_count} из {len(target_ids)} пользователей."
        )
        
        # Отправляем лог в специальную беседу
        self.bot.send_log_message(
            action="masskick",
            admin_id=user_id,
            peer_id=peer_id,
            details=f"Исключено {kicked_count} из {len(target_ids)} пользователей"
        )

    def cmd_quiet(self, peer_id: int, user_id: int, args: str):
        # Переключить режим "тихо".
#
# Аргументы:
# peer_id: ID беседы
# user_id: ID пользователя
# args: Аргументы команды
#
# Примечание: 
# Эта команда доступна администраторам и создателям беседы
        # Дополнительная проверка для владельца беседы
        is_owner = self.bot.is_conversation_owner(peer_id, user_id)
        
        # Если пользователь не администратор (проверка уже в execute_command), 
        # но является владельцем беседы, разрешаем ему выполнить команду
        if not self.bot.check_access(user_id, "admin") and not self.bot.check_access(user_id, "creator") and not is_owner:
            self.bot.send_message(
                peer_id, 
                f"❗ [id{user_id}|Пользователь], у вас недостаточно прав для использования этой команды."
            )
            return
            
        self.bot.quiet_mode = not self.bot.quiet_mode
        
        if self.bot.quiet_mode:
            self.bot.send_message(
                peer_id, 
                "🔇 Тихий режим включен\n\n"
                "Бот не будет отвечать на команды обычных пользователей."
            )
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="quiet",
                admin_id=user_id,
                peer_id=peer_id,
                details="Тихий режим включен"
            )
        else:
            self.bot.send_message(
                peer_id, 
                "🔊 Тихий режим выключен\n\n"
                "Бот снова отвечает на все команды."
            )
            # Отправляем лог в специальную беседу
            self.bot.send_log_message(
                action="quiet",
                admin_id=user_id,
                peer_id=peer_id,
                details="Тихий режим выключен"
            )

    def cmd_addsenmoder(self, peer_id: int, user_id: int, args: str):
        # Add senior moderator role to a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Получаем информацию о пользователе через VK API для отображения имени
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
        
        # Устанавливаем роль для конкретной беседы
        if db.set_role(target_id, "senior_moderator", peer_id):
            self.bot.send_message(
                peer_id, 
                f"⭐ Новый старший модератор\n\n"
                f"👤 [id{target_id}|{user_name}] назначен старшим модератором в этой беседе."
            )
            
            # Логируем назначение старшего модератора
            self.bot.send_log_message(
                action="set_role",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Назначен старшим модератором"
            )
        else:
            self.bot.send_message(
                peer_id, 
                f"❗ Не удалось назначить [id{target_id}|{user_name}] старшим модератором."
            )

    def cmd_addadmin(self, peer_id: int, user_id: int, args: str):
        # Add admin role to a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Make sure user exists in database
        db.add_user(target_id)
        
        # Получаем информацию о пользователе через VK API для отображения имени
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
        
        # Устанавливаем роль для конкретной беседы
        if db.set_role(target_id, "admin", peer_id):
            self.bot.send_message(
                peer_id, 
                f"👑 Новый администратор\n\n"
                f"👤 [id{target_id}|{user_name}] назначен администратором в этой беседе."
            )
            
            # Логируем назначение администратора
            self.bot.send_log_message(
                action="set_role",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Назначен администратором"
            )
        else:
            self.bot.send_message(
                peer_id, 
                f"❗ Не удалось назначить [id{target_id}|{user_name}] администратором."
            )

    def cmd_removeadmin(self, peer_id: int, user_id: int, args: str):
        # Remove admin role from a user.
#
# Args:
# peer_id: Conversation ID
# user_id: User ID
# args: Command arguments (target user ID, mention or link)
        if not args:
            self.bot.send_message(peer_id, "❗ Укажите пользователя (ID, упоминание или ссылку).")
            return
            
        # Извлекаем первую часть сообщения (до пробела) для поиска ID пользователя
        parts = args.strip().split(' ', 1)
        user_identifier = parts[0]
            
        # Извлекаем ID пользователя из различных форматов
        target_id = self.bot.extract_user_id_from_mention(user_identifier)
        
        # Если не получилось распознать по первой части, пробуем по всей строке
        if not target_id:
            target_id = self.bot.extract_user_id_from_mention(args)
            
        if not target_id:
            self.bot.send_message(peer_id, "❗ Не удалось определить пользователя. Укажите корректное упоминание, ID или ссылку.")
            return
        
        # Проверяем роль пользователя в этой беседе
        user_role = db.get_role(target_id, peer_id)
        if user_role != "admin":
            self.bot.send_message(peer_id, f"❗ Пользователь [id{target_id}] не является администратором в этой беседе.")
            return
        
        # Получаем информацию о пользователе через VK API для отображения имени
        try:
            user_info = self.bot.vk.users.get(user_ids=target_id, fields='first_name,last_name')[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = "Пользователь"
        
        # Снимаем роль в конкретной беседе
        if db.set_role(target_id, "user", peer_id):
            self.bot.send_message(
                peer_id, 
                f"🔽 Снятие администратора\n\n"
                f"👤 [id{target_id}|{user_name}] больше не является администратором в этой беседе."
            )
            
            # Логируем снятие администратора
            self.bot.send_log_message(
                action="remove_role",
                admin_id=user_id,
                target_id=target_id,
                peer_id=peer_id,
                details="Снят с должности администратора"
            )
        else:
            self.bot.send_message(
                peer_id, 
                f"❗ Не удалось снять администратора с пользователя [id{target_id}]."
            )
