# config.py
"""
Configuration for AI Agents Manager

Updated: 2025
- Added new OpenAI models
- Added RAG settings
"""
import os


class Config:
    # Bitrix24 App credentials
    CLIENT_ID = os.environ.get('BITRIX_CLIENT_ID', 'local.697c6cefcb4d06.94919258')
    CLIENT_SECRET = os.environ.get('BITRIX_CLIENT_SECRET', 'ZWKavhd6p5hB030JnwSMcb5KvvDT29Lc4ZfWvdzrE1JTSZhGOG')

    # Публичный URL приложения (URL вашего Cloudflare туннеля)
    # ВАЖНО: Укажите здесь URL вашего туннеля без слеша в конце!
    # Например: 'https://your-tunnel-name.trycloudflare.com'
    PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://chemistry-preserve-preview-diana.trycloudflare.com')

    # Database
    DATABASE = os.environ.get('DATABASE_PATH', 'ai_agents.db')

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Limits
    MAX_AGENTS = int(os.environ.get('MAX_AGENTS', 2))

    # Polling settings (legacy, not used in webhook architecture)
    POLLING_INTERVAL = 3

    # Supported languages
    LANGUAGES = ['en', 'ru', 'hy']
    DEFAULT_LANGUAGE = 'en'

    # OpenAI settings - Updated model list for 2025
    OPENAI_MODELS = [
        'gpt-4o',           # Latest GPT-4 Omni
        'gpt-4o-mini',      # Cost-effective GPT-4
        'gpt-4-turbo',      # GPT-4 Turbo
        'gpt-4',            # Standard GPT-4
        'gpt-3.5-turbo',    # GPT-3.5 (legacy, cheaper)
        'o1-preview',       # Reasoning model
        'o1-mini',          # Smaller reasoning model
    ]

    # RAG Settings
    RAG_CHUNK_SIZE = int(os.environ.get('RAG_CHUNK_SIZE', 2000))
    RAG_MAX_CONTEXT = int(os.environ.get('RAG_MAX_CONTEXT', 4000))

    # Timezones (popular ones)
    TIMEZONES = [
        'UTC',
        'Europe/Moscow',
        'Asia/Yerevan',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'America/New_York',
        'America/Los_Angeles',
        'America/Chicago',
        'Asia/Dubai',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Australia/Sydney'
    ]

    # Max file size for RAG uploads (in bytes)
    MAX_RAG_FILE_SIZE = int(os.environ.get('MAX_RAG_FILE_SIZE', 10 * 1024 * 1024))  # 10 MB
