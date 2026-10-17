"""Fon vazifalari. 1-bosqichda faqat skelet; import, yil nusxalash, hisoblash, hisobot va
ESPOS outbox vazifalari keyingi bosqichlarda modullarning `tasks.py` fayllarida qo‘shiladi."""

from celery import Celery

from app.core.config import get_settings

celery = Celery("uniload", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, timezone="Asia/Tashkent")


@celery.task(name="system.ping")
def ping() -> str:
    return "pong"
