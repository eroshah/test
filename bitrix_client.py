# bitrix_client.py
"""
Клиент для работы с Bitrix24 REST API

Поддерживает 3 режима работы:
1. OAuth (основной) — через access_token из БД, с автообновлением
2. Event token — через access_token из входящего события Bitrix24
3. Webhook (fallback) — через входящий вебхук URL

Обновлено: 2025
- Dual-mode: OAuth + Webhook
- Автообновление токенов
- Сохранение токенов из событий
"""
import time
import requests
from config import Config


class BitrixClient:
    def __init__(self, domain=None, db=None, access_token=None):
        """
        Инициализация клиента Bitrix24 API.

        Режимы:
          BitrixClient(domain='...', db=db)              — OAuth из БД
          BitrixClient(domain='...', access_token='xxx')  — токен из события
          BitrixClient()                                   — webhook fallback
        """
        self.domain = domain or Config.BITRIX_DOMAIN
        self.db = db
        self._access_token = access_token
        self.webhook_url = Config.BITRIX_WEBHOOK_URL.rstrip('/') if Config.BITRIX_WEBHOOK_URL else None

        # Определяем режим работы
        if access_token:
            self.mode = 'event_token'
        elif domain and db:
            self.mode = 'oauth'
        elif self.webhook_url:
            self.mode = 'webhook'
        else:
            raise Exception("BitrixClient: нужен (domain+db), access_token, или BITRIX_WEBHOOK_URL")

        print(f"[Bitrix API] Mode: {self.mode}, Domain: {self.domain}")

    def _get_access_token(self):
        """Получить валидный access_token, обновив при необходимости"""
        if self._access_token:
            return self._access_token

        if self.mode == 'oauth' and self.db:
            app = self.db.get_app(self.domain)
            if not app:
                raise Exception(f"Приложение не установлено для домена: {self.domain}")

            # Проверяем срок действия (обновляем за 60 сек до истечения)
            if app.get('expires_at') and int(time.time()) >= int(app['expires_at']) - 60:
                print(f"[Bitrix API] Токен истёк, обновляем...")
                return self._refresh_token(app['refresh_token'])

            return app['access_token']

        raise Exception("Нет доступного access_token")

    def _refresh_token(self, refresh_token):
        """Обновить OAuth access_token через client credentials"""
        print(f"[Bitrix API] Обновление токена для {self.domain}")

        response = requests.post("https://oauth.bitrix.info/oauth/token/", data={
            'grant_type': 'refresh_token',
            'client_id': Config.CLIENT_ID,
            'client_secret': Config.CLIENT_SECRET,
            'refresh_token': refresh_token
        })

        if response.status_code == 200:
            data = response.json()
            new_access_token = data['access_token']

            if self.db:
                self.db.save_app(
                    self.domain,
                    new_access_token,
                    data['refresh_token'],
                    int(time.time()) + int(data.get('expires_in', 3600)),
                    data.get('member_id')
                )
                print(f"[Bitrix API] Токен обновлён и сохранён")

            return new_access_token
        else:
            raise Exception(f"Ошибка обновления токена: {response.status_code} - {response.text}")

    def save_event_tokens(self, auth_data):
        """
        Сохранить токены из входящего события Bitrix24.

        Bitrix24 отправляет auth[access_token], auth[refresh_token] и т.д.
        с каждым событием. Сохраняем для дальнейшего использования.
        """
        if not self.db or not auth_data:
            return

        domain = auth_data.get('domain', self.domain)
        access_token = auth_data.get('access_token')
        refresh_token = auth_data.get('refresh_token')
        expires_in = int(auth_data.get('expires_in', 3600))
        member_id = auth_data.get('member_id')

        if access_token and refresh_token:
            self.db.save_app(
                domain,
                access_token,
                refresh_token,
                int(time.time()) + expires_in,
                member_id
            )
            print(f"[Bitrix API] Токены из события сохранены для {domain}")

    def call(self, method, params=None):
        """Вызов метода Bitrix24 REST API"""
        if params is None:
            params = {}

        if self.mode == 'webhook':
            url = f"{self.webhook_url}/{method}"
        else:
            # OAuth или event_token режим
            access_token = self._get_access_token()
            url = f"https://{self.domain}/rest/{method}"
            params['auth'] = access_token

        print(f"[Bitrix API] Вызов: {method} (mode={self.mode})")

        response = requests.post(url, json=params)

        print(f"[Bitrix API] HTTP статус: {response.status_code}")
        print(f"[Bitrix API] Ответ: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()

            if 'result' in data:
                return data['result']
            elif 'error' in data:
                error_code = data['error']
                error_desc = data.get('error_description', '')

                # Если токен невалиден — пробуем обновить и повторить
                if error_code in ('expired_token', 'invalid_token', 'INVALID_TOKEN') and self.mode == 'oauth' and self.db:
                    print(f"[Bitrix API] Токен невалиден, пробуем обновить...")
                    app = self.db.get_app(self.domain)
                    if app and app.get('refresh_token'):
                        self._access_token = self._refresh_token(app['refresh_token'])
                        # Повторяем запрос с новым токеном
                        params['auth'] = self._access_token
                        retry_response = requests.post(url, json=params)
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            if 'result' in retry_data:
                                return retry_data['result']
                            elif 'error' in retry_data:
                                raise Exception(f"Bitrix API Error (после обновления токена): {retry_data['error']} - {retry_data.get('error_description', '')}")
                        else:
                            raise Exception(f"HTTP Error (после обновления токена): {retry_response.status_code}")

                raise Exception(f"Bitrix API Error: {error_code} - {error_desc}")
            else:
                return data
        else:
            raise Exception(f"HTTP Error: {response.status_code} - {response.text}")

    # ========================================
    # ЧАТБОТ (imbot.*)
    # ========================================

    def register_chatbot(self, bot_code, bot_name, handler_url, bot_description=None):
        """
        Зарегистрировать чат-бота для Открытых линий в Bitrix24

        Создаёт бота типа "O" (OpenLine) - для работы с виджетами, Telegram, WhatsApp и т.д.
        """
        params = {
            'CODE': bot_code,
            'TYPE': 'O',
            'OPENLINE': 'Y',
            'EVENT_MESSAGE_ADD': handler_url,
            'EVENT_WELCOME_MESSAGE': handler_url,
            'EVENT_BOT_DELETE': handler_url,
            'PROPERTIES': {
                'NAME': bot_name,
                'WORK_POSITION': bot_description or 'AI Assistant',
                'COLOR': 'GREEN'
            }
        }

        print(f"[Bitrix] Регистрация бота для Открытых линий")
        print(f"[Bitrix] CODE={bot_code}, NAME={bot_name}")
        print(f"[Bitrix] Handler URL: {handler_url}")

        result = self.call('imbot.register', params)
        print(f"[Bitrix] Бот зарегистрирован! BOT_ID={result}")

        return result

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
        """Получить список всех зарегистрированных ботов"""
        try:
            result = self.call('imbot.bot.list')
            return result if isinstance(result, list) else result if isinstance(result, dict) else []
        except Exception as e:
            print(f"Ошибка получения списка ботов: {e}")
            return []

    def get_bot_info(self, bot_id):
        """Получить информацию о боте"""
        try:
            result = self.call('imbot.bot.list', {'BOT_ID': bot_id})
            return result
        except Exception as e:
            print(f"Ошибка получения информации о боте: {e}")
            return None

    def update_bot(self, bot_id, handler_url):
        """Обновить обработчик событий бота"""
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
        """Отправить сообщение от имени бота"""
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
        """Показать индикатор 'печатает...'"""
        return self.call('imbot.chat.sendTyping', {
            'BOT_ID': bot_id,
            'DIALOG_ID': dialog_id
        })

    # ========================================
    # ОТКРЫТЫЕ ЛИНИИ (imopenlines.*)
    # ========================================

    def openlines_get_config_list(self):
        """Получить список всех открытых линий"""
        try:
            result = self.call('imopenlines.config.list.get')
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return list(result.values()) if result else []
            return []
        except Exception as e:
            print(f"Ошибка получения списка открытых линий: {e}")
            return []

    def openlines_get_config(self, config_id):
        """Получить информацию о конкретной открытой линии"""
        try:
            result = self.call('imopenlines.config.get', {
                'CONFIG_ID': config_id
            })
            return result
        except Exception as e:
            print(f"Ошибка получения открытой линии {config_id}: {e}")
            return None

    def openlines_attach_bot(self, openline_id, bot_id):
        """Привязать бота к открытой линии"""
        result = self.call('imopenlines.config.update', {
            'CONFIG_ID': openline_id,
            'FIELDS': {
                'WELCOME_BOT_ENABLE': 'Y',
                'WELCOME_BOT_ID': bot_id,
                'WELCOME_BOT_JOIN': 'first',
                'WELCOME_BOT_LEFT': 'queue',
                'BOT_ID': bot_id
            }
        })
        print(f"[Bitrix] Бот {bot_id} привязан к линии {openline_id} как приветственный бот")
        return result

    def openlines_detach_bot(self, openline_id):
        """Отвязать бота от открытой линии"""
        return self.call('imopenlines.config.update', {
            'CONFIG_ID': openline_id,
            'FIELDS': {
                'BOT_ID': 0
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
        """Передать диалог другому оператору"""
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
        """Отправить сообщение (от имени текущего пользователя, НЕ бота)"""
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
