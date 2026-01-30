# database.py
"""
База данных для AI Agents Manager

Обновлено: 2025
- Добавлено поле system_prompt для системного промпта
- Добавлено поле rag_files для хранения файлов базы знаний
- Добавлена таблица для хранения RAG документов
"""
import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Проверяем существование столбцов
        cursor.execute("PRAGMA table_info(agents)")
        columns = [column[1] for column in cursor.fetchall()]

        # Если таблица существует но нет новых полей - добавляем их
        needs_migration = False
        if columns:
            if 'bot_id' not in columns or 'system_prompt' not in columns or 'rag_files' not in columns:
                needs_migration = True

        if needs_migration:
            print("⚠️ Обновление структуры БД - миграция...")
            # Добавляем новые столбцы если их нет
            try:
                if 'system_prompt' not in columns:
                    cursor.execute('ALTER TABLE agents ADD COLUMN system_prompt TEXT')
                    print("  + Добавлен столбец system_prompt")
            except:
                pass
            try:
                if 'rag_files' not in columns:
                    cursor.execute('ALTER TABLE agents ADD COLUMN rag_files TEXT')
                    print("  + Добавлен столбец rag_files")
            except:
                pass
            try:
                if 'bot_id' not in columns:
                    cursor.execute('ALTER TABLE agents ADD COLUMN bot_id INTEGER')
                    print("  + Добавлен столбец bot_id")
            except:
                pass

        # Таблица установок приложения (Bitrix24 токены)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                expires_at INTEGER,
                member_id TEXT,
                created_at INTEGER
            )
        ''')

        # Таблица AI агентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                system_prompt TEXT,
                rag_files TEXT,
                openai_api_key TEXT NOT NULL,
                openai_model TEXT DEFAULT 'gpt-4o',
                temperature REAL DEFAULT 0.7,
                audio_transcription INTEGER DEFAULT 1,
                max_retries INTEGER DEFAULT 3,
                inbound_only INTEGER DEFAULT 0,
                message_buffer_time INTEGER DEFAULT 10,
                timezone TEXT DEFAULT 'UTC',
                working_hours_enabled INTEGER DEFAULT 0,
                working_hours_schedule TEXT,
                enabled_tools TEXT,
                is_active INTEGER DEFAULT 1,
                open_line_id TEXT,
                bot_id INTEGER,
                bot_type TEXT DEFAULT 'openline',
                created_at INTEGER,
                updated_at INTEGER
            )
        ''')

        # Миграция: добавляем bot_type если его нет
        try:
            cursor.execute("ALTER TABLE agents ADD COLUMN bot_type TEXT DEFAULT 'openline'")
            conn.commit()
            print("[DB] Миграция: добавлено поле bot_type")
        except:
            pass  # Поле уже существует

        # Таблица RAG документов (база знаний)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                chunk_index INTEGER DEFAULT 0,
                embedding TEXT,
                created_at INTEGER,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
        ''')

        # Таблица чатов (активные диалоги)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                chat_id TEXT NOT NULL,
                user_id TEXT,
                user_name TEXT,
                status TEXT DEFAULT 'active',
                last_message_time INTEGER,
                created_lead_id INTEGER,
                created_deal_id INTEGER,
                created_at INTEGER,
                FOREIGN KEY(agent_id) REFERENCES agents(id),
                UNIQUE(agent_id, chat_id)
            )
        ''')

        # Таблица сообщений (история + буфер)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_table_id INTEGER NOT NULL,
                message_id TEXT,
                author_type TEXT,
                author_id TEXT,
                content TEXT,
                is_audio INTEGER DEFAULT 0,
                audio_transcription TEXT,
                processed INTEGER DEFAULT 0,
                timestamp INTEGER,
                FOREIGN KEY(chat_table_id) REFERENCES chats(id)
            )
        ''')

        # Таблица логов (действия агента)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                chat_table_id INTEGER,
                action_type TEXT,
                action_data TEXT,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                created_at INTEGER,
                FOREIGN KEY(agent_id) REFERENCES agents(id),
                FOREIGN KEY(chat_table_id) REFERENCES chats(id)
            )
        ''')

        conn.commit()
        conn.close()

    # === APPS (Bitrix24 токены) ===

    def save_app(self, domain, access_token, refresh_token, expires_at, member_id=None):
        """Сохранить токены приложения"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO apps
            (domain, access_token, refresh_token, expires_at, member_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (domain, access_token, refresh_token, expires_at, member_id, int(datetime.now().timestamp())))

        conn.commit()
        conn.close()

    def get_app(self, domain):
        """Получить токены приложения"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM apps WHERE domain = ?', (domain,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    # === AGENTS ===

    def create_agent(self, domain, agent_data):
        """Создать AI агента"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = int(datetime.now().timestamp())

        cursor.execute('''
            INSERT INTO agents
            (domain, name, description, system_prompt, rag_files, openai_api_key, openai_model, temperature,
             audio_transcription, max_retries, inbound_only, message_buffer_time,
             timezone, working_hours_enabled, working_hours_schedule, enabled_tools,
             is_active, open_line_id, bot_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            domain,
            agent_data.get('name'),
            agent_data.get('description'),
            agent_data.get('system_prompt'),
            json.dumps(agent_data.get('rag_files', [])),
            agent_data.get('openai_api_key'),
            agent_data.get('openai_model', 'gpt-4o'),
            agent_data.get('temperature', 0.7),
            agent_data.get('audio_transcription', 1),
            agent_data.get('max_retries', 3),
            agent_data.get('inbound_only', 0),
            agent_data.get('message_buffer_time', 10),
            agent_data.get('timezone', 'UTC'),
            agent_data.get('working_hours_enabled', 0),
            json.dumps(agent_data.get('working_hours_schedule', {})),
            json.dumps(agent_data.get('enabled_tools', [])),
            agent_data.get('is_active', 1),
            agent_data.get('open_line_id'),
            agent_data.get('bot_id'),
            now, now
        ))

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return agent_id

    def get_agents(self, domain):
        """Получить всех агентов"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM agents WHERE domain = ? ORDER BY created_at DESC', (domain,))
        rows = cursor.fetchall()
        conn.close()

        agents = []
        for row in rows:
            agent = dict(row)
            agent['working_hours_schedule'] = json.loads(agent['working_hours_schedule']) if agent['working_hours_schedule'] else {}
            agent['enabled_tools'] = json.loads(agent['enabled_tools']) if agent['enabled_tools'] else []
            agent['rag_files'] = json.loads(agent['rag_files']) if agent.get('rag_files') else []
            agents.append(agent)

        return agents

    def get_agent(self, agent_id):
        """Получить агента по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            agent = dict(row)
            agent['working_hours_schedule'] = json.loads(agent['working_hours_schedule']) if agent['working_hours_schedule'] else {}
            agent['enabled_tools'] = json.loads(agent['enabled_tools']) if agent['enabled_tools'] else []
            agent['rag_files'] = json.loads(agent['rag_files']) if agent.get('rag_files') else []
            return agent

        return None

    def get_agent_by_bot_id(self, bot_id, domain):
        """
        Получить агента по BOT_ID

        Args:
            bot_id: ID бота (может быть int или str)
            domain: домен Битрикс24

        Returns:
            dict или None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Приводим bot_id к int для корректного сравнения
        try:
            bot_id_int = int(bot_id) if bot_id else None
        except (ValueError, TypeError):
            print(f"[DB] Warning: cannot convert bot_id '{bot_id}' to int")
            bot_id_int = None

        if bot_id_int is None:
            conn.close()
            return None

        print(f"[DB] Looking for agent: bot_id={bot_id_int}, domain={domain}")

        cursor.execute('SELECT * FROM agents WHERE bot_id = ? AND domain = ?', (bot_id_int, domain))
        row = cursor.fetchone()
        conn.close()

        if row:
            agent = dict(row)
            agent['working_hours_schedule'] = json.loads(agent['working_hours_schedule']) if agent['working_hours_schedule'] else {}
            agent['enabled_tools'] = json.loads(agent['enabled_tools']) if agent['enabled_tools'] else []
            agent['rag_files'] = json.loads(agent['rag_files']) if agent.get('rag_files') else []
            print(f"[DB] Found agent: {agent['name']} (id={agent['id']})")
            return agent

        print(f"[DB] Agent not found for bot_id={bot_id_int}")
        return None

    def get_agent_by_openline(self, open_line_id, domain):
        """
        Получить агента по ID Открытой Линии

        Args:
            open_line_id: ID открытой линии
            domain: домен Битрикс24

        Returns:
            dict или None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        print(f"[DB] Looking for agent by openline: open_line_id={open_line_id}, domain={domain}")

        cursor.execute('SELECT * FROM agents WHERE open_line_id = ? AND domain = ?', (str(open_line_id), domain))
        row = cursor.fetchone()
        conn.close()

        if row:
            agent = dict(row)
            agent['working_hours_schedule'] = json.loads(agent['working_hours_schedule']) if agent['working_hours_schedule'] else {}
            agent['enabled_tools'] = json.loads(agent['enabled_tools']) if agent['enabled_tools'] else []
            agent['rag_files'] = json.loads(agent['rag_files']) if agent.get('rag_files') else []
            print(f"[DB] Found agent by openline: {agent['name']} (id={agent['id']})")
            return agent

        print(f"[DB] Agent not found for open_line_id={open_line_id}")
        return None

    def update_agent(self, agent_id, agent_data):
        """Обновить агента"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Получаем текущие данные агента для сохранения неизменённых полей
        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        current = cursor.fetchone()

        if not current:
            conn.close()
            return False

        current = dict(current)

        cursor.execute('''
            UPDATE agents SET
                name = ?, description = ?, system_prompt = ?, rag_files = ?,
                openai_api_key = ?, openai_model = ?,
                temperature = ?, audio_transcription = ?, max_retries = ?,
                inbound_only = ?, message_buffer_time = ?, timezone = ?,
                working_hours_enabled = ?, working_hours_schedule = ?,
                enabled_tools = ?, is_active = ?, open_line_id = ?, bot_id = ?,
                bot_type = ?, updated_at = ?
            WHERE id = ?
        ''', (
            agent_data.get('name', current['name']),
            agent_data.get('description', current['description']),
            agent_data.get('system_prompt', current.get('system_prompt')),
            json.dumps(agent_data.get('rag_files', [])) if 'rag_files' in agent_data else current.get('rag_files'),
            agent_data.get('openai_api_key', current['openai_api_key']),
            agent_data.get('openai_model', current['openai_model']),
            agent_data.get('temperature', current['temperature']),
            agent_data.get('audio_transcription', current['audio_transcription']),
            agent_data.get('max_retries', current['max_retries']),
            agent_data.get('inbound_only', current['inbound_only']),
            agent_data.get('message_buffer_time', current['message_buffer_time']),
            agent_data.get('timezone', current['timezone']),
            agent_data.get('working_hours_enabled', current['working_hours_enabled']),
            json.dumps(agent_data.get('working_hours_schedule', {})) if 'working_hours_schedule' in agent_data else current['working_hours_schedule'],
            json.dumps(agent_data.get('enabled_tools', [])) if 'enabled_tools' in agent_data else current['enabled_tools'],
            agent_data.get('is_active', current['is_active']),
            agent_data.get('open_line_id', current['open_line_id']),
            agent_data.get('bot_id', current['bot_id']),
            agent_data.get('bot_type', current.get('bot_type', 'openline')),
            int(datetime.now().timestamp()),
            agent_id
        ))

        conn.commit()
        conn.close()
        return True

    def delete_agent(self, agent_id):
        """Удалить агента и все связанные данные"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Удаляем RAG документы
        cursor.execute('DELETE FROM rag_documents WHERE agent_id = ?', (agent_id,))

        # Удаляем логи
        cursor.execute('DELETE FROM logs WHERE agent_id = ?', (agent_id,))

        # Получаем все чаты агента
        cursor.execute('SELECT id FROM chats WHERE agent_id = ?', (agent_id,))
        chat_ids = [row['id'] for row in cursor.fetchall()]

        # Удаляем сообщения чатов
        if chat_ids:
            placeholders = ','.join('?' * len(chat_ids))
            cursor.execute(f'DELETE FROM messages WHERE chat_table_id IN ({placeholders})', chat_ids)

        # Удаляем чаты
        cursor.execute('DELETE FROM chats WHERE agent_id = ?', (agent_id,))

        # Удаляем агента
        cursor.execute('DELETE FROM agents WHERE id = ?', (agent_id,))

        conn.commit()
        conn.close()

    # === RAG DOCUMENTS ===

    def add_rag_document(self, agent_id, filename, content, content_type='text', chunk_index=0, embedding=None):
        """Добавить RAG документ"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO rag_documents
            (agent_id, filename, content, content_type, chunk_index, embedding, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            filename,
            content,
            content_type,
            chunk_index,
            json.dumps(embedding) if embedding else None,
            int(datetime.now().timestamp())
        ))

        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return doc_id

    def get_rag_documents(self, agent_id):
        """Получить все RAG документы агента"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM rag_documents
            WHERE agent_id = ?
            ORDER BY filename, chunk_index
        ''', (agent_id,))

        rows = cursor.fetchall()
        conn.close()

        docs = []
        for row in rows:
            doc = dict(row)
            doc['embedding'] = json.loads(doc['embedding']) if doc['embedding'] else None
            docs.append(doc)

        return docs

    def get_rag_context(self, agent_id, max_length=4000):
        """
        Получить контекст из базы знаний для агента

        Args:
            agent_id: ID агента
            max_length: максимальная длина контекста

        Returns:
            str: объединённый контекст из документов
        """
        docs = self.get_rag_documents(agent_id)

        if not docs:
            return None

        context_parts = []
        current_length = 0

        for doc in docs:
            doc_text = f"[{doc['filename']}]\n{doc['content']}\n"

            if current_length + len(doc_text) > max_length:
                # Обрезаем если превышает лимит
                remaining = max_length - current_length
                if remaining > 100:
                    context_parts.append(doc_text[:remaining] + "...")
                break

            context_parts.append(doc_text)
            current_length += len(doc_text)

        return "\n".join(context_parts) if context_parts else None

    def delete_rag_document(self, doc_id):
        """Удалить RAG документ"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM rag_documents WHERE id = ?', (doc_id,))

        conn.commit()
        conn.close()

    def delete_rag_documents_by_filename(self, agent_id, filename):
        """Удалить все RAG документы с определённым именем файла"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM rag_documents WHERE agent_id = ? AND filename = ?', (agent_id, filename))

        conn.commit()
        conn.close()

    # === CHATS ===

    def get_or_create_chat(self, agent_id, chat_id, user_id=None, user_name=None):
        """Получить или создать чат"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM chats WHERE agent_id = ? AND chat_id = ?
        ''', (agent_id, chat_id))

        row = cursor.fetchone()

        if row:
            chat_table_id = row['id']
        else:
            cursor.execute('''
                INSERT INTO chats (agent_id, chat_id, user_id, user_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (agent_id, chat_id, user_id, user_name, int(datetime.now().timestamp())))

            chat_table_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return chat_table_id

    def update_chat_status(self, chat_table_id, status, lead_id=None, deal_id=None):
        """Обновить статус чата"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = ['status = ?']
        params = [status]

        if lead_id:
            updates.append('created_lead_id = ?')
            params.append(lead_id)

        if deal_id:
            updates.append('created_deal_id = ?')
            params.append(deal_id)

        params.append(chat_table_id)

        cursor.execute(f'''
            UPDATE chats SET {', '.join(updates)}
            WHERE id = ?
        ''', params)

        conn.commit()
        conn.close()

    # === MESSAGES ===

    def add_message(self, chat_table_id, message_data):
        """Добавить сообщение"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO messages
            (chat_table_id, message_id, author_type, author_id, content,
             is_audio, audio_transcription, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chat_table_id,
            message_data.get('message_id'),
            message_data.get('author_type'),
            message_data.get('author_id'),
            message_data.get('content'),
            message_data.get('is_audio', 0),
            message_data.get('audio_transcription'),
            int(datetime.now().timestamp())
        ))

        conn.commit()
        conn.close()

    def get_unprocessed_messages(self, chat_table_id):
        """Получить необработанные сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM messages
            WHERE chat_table_id = ? AND processed = 0
            ORDER BY timestamp ASC
        ''', (chat_table_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_chat_history(self, chat_table_id, limit=50):
        """Получить историю сообщений чата"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM messages
            WHERE chat_table_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (chat_table_id, limit))

        rows = cursor.fetchall()
        conn.close()

        # Возвращаем в хронологическом порядке
        return [dict(row) for row in reversed(rows)]

    def mark_messages_processed(self, message_ids):
        """Отметить сообщения как обработанные"""
        if not message_ids:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(message_ids))
        cursor.execute(f'''
            UPDATE messages SET processed = 1
            WHERE id IN ({placeholders})
        ''', message_ids)

        conn.commit()
        conn.close()

    # === LOGS ===

    def add_log(self, agent_id, action_type, action_data=None, chat_table_id=None, success=True, error_message=None):
        """Добавить лог"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO logs
            (agent_id, chat_table_id, action_type, action_data, success, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            chat_table_id,
            action_type,
            json.dumps(action_data, ensure_ascii=False) if action_data else None,
            1 if success else 0,
            error_message,
            int(datetime.now().timestamp())
        ))

        conn.commit()
        conn.close()

    def get_agent_logs(self, agent_id, limit=100):
        """Получить логи агента"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM logs
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (agent_id, limit))

        rows = cursor.fetchall()
        conn.close()

        logs = []
        for row in rows:
            log = dict(row)
            log['action_data'] = json.loads(log['action_data']) if log['action_data'] else None
            logs.append(log)

        return logs

    def get_used_openlines(self, domain):
        """Получить список используемых открытых линий"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT open_line_id
            FROM agents
            WHERE domain = ?
            AND open_line_id IS NOT NULL
            AND is_active = 1
        ''', (domain,))

        rows = cursor.fetchall()
        conn.close()

        return {row['open_line_id'] for row in rows}
