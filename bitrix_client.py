# bitrix_client.py
"""
Исправленный клиент для работы с Bitrix24 REST API
Работа с чат-ботами происходит через WEBHOOK (события), а НЕ через polling

Обновлено: 2025
- Добавлены методы для получения списка ботов
- Исправлено удаление ботов с открытых линий
- Исправлено получение открытых линий
"""
import requests
import time
from config import Config


class BitrixClient:
    def __init__(self, domain, db):
        self.domain = domain
        self.db = db
        self.base_url = f"https://{domain}/rest"

    def _get_tokens(self):
        """Получить токены из БД"""
        app = self.db.get_app(self.domain)
        if not app:
            raise Exception("Приложение не установлено")
        return app

    def _refresh_token(self, refresh_token):
        """Обновить access_token"""
        response = requests.post("https://oauth.bitrix.info/oauth/token/", data={
            'grant_type': 'refresh_token',
            'client_id': Config.CLIENT_ID,
            'client_secret': Config.CLIENT_SECRET,
            'refresh_token': refresh_token
        })

        if response.status_code == 200:
            data = response.json()

            self.db.save_app(
                self.domain,
                data['access_token'],
                data['refresh_token'],
                int(time.time()) + data['expires_in'],
                data.get('member_id')
            )

            return data['access_token']
        else:
            raise Exception("Не удалось обновить токен")

    def call(self, method, params=None):
        """Вызов метода Bitrix24 REST API"""
        app = self._get_tokens()
        access_token = app['access_token']

        # Проверка срока действия токена
        if app['expires_at'] and int(time.time()) >= app['expires_at']:
            print(f"[Bitrix API] Токен истёк, обновляем...")
            access_token = self._refresh_token(app['refresh_token'])

        url = f"{self.base_url}/{method}"

        if params is None:
            params = {}

        params['auth'] = access_token

        print(f"[Bitrix API] Вызов: {method}")
        print(f"[Bitrix API] Параметры: {params}")

        response = requests.post(url, json=params)

        print(f"[Bitrix API] HTTP статус: {response.status_code}")
        print(f"[Bitrix API] Ответ: {response.text[:1000]}")

        if response.status_code == 200:
            data = response.json()

            if 'result' in data:
                return data['result']
            elif 'error' in data:
                raise Exception(f"Bitrix API Error: {data['error']} - {data.get('error_description', '')}")
            else:
                return data
        else:
            raise Exception(f"HTTP Error: {response.status_code} - {response.text}")

    # ========================================
    # ЧАТБОТ (imbot.*)
    # ========================================

    def register_chatbot(self, bot_code, bot_name, handler_url, bot_description=None, openline=False):
        """
        Зарегистрировать чат-бота в Bitrix24

        ВАЖНО: handler_url - это URL вашего сервера, куда Bitrix будет отправлять события!

        Args:
            bot_code: Уникальный код бота (латиницей)
            bot_name: Отображаемое имя бота
            handler_url: URL для получения событий (webhook)
            bot_description: Описание бота
            openline: Если True - бот для Открытых Линий (по умолчанию False - внутренний чатбот)

        Returns:
            int: BOT_ID
        """
        params = {
            'CODE': bot_code,
            'TYPE': 'B',  # B = Bot (внутренний чатбот)
            'EVENT_MESSAGE_ADD': handler_url,  # Событие: новое сообщение
            'EVENT_WELCOME_MESSAGE': handler_url,  # Событие: приветствие
            'EVENT_BOT_DELETE': handler_url,  # Событие: удаление бота
            'EVENT_MESSAGE_UPDATE': handler_url,  # Событие: обновление сообщения
            'PROPERTIES': {
                'NAME': bot_name,
                'WORK_POSITION': bot_description or 'AI Assistant',
                'COLOR': 'GREEN'
            }
        }

        # Для бота Открытых Линий
        if openline:
            params['TYPE'] = 'O'  # OpenLine bot
            params['OPENLINE'] = 'Y'

        print(f"[Bitrix] Регистрация бота: CODE={bot_code}, TYPE={params['TYPE']}, NAME={bot_name}")
        print(f"[Bitrix] Handler URL: {handler_url}")
        result = self.call('imbot.register', params)
        print(f"[Bitrix] Бот зарегистрирован: BOT_ID={result}")

        # Подписываемся на события открытых линий
        if openline:
            self._bind_openline_events(handler_url)

        return result

    def _bind_openline_events(self, handler_url):
        """Подписаться на события открытых линий"""
        events = [
            'ONIMBOTMESSAGEADD',
            'ONIMJOINCHAT',
            'ONIMBOTDELETE',
        ]

        for event in events:
            try:
                self.call('event.bind', {
                    'EVENT': event,
                    'HANDLER': handler_url
                })
                print(f"[Bitrix] Подписка на событие {event}: OK")
            except Exception as e:
                print(f"[Bitrix] Ошибка подписки на {event}: {e}")

    def unregister_chatbot(self, bot_id):
        """Удалить бота"""
        return self.call('imbot.unregister', {'BOT_ID': bot_id})

    def get_event_bindings(self):
        """Получить список подписок на события"""
        try:
            return self.call('event.get')
        except Exception as e:
            print(f"[Bitrix] Ошибка получения подписок: {e}")
            return []

    def bind_event(self, event_name, handler_url):
        """Подписаться на событие"""
        return self.call('event.bind', {
            'EVENT': event_name,
            'HANDLER': handler_url
        })

    def unbind_event(self, event_name, handler_url):
        """Отписаться от события"""
        return self.call('event.unbind', {
            'EVENT': event_name,
            'HANDLER': handler_url
        })

    def get_bot_list(self):
        """
        Получить список всех зарегистрированных ботов текущего приложения

        Returns:
            list: Список ботов с их данными
        """
        try:
            result = self.call('imbot.bot.list')
            return result if isinstance(result, list) else result if isinstance(result, dict) else []
        except Exception as e:
            print(f"Ошибка получения списка ботов: {e}")
            return []

    def get_bot_info(self, bot_id):
        """
        Получить подробную информацию о боте

        Args:
            bot_id: ID бота

        Returns:
            dict: Информация о боте
        """
        try:
            result = self.call('imbot.bot.list', {'BOT_ID': bot_id})
            return result
        except Exception as e:
            print(f"Ошибка получения информации о боте: {e}")
            return None

    def update_bot(self, bot_id, handler_url):
        """
        Обновить обработчик событий бота

        Args:
            bot_id: ID бота
            handler_url: Новый URL обработчика
        """
        return self.call('imbot.update', {
            'BOT_ID': bot_id,
            'FIELDS': {
                'EVENT_MESSAGE_ADD': handler_url,
                'EVENT_WELCOME_MESSAGE': handler_url,
                'EVENT_BOT_DELETE': handler_url,
                'EVENT_MESSAGE_UPDATE': handler_url
            }
        })

    def bot_send_message(self, bot_id, dialog_id, message, keyboard=None, attach=None):
        """
        Отправить сообщение от имени бота

        Args:
            bot_id: ID бота
            dialog_id: ID диалога (USER_ID или chatXX)
            message: Текст сообщения
            keyboard: Клавиатура (опционально)
            attach: Вложение (опционально)
        """
        params = {
            'BOT_ID': bot_id,
            'DIALOG_ID': dialog_id,
            'MESSAGE': message
        }

        if keyboard:
            params['KEYBOARD'] = keyboard
        if attach:
            params['ATTACH'] = attach

        return self.call('imbot.message.add', params)

    def bot_update_message(self, bot_id, message_id, new_message):
        """Обновить сообщение бота"""
        return self.call('imbot.message.update', {
            'BOT_ID': bot_id,
            'MESSAGE_ID': message_id,
            'MESSAGE': new_message
        })

    def bot_delete_message(self, bot_id, message_id):
        """Удалить сообщение бота"""
        return self.call('imbot.message.delete', {
            'BOT_ID': bot_id,
            'MESSAGE_ID': message_id
        })

    def bot_typing_start(self, bot_id, dialog_id):
        """Показать индикатор "печатает..." """
        return self.call('imbot.chat.sendTyping', {
            'BOT_ID': bot_id,
            'DIALOG_ID': dialog_id
        })

    # ========================================
    # ОТКРЫТЫЕ ЛИНИИ (imopenlines.*)
    # ========================================

    def openlines_get_config_list(self):
        """
        Получить список всех открытых линий

        Returns:
            list: Список открытых линий с полной информацией
        """
        try:
            # Метод imopenlines.config.list.get возвращает список конфигураций
            result = self.call('imopenlines.config.list.get')

            # Результат может быть списком или словарем
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                # Иногда Bitrix возвращает словарь с ключами
                return list(result.values()) if result else []
            return []
        except Exception as e:
            print(f"Ошибка получения списка открытых линий: {e}")
            return []

    def openlines_get_config(self, config_id):
        """
        Получить информацию о конкретной открытой линии

        Args:
            config_id: ID конфигурации открытой линии

        Returns:
            dict: Данные открытой линии
        """
        try:
            result = self.call('imopenlines.config.get', {
                'CONFIG_ID': config_id
            })
            return result
        except Exception as e:
            print(f"Ошибка получения открытой линии {config_id}: {e}")
            return None

    def openlines_attach_bot(self, openline_id, bot_id):
        """
        Привязать бота к открытой линии

        Args:
            openline_id: ID открытой линии
            bot_id: ID бота
        """
        # Включаем бота И активируем его как приветственного бота
        result = self.call('imopenlines.config.update', {
            'CONFIG_ID': openline_id,
            'FIELDS': {
                'WELCOME_BOT_ENABLE': 'Y',  # Включить приветственного бота
                'WELCOME_BOT_ID': bot_id,    # ID бота для приветствия
                'WELCOME_BOT_JOIN': 'first', # Подключать при первом сообщении
                'WELCOME_BOT_LEFT': 'queue',  # После работы бота - в очередь операторов
                'BOT_ID': bot_id              # Основной бот линии
            }
        })
        print(f"[Bitrix] Бот {bot_id} привязан к линии {openline_id} как приветственный бот")
        return result

    def openlines_detach_bot(self, openline_id):
        """
        Отвязать бота от открытой линии

        Args:
            openline_id: ID открытой линии
        """
        return self.call('imopenlines.config.update', {
            'CONFIG_ID': openline_id,
            'FIELDS': {
                'BOT_ID': 0  # 0 означает отсутствие бота
            }
        })

    def openlines_operator_answer(self, chat_id):
        """Оператор/бот взял диалог в работу"""
        return self.call('imopenlines.operator.answer', {
            'CHAT_ID': chat_id
        })

    def openlines_operator_finish(self, chat_id):
        """Завершить диалог"""
        return self.call('imopenlines.operator.finish', {
            'CHAT_ID': chat_id
        })

    def openlines_operator_transfer(self, chat_id, transfer_id):
        """
        Передать диалог другому оператору

        Args:
            chat_id: ID чата
            transfer_id: ID пользователя или очереди
        """
        return self.call('imopenlines.operator.transfer', {
            'CHAT_ID': chat_id,
            'TRANSFER_ID': transfer_id
        })

    def openlines_session_history(self, session_id):
        """Получить историю сессии"""
        return self.call('imopenlines.session.history.get', {
            'SESSION_ID': session_id
        })

    # ========================================
    # СТАНДАРТНЫЕ СООБЩЕНИЯ (im.*)
    # ========================================

    def im_send_message(self, dialog_id, message):
        """
        Отправить сообщение (от имени текущего пользователя, НЕ бота)

        Args:
            dialog_id: USER_ID или chatXX
            message: Текст
        """
        return self.call('im.message.add', {
            'DIALOG_ID': dialog_id,
            'MESSAGE': message
        })

    def im_get_dialog_messages(self, dialog_id, last_id=0, limit=20):
        """Получить сообщения диалога"""
        return self.call('im.dialog.messages.get', {
            'DIALOG_ID': dialog_id,
            'LAST_ID': last_id,
            'LIMIT': limit
        })

    # ========================================
    # CRM МЕТОДЫ
    # ========================================

    def crm_lead_add(self, fields):
        """Создать лид"""
        return self.call('crm.lead.add', {'fields': fields})

    def crm_lead_get(self, lead_id):
        """Получить лид"""
        return self.call('crm.lead.get', {'id': lead_id})

    def crm_lead_update(self, lead_id, fields):
        """Обновить лид"""
        return self.call('crm.lead.update', {'id': lead_id, 'fields': fields})

    def crm_deal_add(self, fields):
        """Создать сделку"""
        return self.call('crm.deal.add', {'fields': fields})

    def crm_deal_get(self, deal_id):
        """Получить сделку"""
        return self.call('crm.deal.get', {'id': deal_id})

    def crm_deal_update(self, deal_id, fields):
        """Обновить сделку"""
        return self.call('crm.deal.update', {'id': deal_id, 'fields': fields})

    def crm_contact_add(self, fields):
        """Создать контакт"""
        return self.call('crm.contact.add', {'fields': fields})

    def crm_contact_get(self, contact_id):
        """Получить контакт"""
        return self.call('crm.contact.get', {'id': contact_id})

    def crm_company_add(self, fields):
        """Создать компанию"""
        return self.call('crm.company.add', {'fields': fields})

    def crm_company_get(self, company_id):
        """Получить компанию"""
        return self.call('crm.company.get', {'id': company_id})

    # ========================================
    # ДИСК (disk.*)
    # ========================================

    def disk_folder_get_children(self, folder_id):
        """Получить содержимое папки"""
        return self.call('disk.folder.getchildren', {'id': folder_id})

    def disk_file_get(self, file_id):
        """Получить информацию о файле"""
        return self.call('disk.file.get', {'id': file_id})

    def disk_file_upload_version(self, file_id, file_content, filename):
        """Загрузить новую версию файла"""
        return self.call('disk.file.uploadversion', {
            'id': file_id,
            'fileContent': file_content,
            'filename': filename
        })

    def disk_storage_get_list(self):
        """Получить список доступных хранилищ"""
        return self.call('disk.storage.getlist')
