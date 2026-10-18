"""Private AI settings; use the existing data volume without schema changes."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from fastapi import HTTPException
from services.private_settings import read_settings, write_settings, settings_lock

MODEL = 'glm-4.6v-flash'
API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
DEFAULTS = {
    'enabled': False, 'api_key': '', 'max_concurrent': 1,
    'user_per_minute': 3, 'user_per_day': 40,
    'global_per_minute': 12, 'global_per_day': 300,
    'min_interval_seconds': 5, 'timeout_seconds': 60, 'max_tokens': 2048,
}

class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    api_key: str = Field(default='', max_length=512)
    clear_api_key: bool = False
    max_concurrent: int = Field(default=1, ge=1, le=2)
    user_per_minute: int = Field(default=3, ge=1, le=6)
    user_per_day: int = Field(default=40, ge=1, le=200)
    global_per_minute: int = Field(default=12, ge=1, le=30)
    global_per_day: int = Field(default=300, ge=1, le=2000)
    min_interval_seconds: int = Field(default=5, ge=2, le=60)
    timeout_seconds: int = Field(default=60, ge=15, le=90)
    max_tokens: int = Field(default=2048, ge=512, le=4096)

    @field_validator('api_key')
    @classmethod
    def valid_key(cls, value):
        value = value.strip()
        if value and (len(value) < 8 or any(not 33 <= ord(char) <= 126 for char in value)):
            raise ValueError('Invalid API key')
        return value


def load_ai_settings():
    # Revalidate on load, so edited configuration cannot bypass resource budgets.
    try:
        with settings_lock:
            saved = read_settings('ai-settings.json', {})
        settings = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
        data = AISettingsUpdate.model_validate(settings).model_dump(exclude={'clear_api_key'})
    except (AttributeError, ValueError, TypeError, OSError):
        raise HTTPException(503, 'AI 配置无法读取，请联系系统管理员检查服务器配置') from None
    return data


def public_settings(settings):
    return {**{k: v for k, v in settings.items() if k != 'api_key'},
            'configured': bool(settings['api_key']), 'model': MODEL}


def save_ai_settings(data):
    with settings_lock:
        existing = load_ai_settings()
        result = data.model_dump(exclude={'clear_api_key'})
        result['api_key'] = '' if data.clear_api_key else data.api_key or existing['api_key']
        if result['enabled'] and not result['api_key']:
            raise HTTPException(422, '请先填写 API Key，再启用 AI 问答')
        write_settings('ai-settings.json', result)
    return public_settings(result)
