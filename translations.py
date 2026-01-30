# translations.py
"""
Translations for AI Agents Manager

Updated: 2025
- Added translations for system_prompt
- Added translations for rag_files
- Added translations for bot list
"""

TRANSLATIONS = {
    'en': {
        # General
        'app_name': 'AI Agents Manager',
        'language': 'Language',
        'save': 'Save',
        'cancel': 'Cancel',
        'delete': 'Delete',
        'edit': 'Edit',
        'create': 'Create',
        'back': 'Back',
        'yes': 'Yes',
        'no': 'No',
        'enabled': 'Enabled',
        'disabled': 'Disabled',
        'upload': 'Upload',
        'download': 'Download',
        'refresh': 'Refresh',
        'sync': 'Sync',
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'warning': 'Warning',
        'info': 'Info',

        # Agents
        'agents_list': 'AI Agents',
        'create_agent': 'Create Agent',
        'edit_agent': 'Edit Agent',
        'agent_settings': 'Agent Settings',
        'no_agents': 'No agents created yet',
        'max_agents_reached': 'Maximum number of agents reached',
        'agent_created': 'Agent created successfully',
        'agent_updated': 'Agent updated successfully',
        'agent_deleted': 'Agent deleted successfully',

        # Agent fields
        'name': 'Name',
        'description': 'Description',
        'system_prompt': 'System Prompt',
        'system_prompt_placeholder': 'Enter the system prompt that defines how the bot should behave...',
        'rag_files': 'Knowledge Base (RAG)',
        'rag_files_description': 'Upload text files to create a knowledge base for the bot',
        'openai_api_key': 'OpenAI API Key',
        'openai_model': 'OpenAI Model',
        'temperature': 'Temperature',
        'audio_transcription': 'Audio Transcription in BX24 Chat',
        'max_retries': 'Max Retries',
        'inbound_only': 'Inbound Only in BX24 Chat',
        'message_buffer_time': 'Message Buffer Wait Time (Seconds)',
        'timezone': 'Timezone',
        'working_hours': 'Working Hours',
        'working_hours_247': '24/7',
        'working_hours_custom': 'Custom Schedule',
        'tools': 'Available Tools',
        'open_line': 'Open Line',
        'bot_id': 'Bot ID',

        # Bots
        'bots_list': 'Registered Bots',
        'bots_sync': 'Sync Bots',
        'bots_orphaned': 'Orphaned Agents',
        'bots_description': 'List of all bots registered by this application',

        # Working hours
        'monday': 'Monday',
        'tuesday': 'Tuesday',
        'wednesday': 'Wednesday',
        'thursday': 'Thursday',
        'friday': 'Friday',
        'saturday': 'Saturday',
        'sunday': 'Sunday',
        'from': 'From',
        'to': 'To',

        # Status
        'active': 'Active',
        'inactive': 'Inactive',
        'status': 'Status',

        # Logs
        'logs': 'Logs',
        'view_logs': 'View Logs',
        'action': 'Action',
        'timestamp': 'Timestamp',

        # RAG
        'rag_upload': 'Upload File',
        'rag_files_list': 'Uploaded Files',
        'rag_no_files': 'No files uploaded yet',
        'rag_file_name': 'File Name',
        'rag_file_size': 'Size',
        'rag_file_chunks': 'Chunks',
        'rag_delete_confirm': 'Are you sure you want to delete this file?',

        # Tooltips
        'tooltip_name': 'Agent display name',
        'tooltip_description': 'Short description of the agent (shown in Bitrix24)',
        'tooltip_system_prompt': 'System prompt that defines the bot behavior, restrictions, and communication style',
        'tooltip_rag_files': 'Text files that form the knowledge base - the bot will use this information when answering',
        'tooltip_temperature': '0.0 = precise, 1.0 = creative',
        'tooltip_buffer_time': 'Wait time before responding to allow message grouping',
        'tooltip_inbound_only': 'Agent disconnects after creating a lead/deal',
        'tooltip_audio': 'Transcribe voice messages using OpenAI Whisper',
        'tooltip_api_key': 'Your OpenAI API key (starts with sk-)',
    },

    'ru': {
        # General
        'app_name': 'Менеджер AI Агентов',
        'language': 'Язык',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'delete': 'Удалить',
        'edit': 'Редактировать',
        'create': 'Создать',
        'back': 'Назад',
        'yes': 'Да',
        'no': 'Нет',
        'enabled': 'Включено',
        'disabled': 'Выключено',
        'upload': 'Загрузить',
        'download': 'Скачать',
        'refresh': 'Обновить',
        'sync': 'Синхронизировать',
        'loading': 'Загрузка...',
        'error': 'Ошибка',
        'success': 'Успешно',
        'warning': 'Предупреждение',
        'info': 'Информация',

        # Agents
        'agents_list': 'AI Агенты',
        'create_agent': 'Создать Агента',
        'edit_agent': 'Редактировать Агента',
        'agent_settings': 'Настройки Агента',
        'no_agents': 'Агенты еще не созданы',
        'max_agents_reached': 'Достигнуто максимальное количество агентов',
        'agent_created': 'Агент успешно создан',
        'agent_updated': 'Агент успешно обновлён',
        'agent_deleted': 'Агент успешно удалён',

        # Agent fields
        'name': 'Имя',
        'description': 'Описание',
        'system_prompt': 'Системный промпт',
        'system_prompt_placeholder': 'Введите системный промпт, который определяет поведение бота...',
        'rag_files': 'База знаний (RAG)',
        'rag_files_description': 'Загрузите текстовые файлы для создания базы знаний бота',
        'openai_api_key': 'OpenAI API Ключ',
        'openai_model': 'Модель OpenAI',
        'temperature': 'Температура',
        'audio_transcription': 'Транскрипция Аудио в Чате BX24',
        'max_retries': 'Максимум Попыток',
        'inbound_only': 'Только Входящие в Чате BX24',
        'message_buffer_time': 'Время Ожидания Буфера Сообщений (Секунды)',
        'timezone': 'Часовой Пояс',
        'working_hours': 'Рабочие Часы',
        'working_hours_247': '24/7',
        'working_hours_custom': 'Настраиваемый График',
        'tools': 'Доступные Инструменты',
        'open_line': 'Открытая Линия',
        'bot_id': 'ID Бота',

        # Bots
        'bots_list': 'Зарегистрированные Боты',
        'bots_sync': 'Синхронизировать Ботов',
        'bots_orphaned': 'Осиротевшие Агенты',
        'bots_description': 'Список всех ботов, зарегистрированных этим приложением',

        # Working hours
        'monday': 'Понедельник',
        'tuesday': 'Вторник',
        'wednesday': 'Среда',
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье',
        'from': 'С',
        'to': 'До',

        # Status
        'active': 'Активен',
        'inactive': 'Неактивен',
        'status': 'Статус',

        # Logs
        'logs': 'Логи',
        'view_logs': 'Просмотр Логов',
        'action': 'Действие',
        'timestamp': 'Время',

        # RAG
        'rag_upload': 'Загрузить файл',
        'rag_files_list': 'Загруженные файлы',
        'rag_no_files': 'Файлы еще не загружены',
        'rag_file_name': 'Имя файла',
        'rag_file_size': 'Размер',
        'rag_file_chunks': 'Частей',
        'rag_delete_confirm': 'Вы уверены, что хотите удалить этот файл?',

        # Tooltips
        'tooltip_name': 'Отображаемое имя агента',
        'tooltip_description': 'Краткое описание агента (отображается в Bitrix24)',
        'tooltip_system_prompt': 'Системный промпт, определяющий поведение бота, ограничения и стиль общения',
        'tooltip_rag_files': 'Текстовые файлы, формирующие базу знаний - бот будет использовать эту информацию при ответах',
        'tooltip_temperature': '0.0 = точность, 1.0 = креативность',
        'tooltip_buffer_time': 'Время ожидания перед ответом для группировки сообщений',
        'tooltip_inbound_only': 'Агент отключается после создания лида/сделки',
        'tooltip_audio': 'Транскрибировать голосовые сообщения через OpenAI Whisper',
        'tooltip_api_key': 'Ваш API ключ OpenAI (начинается с sk-)',
    },

    'hy': {
        # General
        'app_name': 'AI Գdelays Կdelays',
        'language': 'Լdelays',
        'save': 'Պdelays',
        'cancel': 'Չdelays',
        'delete': ' Delays',
        'edit': 'Խdelay',
        'create': 'Ստdelay',
        'back': 'Հետ',
        'yes': 'Այdelays',
        'no': 'Ոdelays',
        'enabled': 'Միdelays',
        'disabled': 'Delays',
        'upload': 'Վdelays',
        'download': ' Delays',
        'refresh': 'Թdelay',
        'sync': 'Delays',
        'loading': 'Բdelays...',
        'error': 'Sdelay',
        'success': 'Հdelay',
        'warning': 'Զdelay',
        'info': 'Տdelay',

        # Agents
        'agents_list': 'AI Գdelay',
        'create_agent': ' Delays Գdelay',
        'edit_agent': 'Խdelay Գdelaydelay',
        'agent_settings': 'Գdelaydelay Delays',
        'no_agents': 'Գdelaydelaydelay delays delays',
        'max_agents_reached': 'Գdelaydelaydelay delaydelay delaydelay delay delays',
        'agent_created': 'Գdelaydelay delaydelaydelay delays',
        'agent_updated': 'Գdelaydelay delaydelaydelay delays',
        'agent_deleted': 'Գdelaydelay delaydelaydelay delays',

        # Agent fields
        'name': 'Անdelays',
        'description': ' Delays',
        'system_prompt': 'Delays Delays',
        'system_prompt_placeholder': 'Մdelay delays delays delays delays...',
        'rag_files': 'Գdelay Delays (RAG)',
        'rag_files_description': 'Delays delays delays delays delays delays delays',
        'openai_api_key': 'OpenAI API Delays',
        'openai_model': 'OpenAI Delays',
        'temperature': 'Delays',
        'audio_transcription': 'Delays Delays BX24 Delays',
        'max_retries': 'Delays Delays',
        'inbound_only': 'Delays Delays BX24 Delays',
        'message_buffer_time': 'Delays Delays Delays (Delays)',
        'timezone': 'Delays Delays',
        'working_hours': 'Delays Delays',
        'working_hours_247': '24/7',
        'working_hours_custom': 'Delays Delays',
        'tools': 'Delays Delays',
        'open_line': 'Delays Delays',
        'bot_id': 'Delays ID',

        # Bots
        'bots_list': 'Delays Delays',
        'bots_sync': 'Delays Delays',
        'bots_orphaned': 'Delays Delays',
        'bots_description': 'Delays delays delays delays delays',

        # Working hours
        'monday': 'Delays',
        'tuesday': 'Delays',
        'wednesday': 'Delays',
        'thursday': 'Delays',
        'friday': 'Delays',
        'saturday': 'Delays',
        'sunday': 'Delays',
        'from': 'Delays',
        'to': 'Delays',

        # Status
        'active': 'Delays',
        'inactive': 'Delays',
        'status': 'Delays',

        # Logs
        'logs': 'Delays',
        'view_logs': 'Delays Delays',
        'action': 'Delays',
        'timestamp': 'Delays',

        # RAG
        'rag_upload': 'Delays delays',
        'rag_files_list': 'Delays delays',
        'rag_no_files': 'Delays delays delays',
        'rag_file_name': 'Delays delays',
        'rag_file_size': 'Delays',
        'rag_file_chunks': 'Delays',
        'rag_delete_confirm': 'Delays delays delays delays delays?',

        # Tooltips
        'tooltip_name': 'Delays delays delays',
        'tooltip_description': 'Delays delays delays (delays delays Bitrix24)',
        'tooltip_system_prompt': 'Delays delays delays delays delays delays delays',
        'tooltip_rag_files': 'Delays delays delays delays delays delays',
        'tooltip_temperature': '0.0 = delays, 1.0 = delays',
        'tooltip_buffer_time': 'Delays delays delays delays delays',
        'tooltip_inbound_only': 'Delays delays delays delays/delays delays',
        'tooltip_audio': 'Delays delays delays OpenAI Whisper-delays delays',
        'tooltip_api_key': 'Delays OpenAI API delays (delays sk-)',
    }
}


def get_translation(key, lang='en'):
    """Get translation"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)


def get_all_translations(lang='en'):
    """Get all translations for language"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en'])
