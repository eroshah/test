# app.py
"""
AI Agents Manager для Bitrix24

АРХИТЕКТУРА:
- Bitrix24 боты работают через WEBHOOK (события), а не polling
- При создании агента регистрируется бот с handler_url
- Bitrix отправляет события на /webhook/bot
- Мы обрабатываем и отвечаем через API

Обновлено: 2025
- Добавлен endpoint для получения списка ботов
- Исправлено удаление ботов (отвязка от открытых линий)
- Добавлены поля system_prompt и rag_files
- Обновлены API для работы с RAG
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import time
import os
from config import Config
from database import Database
from translations import get_all_translations
from webhook_handler import webhook_bp



app = Flask(__name__)



@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ''


app.config.from_object(Config)

# Регистрируем blueprint для webhook
app.register_blueprint(webhook_bp, url_prefix='/webhook')

# Инициализация БД
db = Database(Config.DATABASE)

# === LANGUAGE MIDDLEWARE ===


@app.before_request
def set_language():
    """Установить язык из сессии или по умолчанию"""
    if 'lang' not in session:
        session['lang'] = Config.DEFAULT_LANGUAGE


@app.context_processor
def inject_translations():
    """Внедрить переводы в шаблоны"""
    lang = session.get('lang', Config.DEFAULT_LANGUAGE)
    return {
        't': get_all_translations(lang),
        'current_lang': lang,
        'available_langs': Config.LANGUAGES
    }


@app.route('/set-language/<lang>')
def set_language_route(lang):
    """Переключить язык"""
    if lang in Config.LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


# === MAIN ROUTES ===

@app.route('/')
def index():
    """Главная страница - список агентов"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return "Error: DOMAIN parameter required", 400

    # Проверка установки приложения
    app_data = db.get_app(domain)
    if not app_data:
        return render_template('not_installed.html', domain=domain), 400

    # Получить всех агентов
    agents = db.get_agents(domain)

    return render_template('index.html',
                           domain=domain,
                           agents=agents,
                           max_agents=Config.MAX_AGENTS)


@app.route('/agent/create')
def create_agent_page():
    """Страница создания агента"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return "Error: DOMAIN parameter required", 400

    # Проверка лимита
    agents = db.get_agents(domain)
    if len(agents) >= Config.MAX_AGENTS:
        return redirect(url_for('index', DOMAIN=domain))

    return render_template('agent_edit.html',
                           domain=domain,
                           agent=None,
                           models=Config.OPENAI_MODELS,
                           timezones=Config.TIMEZONES)


@app.route('/agent/edit/<int:agent_id>')
def edit_agent_page(agent_id):
    """Страница редактирования агента"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return "Error: DOMAIN parameter required", 400

    agent = db.get_agent(agent_id)

    if not agent or agent['domain'] != domain:
        return "Agent not found", 404

    return render_template('agent_edit.html',
                           domain=domain,
                           agent=agent,
                           models=Config.OPENAI_MODELS,
                           timezones=Config.TIMEZONES)


@app.route('/agent/logs/<int:agent_id>')
def agent_logs_page(agent_id):
    """Страница логов агента"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return "Error: DOMAIN parameter required", 400

    agent = db.get_agent(agent_id)

    if not agent or agent['domain'] != domain:
        return "Agent not found", 404

    logs = db.get_agent_logs(agent_id, limit=100)

    return render_template('agent_logs.html',
                           domain=domain,
                           agent=agent,
                           logs=logs)


# === API ROUTES ===

@app.route('/api/agent/create', methods=['POST'])
def api_create_agent():
    """
    API: Создать агента с ботом для Открытых линий

    Автоматически создаёт бота в Bitrix24 через webhook.
    Бот будет доступен для подключения к любой Открытой линии.
    """
    data = request.json
    domain = Config.BITRIX_DOMAIN  # Берём домен из конфига

    # Проверка лимита
    agents = db.get_agents(domain)
    if len(agents) >= Config.MAX_AGENTS:
        return jsonify({'error': 'Maximum agents reached'}), 400

    try:
        # Создаём агента в БД (пока без bot_id)
        agent_id = db.create_agent(domain, data)

        # Регистрируем бота в Bitrix24 (OAuth или webhook fallback)
        from bitrix_client import BitrixClient
        try:
            bitrix = BitrixClient(domain=domain, db=db)
        except Exception:
            print("[CREATE] OAuth не доступен, используем webhook fallback")
            bitrix = BitrixClient()

        # URL обработчика событий (Cloudflare туннель)
        handler_url = f"{Config.PUBLIC_URL.rstrip('/')}/webhook/bot"

        # Уникальный код бота
        bot_code = f"ai_agent_{agent_id}_{int(time.time())}"

        print(f"[CREATE] Создание бота для Открытых линий")
        print(f"[CREATE] Bot code: {bot_code}")
        print(f"[CREATE] Handler URL: {handler_url}")

        try:
            # Регистрируем бота типа "O" (OpenLine)
            bot_id = bitrix.register_chatbot(
                bot_code=bot_code,
                bot_name=data.get('name', 'AI Assistant'),
                handler_url=handler_url,
                bot_description=data.get('description')
            )

            print(f"[CREATE] Бот создан! BOT_ID={bot_id}")

            # Сохраняем bot_id и все данные
            db.update_agent(agent_id, {
                'bot_id': bot_id,
                'bot_type': 'openline',
                'name': data.get('name'),
                'description': data.get('description'),
                'system_prompt': data.get('system_prompt'),
                'openai_api_key': data.get('openai_api_key'),
                'openai_model': data.get('openai_model', 'gpt-4o'),
                'temperature': data.get('temperature', 0.7),
                'max_retries': data.get('max_retries', 3),
                'timezone': data.get('timezone', 'UTC'),
                'enabled_tools': data.get('enabled_tools', []),
                'is_active': data.get('is_active', 1)
            })

            print(f"[CREATE] Агент создан успешно!")

            return jsonify({
                'success': True,
                'agent_id': agent_id,
                'bot_id': bot_id,
                'message': f'Бот создан! Теперь подключите его к Открытой линии в настройках Bitrix24.'
            })

        except Exception as e:
            print(f"[CREATE] Ошибка создания бота: {e}")
            import traceback
            traceback.print_exc()
            db.delete_agent(agent_id)
            return jsonify({'error': f'Ошибка регистрации бота: {str(e)}'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/update/<int:agent_id>', methods=['POST'])
def api_update_agent(agent_id):
    """API: Обновить агента"""
    data = request.json
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        db.update_agent(agent_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/delete/<int:agent_id>', methods=['POST'])
def api_delete_agent(agent_id):
    """API: Удалить агента и бота в Bitrix24"""
    domain = Config.BITRIX_DOMAIN

    agent = db.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        from bitrix_client import BitrixClient
        try:
            bitrix = BitrixClient(domain=domain, db=db)
        except Exception:
            bitrix = BitrixClient()

        # Удаляем бота из Bitrix24
        if agent.get('bot_id'):
            try:
                bitrix.unregister_chatbot(agent['bot_id'])
                print(f"[DELETE] Бот удалён: BOT_ID={agent['bot_id']}")
            except Exception as e:
                print(f"[DELETE] Не удалось удалить бота: {e}")

        # Удаляем агента из БД
        db.delete_agent(agent_id)
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/toggle/<int:agent_id>', methods=['POST'])
def api_toggle_agent(agent_id):
    """API: Включить/выключить агента"""
    data = request.json
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        new_status = 0 if agent['is_active'] else 1
        db.update_agent(agent_id, {'is_active': new_status})
        return jsonify({'success': True, 'is_active': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === BOTS API ===

@app.route('/api/bots/list', methods=['GET'])
def api_bots_list():
    """API: Получить список всех ботов в Bitrix24"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        bots = bitrix.get_bot_list()
        return jsonify(bots)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bots/sync', methods=['POST'])
def api_bots_sync():
    """API: Синхронизировать ботов с агентами"""
    data = request.json
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Получаем список ботов из Bitrix24
        bots = bitrix.get_bot_list()
        bot_ids = {int(bot.get('ID') or bot.get('id') or 0) for bot in bots}

        # Получаем агентов
        agents = db.get_agents(domain)

        # Проверяем какие агенты имеют несуществующих ботов
        orphaned_agents = []
        for agent in agents:
            if agent.get('bot_id') and agent['bot_id'] not in bot_ids:
                orphaned_agents.append(agent)

        return jsonify({
            'bots': bots,
            'agents': agents,
            'orphaned_agents': orphaned_agents
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === OPENLINES API ===

@app.route('/api/openlines/list', methods=['GET'])
def api_openlines_list():
    """API: Получить список всех открытых линий"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        lines = bitrix.openlines_get_config_list()
        return jsonify(lines)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/openlines/available', methods=['GET'])
def api_available_openlines():
    """API: Получить список доступных (не занятых) открытых линий"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        all_lines = bitrix.openlines_get_config_list()
        used_lines = db.get_used_openlines(domain)

        available = []
        for line in all_lines:
            line_id = str(line.get('ID') or line.get('id', ''))
            if line_id and line_id not in used_lines:
                available.append(line)

        return jsonify(available)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === RAG API ===

@app.route('/api/agent/<int:agent_id>/rag/upload', methods=['POST'])
def api_rag_upload(agent_id):
    """API: Загрузить файл в базу знаний"""
    domain = request.form.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Читаем содержимое файла
        content = file.read().decode('utf-8')
        filename = file.filename

        # Удаляем старые документы с таким именем
        db.delete_rag_documents_by_filename(agent_id, filename)

        # Разбиваем на чанки (простой способ - по 2000 символов)
        chunk_size = 2000
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

        doc_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = db.add_rag_document(
                agent_id=agent_id,
                filename=filename,
                content=chunk,
                content_type='text',
                chunk_index=i
            )
            doc_ids.append(doc_id)

        return jsonify({
            'success': True,
            'filename': filename,
            'chunks': len(chunks),
            'doc_ids': doc_ids
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/<int:agent_id>/rag/list', methods=['GET'])
def api_rag_list(agent_id):
    """API: Получить список файлов базы знаний"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        docs = db.get_rag_documents(agent_id)

        # Группируем по файлам
        files = {}
        for doc in docs:
            filename = doc['filename']
            if filename not in files:
                files[filename] = {
                    'filename': filename,
                    'chunks': 0,
                    'total_length': 0,
                    'created_at': doc['created_at']
                }
            files[filename]['chunks'] += 1
            files[filename]['total_length'] += len(doc['content'])

        return jsonify(list(files.values()))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/<int:agent_id>/rag/delete', methods=['POST'])
def api_rag_delete(agent_id):
    """API: Удалить файл из базы знаний"""
    data = request.json
    domain = data.get('domain')
    filename = data.get('filename')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    if not filename:
        return jsonify({'error': 'Filename required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        db.delete_rag_documents_by_filename(agent_id, filename)
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === INSTALLATION ===

@app.route('/install', methods=['GET', 'POST'])
def install():
    """Установка приложения"""
    print("=== УСТАНОВКА ПРИЛОЖЕНИЯ ===")
    print("Method:", request.method)
    print("Args:", request.args.to_dict())
    print("Form:", request.form.to_dict())

    domain = request.args.get('DOMAIN')
    body_data = request.form.to_dict() or request.get_json(silent=True) or {}

    if not domain:
        return jsonify({'error': 'DOMAIN не передан'}), 400

    auth_id = body_data.get('AUTH_ID')
    refresh_id = body_data.get('REFRESH_ID')
    auth_expires = body_data.get('AUTH_EXPIRES', 3600)
    member_id = body_data.get('member_id')

    # Если нет токенов — показываем страницу с JS SDK который вытянет токены из Bitrix24
    if not auth_id:
        print("[INSTALL] No AUTH_ID, showing JS install page")
        return f'''
        <html>
        <head><script src="//api.bitrix24.com/api/v1/"></script></head>
        <body>
            <script>
                BX24.init(function() {{
                    BX24.installFinish();
                    console.log("installFinish called from init!");
                    window.location.href = '/?DOMAIN={domain}';
                }});
            </script>
            <p>Инициализация приложения...</p>
        </body>
        </html>
        '''

    if auth_id and refresh_id:
        try:
            db.save_app(
                domain,
                auth_id,
                refresh_id,
                int(time.time()) + int(auth_expires),
                member_id
            )
            print("[INSTALL] Токены сохранены")

            # Обновляем handler URL всех ботов (важно при смене Cloudflare tunnel URL)
            if Config.PUBLIC_URL:
                try:
                    from bitrix_client import BitrixClient
                    bitrix = BitrixClient(domain=domain, db=db)
                    handler_url = f"{Config.PUBLIC_URL.rstrip('/')}/webhook/bot"
                    agents = db.get_agents(domain)
                    for agent in agents:
                        if agent.get('bot_id'):
                            try:
                                bitrix.update_bot(agent['bot_id'], handler_url)
                                print(f"[INSTALL] Bot {agent['bot_id']} ({agent['name']}) - URL обновлён")
                            except Exception as e:
                                print(f"[INSTALL] Ошибка обновления бота {agent['bot_id']}: {e}")
                except Exception as e:
                    print(f"[INSTALL] Ошибка обновления ботов: {e}")

            # Завершаем установку и редиректим на главную
            if request.method == 'POST':
                return f'''
                <html>
                <head><script src="//api.bitrix24.com/api/v1/"></script></head>
                <body>
                    <script>
                        BX24.init(function() {{
                            // КРИТИЧЕСКИ ВАЖНО: сообщаем Bitrix24 что установка завершена
                            BX24.installFinish();
                            console.log("installFinish called!");
                            // Переходим на главную
                            setTimeout(function() {{
                                window.location.href = '/?DOMAIN={domain}';
                            }}, 1000);
                        }});
                    </script>
                    <p>Установка приложения...</p>
                </body>
                </html>
                '''

            return jsonify({'success': True, 'message': 'Application installed successfully'})
        except Exception as e:
            print("❌ Ошибка:", str(e))
            return jsonify({'error': str(e)}), 500

    # Fallback
    return redirect(f'/?DOMAIN={domain}')


# === HEALTH CHECK ===

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '3.0',
        'architecture': 'webhook',
        'features': ['system_prompt', 'rag_files', 'bot_list', 'proper_deletion']
    })


# === DEBUG: События ===

@app.route('/api/events/list', methods=['GET'])
def api_events_list():
    """API: Получить список подписок на события"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        events = bitrix.get_event_bindings()

        # Также получим информацию о ботах
        bots = bitrix.get_bot_list()

        return jsonify({
            'events': events,
            'bots': bots,
            'public_url': Config.PUBLIC_URL
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/openline/check/<int:agent_id>', methods=['GET'])
def api_openline_check(agent_id):
    """API: Проверить настройки открытой линии для агента"""
    domain = request.args.get('DOMAIN')

    if not domain:
        return jsonify({'error': 'DOMAIN required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    if not agent.get('open_line_id'):
        return jsonify({'error': 'Agent has no open_line_id'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Получаем настройки открытой линии
        config = bitrix.openlines_get_config(agent['open_line_id'])

        return jsonify({
            'agent': {
                'id': agent['id'],
                'name': agent['name'],
                'bot_id': agent['bot_id'],
                'open_line_id': agent['open_line_id']
            },
            'openline_config': config
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/openline/fix/<int:agent_id>', methods=['POST'])
def api_openline_fix(agent_id):
    """API: Исправить привязку бота к открытой линии"""
    domain = request.json.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    if not agent.get('open_line_id') or not agent.get('bot_id'):
        return jsonify({'error': 'Agent has no open_line_id or bot_id'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Перепривязываем бота с правильными настройками
        result = bitrix.openlines_attach_bot(agent['open_line_id'], agent['bot_id'])

        return jsonify({
            'success': True,
            'result': result,
            'message': f"Бот {agent['bot_id']} привязан к линии {agent['open_line_id']}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/update-url/<int:agent_id>', methods=['POST'])
def api_bot_update_url(agent_id):
    """API: Обновить URL обработчика бота"""
    domain = request.json.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    if not agent.get('bot_id'):
        return jsonify({'error': 'Agent has no bot_id'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Новый URL
        if Config.PUBLIC_URL:
            base_url = Config.PUBLIC_URL.rstrip('/')
        else:
            base_url = request.url_root.rstrip('/')

        handler_url = f"{base_url}/webhook/bot"

        # Обновляем URL бота
        result = bitrix.update_bot(agent['bot_id'], handler_url)

        return jsonify({
            'success': True,
            'result': result,
            'handler_url': handler_url,
            'message': f"URL бота {agent['bot_id']} обновлён на {handler_url}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/agent/<int:agent_id>/chat', methods=['POST'])
def api_agent_chat(agent_id):
    """
    API: Тестовый чат с агентом напрямую (без Bitrix24 webhook)

    Позволяет тестировать агента прямо из интерфейса приложения
    """
    data = request.json
    domain = data.get('domain')
    message = data.get('message', '').strip()

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    if not message:
        return jsonify({'error': 'Message required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    if not agent.get('openai_api_key'):
        return jsonify({'error': 'OpenAI API key not configured'}), 400

    try:
        from openai_client import OpenAIClient
        from datetime import datetime
        import pytz

        openai_client = OpenAIClient(agent['openai_api_key'])

        # Получаем текущее время в часовом поясе агента
        tz = pytz.timezone(agent.get('timezone', 'UTC'))
        now = datetime.now(tz)

        # Получаем RAG контекст
        rag_context = db.get_rag_context(agent_id, max_length=4000)

        # Строим системный промпт
        system_prompt = openai_client.build_system_prompt(
            custom_system_prompt=agent.get('system_prompt'),
            agent_description=agent.get('description'),
            current_time_info=now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            rag_context=rag_context
        )

        # Формируем сообщения
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        # Получаем инструменты (но для тестового чата не выполняем их)
        from tools_registry import get_enabled_tools
        tools = get_enabled_tools(agent.get('enabled_tools', []))

        # Вызываем OpenAI
        response = openai_client.chat_completion(
            messages=messages,
            model=agent.get('openai_model', 'gpt-4o'),
            temperature=agent.get('temperature', 0.7),
            tools=tools if tools else None,
            max_retries=agent.get('max_retries', 3)
        )

        # Получаем ответ
        response_text = response.get('content', '')

        # Если есть tool calls, показываем их
        tool_calls_info = []
        if response.get('tool_calls'):
            for tc in response['tool_calls']:
                tool_calls_info.append({
                    'function': tc['function'],
                    'arguments': tc['arguments']
                })
            if not response_text:
                response_text = f"[Бот хочет выполнить функции: {', '.join([tc['function'] for tc in response['tool_calls']])}]"

        # Логируем тестовое сообщение
        db.add_log(agent_id, 'test_chat', {
            'message': message,
            'response': response_text,
            'tool_calls': tool_calls_info,
            'usage': response.get('usage', {})
        })

        return jsonify({
            'success': True,
            'response': response_text,
            'tool_calls': tool_calls_info,
            'usage': response.get('usage', {})
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-webhook', methods=['POST'])
def api_test_webhook():
    """API: Отправить тестовое сообщение боту для проверки webhook"""
    data = request.json
    domain = data.get('domain')
    agent_id = data.get('agent_id')

    if not domain or not agent_id:
        return jsonify({'error': 'Domain and agent_id required'}), 400

    agent = db.get_agent(agent_id)
    if not agent or agent['domain'] != domain:
        return jsonify({'error': 'Agent not found'}), 404

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Отправляем тестовое сообщение боту от имени текущего пользователя
        # Это должно вызвать событие ONIMBOTMESSAGEADD
        bot_id = agent['bot_id']

        # Получим информацию о текущем пользователе
        user_info = bitrix.call('user.current')
        user_id = user_info.get('ID')

        print(f"[TEST] Отправляем тестовое сообщение боту {bot_id} от пользователя {user_id}")

        # Отправляем сообщение боту через обычный чат
        result = bitrix.call('im.message.add', {
            'DIALOG_ID': bot_id,  # ID бота как получателя
            'MESSAGE': 'Тестовое сообщение для проверки webhook'
        })

        return jsonify({
            'success': True,
            'result': result,
            'message': f'Тестовое сообщение отправлено боту {bot_id}',
            'user_id': user_id
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/bind', methods=['POST'])
def api_events_bind():
    """API: Подписаться на события для бота"""
    data = request.json
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # URL для событий
        if Config.PUBLIC_URL:
            base_url = Config.PUBLIC_URL.rstrip('/')
        else:
            base_url = request.url_root.rstrip('/')

        handler_url = f"{base_url}/webhook/bot"

        # Подписываемся на все нужные события
        events = [
            'ONIMBOTMESSAGEADD',
            'ONIMJOINCHAT',
            'ONIMBOTDELETE',
            'ONIMBOTMESSAGEUPDATE',
        ]

        results = []
        for event in events:
            try:
                bitrix.bind_event(event, handler_url)
                results.append({'event': event, 'status': 'ok'})
            except Exception as e:
                results.append({'event': event, 'status': 'error', 'error': str(e)})

        return jsonify({'results': results, 'handler_url': handler_url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Логирование ВСЕХ запросов для отладки
@app.before_request
def log_request():
    # Пропускаем статику и частые запросы
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return

    print(f"\n{'='*50}")
    print(f"[REQUEST] {request.method} {request.path}")
    print(f"[REQUEST] From: {request.remote_addr}")

    if request.path.startswith('/webhook'):
        print(f"[REQUEST] Headers: {dict(request.headers)}")
        print(f"[REQUEST] Form: {request.form.to_dict()}")
        print(f"[REQUEST] Data: {request.get_data(as_text=True)[:500]}")


@app.route('/api/bots/update-all-urls', methods=['POST'])
def api_update_all_bot_urls():
    """
    API: Обновить URL обработчика для ВСЕХ ботов домена

    Используйте этот endpoint после смены URL Cloudflare туннеля!
    """
    data = request.json
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain required'}), 400

    try:
        from bitrix_client import BitrixClient
        bitrix = BitrixClient(domain, db)

        # Новый URL
        if Config.PUBLIC_URL:
            base_url = Config.PUBLIC_URL.rstrip('/')
        else:
            base_url = request.url_root.rstrip('/')

        handler_url = f"{base_url}/webhook/bot"

        # Получаем всех агентов домена
        agents = db.get_agents(domain)
        results = []

        for agent in agents:
            if agent.get('bot_id'):
                try:
                    bitrix.update_bot(agent['bot_id'], handler_url)
                    results.append({
                        'agent_id': agent['id'],
                        'bot_id': agent['bot_id'],
                        'status': 'updated',
                        'handler_url': handler_url
                    })
                    print(f"✅ Бот {agent['bot_id']} ({agent['name']}) - URL обновлён на {handler_url}")
                except Exception as e:
                    results.append({
                        'agent_id': agent['id'],
                        'bot_id': agent['bot_id'],
                        'status': 'error',
                        'error': str(e)
                    })
                    print(f"❌ Бот {agent['bot_id']} - ошибка: {e}")

        return jsonify({
            'success': True,
            'handler_url': handler_url,
            'results': results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def update_all_bots_on_startup():
    """Обновить URL всех ботов при запуске приложения"""
    print("\n" + "="*60)
    print("🔄 Проверка и обновление URL всех ботов...")
    print(f"📌 PUBLIC_URL: {Config.PUBLIC_URL}")

    if not Config.PUBLIC_URL:
        print("⚠️ PUBLIC_URL не указан! Боты не будут обновлены.")
        return

    handler_url = f"{Config.PUBLIC_URL.rstrip('/')}/webhook/bot"
    print(f"📌 Handler URL: {handler_url}")

    # Получаем все приложения (домены)
    try:
        import sqlite3
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT domain FROM apps')
        domains = [row['domain'] for row in cursor.fetchall()]
        conn.close()

        for domain in domains:
            print(f"\n📍 Домен: {domain}")
            try:
                from bitrix_client import BitrixClient
                bitrix = BitrixClient(domain, db)

                agents = db.get_agents(domain)
                for agent in agents:
                    if agent.get('bot_id'):
                        try:
                            bitrix.update_bot(agent['bot_id'], handler_url)
                            print(f"  ✅ Бот {agent['bot_id']} ({agent['name']}) - URL обновлён")
                        except Exception as e:
                            print(f"  ⚠️ Бот {agent['bot_id']} - ошибка: {e}")
            except Exception as e:
                print(f"  ❌ Ошибка домена {domain}: {e}")

        print("\n" + "="*60)
        print("✅ Проверка ботов завершена!")

    except Exception as e:
        print(f"❌ Ошибка при обновлении ботов: {e}")


if __name__ == '__main__':
    print("🚀 Запуск Flask приложения...")
    print("📌 Убедитесь, что Cloudflare tunnel запущен отдельно!")
    print(f"📌 PUBLIC_URL: {Config.PUBLIC_URL}")
    print("📌 Приложение доступно на http://localhost:5000")

    # Обновляем URL ботов при запуске
    update_all_bots_on_startup()

    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
