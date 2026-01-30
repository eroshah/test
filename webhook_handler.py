# webhook_handler.py
from flask import Blueprint, request, jsonify
import json
import time
import re
from config import Config
from database import Database
from bitrix_client import BitrixClient
from openai_client import OpenAIClient
from tools_registry import get_enabled_tools, execute_tool

webhook_bp = Blueprint('webhook', __name__)
db = Database(Config.DATABASE)


def parse_bitrix_form_data(form_data):
    """
    Парсит данные от Bitrix24 из формата data[PARAMS][KEY] в вложенный словарь

    Bitrix отправляет данные в формате:
    event=ONIMBOTMESSAGEADD
    data[PARAMS][DIALOG_ID]=123
    data[PARAMS][MESSAGE]=Hello
    auth[domain]=xxx.bitrix24.ru
    """
    result = {
        'event': form_data.get('event'),
        'data': {'PARAMS': {}},
        'auth': {}
    }

    for key, value in form_data.items():
        # Парсим data[PARAMS][XXX]
        match = re.match(r'data\[PARAMS\]\[(\w+)\]', key)
        if match:
            param_name = match.group(1)
            result['data']['PARAMS'][param_name] = value
            continue

        # Парсим data[USER][XXX]
        match = re.match(r'data\[USER\]\[(\w+)\]', key)
        if match:
            if 'USER' not in result['data']:
                result['data']['USER'] = {}
            param_name = match.group(1)
            result['data']['USER'][param_name] = value
            continue

        # Парсим auth[XXX]
        match = re.match(r'auth\[(\w+)\]', key)
        if match:
            param_name = match.group(1)
            result['auth'][param_name] = value
            continue

    return result


# ТЕСТОВЫЙ ENDPOINT - проверка доступности
@webhook_bp.route('/test', methods=['GET', 'POST'])
def test_webhook():
    print("\n" + "="*60)
    print("[TEST] Webhook is accessible!")
    print(f"[TEST] Method: {request.method}")
    print(f"[TEST] Args: {request.args}")
    print(f"[TEST] Form: {request.form}")
    return jsonify({'status': 'ok', 'message': 'Webhook is working!'})


# Корневой endpoint для /webhook/
@webhook_bp.route('/', methods=['GET', 'POST'])
def webhook_root():
    print("\n" + "="*60)
    print("[WEBHOOK ROOT] Request received!")
    print(f"[WEBHOOK ROOT] Method: {request.method}")
    print(f"[WEBHOOK ROOT] Data: {request.get_data(as_text=True)[:500]}")
    return jsonify({'status': 'ok', 'endpoint': 'webhook_root'})


# Catch-all для любых путей под /webhook/
@webhook_bp.route('/<path:path>', methods=['GET', 'POST'])
def webhook_catchall(path):
    print("\n" + "="*60)
    print(f"[WEBHOOK CATCHALL] Path: {path}")
    print(f"[WEBHOOK CATCHALL] Method: {request.method}")
    print(f"[WEBHOOK CATCHALL] Headers: {dict(request.headers)}")
    print(f"[WEBHOOK CATCHALL] Form: {request.form.to_dict()}")
    print(f"[WEBHOOK CATCHALL] Data: {request.get_data(as_text=True)[:1000]}")

    # Если это /bot, перенаправляем на основной обработчик
    if path == 'bot':
        return bot_webhook()

    return jsonify({'status': 'ok', 'path': path, 'received': True})


@webhook_bp.route('/bot', methods=['GET', 'POST'])
def bot_webhook():
    print("\n" + "="*60)
    print("[WEBHOOK] === INCOMING REQUEST ===")
    print(f"[WEBHOOK] Method: {request.method}")
    print(f"[WEBHOOK] Content-Type: {request.content_type}")
    print(f"[WEBHOOK] Headers: {dict(request.headers)}")
    print(f"[WEBHOOK] Args: {request.args.to_dict()}")

    # Логируем ВСЕ входящие данные для отладки
    form_data = request.form.to_dict()
    print(f"[WEBHOOK] Form data: {form_data}")

    raw_data = request.get_data(as_text=True)
    print(f"[WEBHOOK] Raw data: {raw_data[:2000] if raw_data else 'EMPTY'}")

    try:
        # Парсим данные от Bitrix24
        if form_data:
            event_data = parse_bitrix_form_data(form_data)
        else:
            # Попробуем JSON
            event_data = request.get_json(silent=True) or {}
            if not event_data and raw_data:
                # Попробуем URL-encoded данные
                from urllib.parse import parse_qs
                parsed = parse_qs(raw_data)
                flat_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                event_data = parse_bitrix_form_data(flat_data)

        print(f"[WEBHOOK] Parsed event data: {json.dumps(event_data, indent=2, ensure_ascii=False)[:2000]}")

        event_type = event_data.get('event')
        print(f"[WEBHOOK] Event type: {event_type}")

        # === СОБЫТИЯ ДЛЯ ВНУТРЕННИХ БОТОВ ===
        if event_type == 'ONIMBOTMESSAGEADD':
            return handle_message_add(event_data)

        elif event_type == 'ONIMBOTJOINCHAT':
            print("[WEBHOOK] Bot joined chat")
            return jsonify({'status': 'ok'})

        elif event_type == 'ONIMBOTWELCOMEMESSAGE':
            print("[WEBHOOK] Welcome message request")
            return jsonify({'status': 'ok'})

        # === СОБЫТИЯ ДЛЯ ОТКРЫТЫХ ЛИНИЙ ===
        elif event_type == 'ONIMCONNECTORMESSAGEADD':
            # Сообщение от клиента через коннектор (Telegram, WhatsApp и т.д.)
            print("[WEBHOOK] OpenLine connector message!")
            return handle_openline_message(event_data)

        elif event_type == 'ONIMOPENLINEMESSAGEADD':
            # Сообщение в открытой линии
            print("[WEBHOOK] OpenLine message add!")
            return handle_openline_message(event_data)

        elif event_type == 'ONIMBOTMESSAGEUPDATE':
            print("[WEBHOOK] Bot message update")
            return jsonify({'status': 'ok'})

        elif event_type == 'ONIMBOTMESSAGEDELETE':
            print("[WEBHOOK] Bot message delete")
            return jsonify({'status': 'ok'})

        elif event_type == 'ONIMBOTDELETE':
            print("[WEBHOOK] Bot deleted!")
            return jsonify({'status': 'ok'})

        else:
            print(f"[WEBHOOK] Unknown event type: {event_type}")
            print(f"[WEBHOOK] Full form_data for debugging: {form_data}")
            return jsonify({'status': 'ok', 'event': event_type})

    except Exception as e:
        print(f"[WEBHOOK] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def handle_openline_message(event_data):
    """
    Обработка сообщений из Открытых Линий
    """
    print("\n[OPENLINE] === HANDLING OPENLINE MESSAGE ===")

    try:
        data = event_data.get('data', {})
        params = data.get('PARAMS', {})

        # Для открытых линий структура данных может отличаться
        dialog_id = params.get('DIALOG_ID') or params.get('CHAT_ID')
        message_text = params.get('MESSAGE') or params.get('MESSAGE_TEXT')
        from_user_id = params.get('FROM_USER_ID') or params.get('USER_ID')
        chat_id = params.get('CHAT_ID')
        connector_mid = params.get('CONNECTOR_MID')  # ID сообщения в коннекторе
        line_id = params.get('LINE_ID')  # ID открытой линии

        auth = event_data.get('auth', {})
        domain = auth.get('domain')

        print(f"[OPENLINE] Domain: {domain}")
        print(f"[OPENLINE] Dialog ID: {dialog_id}")
        print(f"[OPENLINE] Chat ID: {chat_id}")
        print(f"[OPENLINE] Line ID: {line_id}")
        print(f"[OPENLINE] From user: {from_user_id}")
        print(f"[OPENLINE] Message: {message_text}")
        print(f"[OPENLINE] All params: {params}")

        if not domain:
            print("[OPENLINE] ERROR: No domain!")
            return jsonify({'status': 'no_domain'})

        if not message_text:
            print("[OPENLINE] ERROR: No message text!")
            return jsonify({'status': 'no_message'})

        # Ищем агента по open_line_id
        agent = None
        if line_id:
            agent = db.get_agent_by_openline(line_id, domain)

        if not agent:
            # Пробуем найти любого активного агента с типом openline
            print(f"[OPENLINE] Agent not found for line_id={line_id}, trying fallback...")
            all_agents = db.get_agents(domain)
            for a in all_agents:
                if a.get('is_active') and a.get('bot_type') == 'openline':
                    print(f"[OPENLINE] Using fallback agent: {a['name']}")
                    agent = a
                    break

        if not agent:
            print(f"[OPENLINE] No agent found!")
            return jsonify({'status': 'agent_not_found'})

        print(f"[OPENLINE] Found agent: {agent['name']} (bot_id={agent['bot_id']})")

        if not agent.get('is_active'):
            print(f"[OPENLINE] Agent is inactive")
            return jsonify({'status': 'agent_inactive'})

        bitrix = BitrixClient(domain, db)
        bot_id = agent['bot_id']

        # Для открытых линий используем chat_id как dialog_id
        target_dialog_id = f"chat{chat_id}" if chat_id and not str(chat_id).startswith('chat') else (dialog_id or chat_id)

        # Показываем индикатор "печатает..."
        try:
            bitrix.bot_typing_start(bot_id, target_dialog_id)
        except Exception as e:
            print(f"[OPENLINE] Typing indicator failed: {e}")

        # Обрабатываем сообщение через OpenAI
        response_text = process_with_openai(agent, message_text, target_dialog_id, bitrix, chat_id)
        print(f"[OPENLINE] Response: {response_text[:200] if response_text else 'EMPTY'}...")

        # Отправляем ответ
        try:
            result = bitrix.bot_send_message(
                bot_id=bot_id,
                dialog_id=target_dialog_id,
                message=response_text
            )
            print(f"[OPENLINE] Response sent! Result: {result}")
        except Exception as e:
            print(f"[OPENLINE] Send failed: {e}")
            import traceback
            traceback.print_exc()

        # Логируем
        db.add_log(agent['id'], 'openline_message', {
            'from_user': from_user_id,
            'message': message_text,
            'response': response_text,
            'dialog_id': target_dialog_id,
            'line_id': line_id
        })

        return jsonify({'status': 'ok'})

    except Exception as e:
        print(f"[OPENLINE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def handle_message_add(event_data):
    print("\n[MESSAGE] === HANDLING MESSAGE ===")

    try:
        # Получаем параметры из распарсенных данных
        data = event_data.get('data', {})
        params = data.get('PARAMS', {})

        dialog_id = params.get('DIALOG_ID')
        message_text = params.get('MESSAGE')
        from_user_id = params.get('FROM_USER_ID')
        to_bot_id = params.get('TO_USER_ID')  # Это ID бота, которому отправлено сообщение
        chat_id = params.get('CHAT_ID')
        message_id = params.get('MESSAGE_ID')

        auth = event_data.get('auth', {})
        domain = auth.get('domain')

        print(f"[MESSAGE] Domain: {domain}")
        print(f"[MESSAGE] Dialog ID: {dialog_id}")
        print(f"[MESSAGE] From user: {from_user_id}")
        print(f"[MESSAGE] To bot (BOT_ID): {to_bot_id}")
        print(f"[MESSAGE] Chat ID: {chat_id}")
        print(f"[MESSAGE] Message: {message_text}")

        if not domain:
            print("[MESSAGE] ERROR: No domain!")
            return jsonify({'status': 'no_domain'})

        if not message_text:
            print("[MESSAGE] ERROR: No message text!")
            return jsonify({'status': 'no_message'})

        # Ищем агента по bot_id
        # ВАЖНО: приводим to_bot_id к int, т.к. в БД хранится как INTEGER
        bot_id_int = None
        if to_bot_id:
            try:
                bot_id_int = int(to_bot_id)
            except (ValueError, TypeError):
                print(f"[MESSAGE] Warning: cannot convert bot_id '{to_bot_id}' to int")

        print(f"[MESSAGE] Looking for agent with bot_id={bot_id_int} in domain={domain}")

        agent = None
        if bot_id_int:
            agent = db.get_agent_by_bot_id(bot_id_int, domain)

        if not agent:
            print(f"[MESSAGE] Agent not found for bot_id={bot_id_int}")
            all_agents = db.get_agents(domain)
            print(f"[MESSAGE] All agents in domain: {[(a['id'], a['bot_id'], a['name']) for a in all_agents]}")

            # Попробуем найти любого активного агента для этого домена
            for a in all_agents:
                if a.get('is_active') and a.get('bot_id'):
                    print(f"[MESSAGE] Using fallback agent: {a['name']} (bot_id={a['bot_id']})")
                    agent = a
                    break

            if not agent:
                return jsonify({'status': 'agent_not_found'})

        print(f"[MESSAGE] Found agent: {agent['name']} (ID={agent['id']}, bot_id={agent['bot_id']})")

        if not agent.get('is_active'):
            print(f"[MESSAGE] Agent is inactive")
            return jsonify({'status': 'agent_inactive'})

        bitrix = BitrixClient(domain, db)
        bot_id_to_use = agent['bot_id']

        # Показываем индикатор "печатает..."
        try:
            bitrix.bot_typing_start(bot_id_to_use, dialog_id)
        except Exception as e:
            print(f"[MESSAGE] Typing indicator failed: {e}")

        # Обрабатываем сообщение через OpenAI
        response_text = process_with_openai(agent, message_text, dialog_id, bitrix, chat_id)
        print(f"[MESSAGE] Response: {response_text[:200] if response_text else 'EMPTY'}...")

        # Отправляем ответ
        try:
            result = bitrix.bot_send_message(
                bot_id=bot_id_to_use,
                dialog_id=dialog_id,
                message=response_text
            )
            print(f"[MESSAGE] Response sent! Result: {result}")
        except Exception as e:
            print(f"[MESSAGE] Send failed: {e}")
            import traceback
            traceback.print_exc()

        # Логируем
        db.add_log(agent['id'], 'message_received', {
            'from_user': from_user_id,
            'message': message_text,
            'response': response_text,
            'dialog_id': dialog_id
        })

        return jsonify({'status': 'ok'})

    except Exception as e:
        print(f"[MESSAGE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def process_with_openai(agent, message_text, dialog_id, bitrix, chat_id=None):
    print("\n[OPENAI] === CALLING OPENAI ===")

    try:
        openai_client = OpenAIClient(agent['openai_api_key'])

        from datetime import datetime
        import pytz
        tz = pytz.timezone(agent.get('timezone', 'UTC'))
        now = datetime.now(tz)

        rag_context = db.get_rag_context(agent['id'], max_length=4000)

        system_prompt = openai_client.build_system_prompt(
            custom_system_prompt=agent.get('system_prompt'),
            agent_description=agent.get('description'),
            current_time_info=now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            rag_context=rag_context
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_text}
        ]

        tools = get_enabled_tools(agent.get('enabled_tools', []))

        response = openai_client.chat_completion(
            messages=messages,
            model=agent.get('openai_model', 'gpt-4o'),
            temperature=agent.get('temperature', 0.7),
            tools=tools if tools else None,
            max_retries=agent.get('max_retries', 3)
        )

        if response.get('tool_calls'):
            tool_results = []
            for tool_call in response['tool_calls']:
                result = execute_tool(
                    tool_call['function'],
                    tool_call['arguments'],
                    bitrix,
                    chat_id=chat_id,
                    agent_timezone=agent.get('timezone', 'UTC')
                )
                tool_results.append(result)

            if response.get('content'):
                return response['content']
            successful = [r.get('message', 'OK') for r in tool_results if r.get('success')]
            return "Done: " + ", ".join(successful) if successful else "Action completed."

        return response.get('content', 'Sorry, I cannot respond.')

    except Exception as e:
        print(f"[OPENAI] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"
