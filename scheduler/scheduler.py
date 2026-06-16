import os
import threading
import time
from datetime import datetime, timedelta
import json

MEMORY_DIR = os.path.expanduser("~/.jarvis/memory")


class Scheduler:
    def __init__(self):
        self._reminders = []
        self._timer = None
        self._running = False
        self._on_reminder = None
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._load()

    def set_callback(self, callback):
        self._on_reminder = callback

    def add_reminder(self, message, delay_minutes=0, when=None):
        if when:
            reminder_time = when
        else:
            reminder_time = datetime.now() + timedelta(minutes=delay_minutes)
        reminder = {
            "id": len(self._reminders) + 1,
            "message": message,
            "time": reminder_time.isoformat(),
            "active": True
        }
        self._reminders.append(reminder)
        self._save()
        self._reschedule()
        return reminder["id"]

    def add_cron(self, message, cron_expr):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            if not hasattr(self, '_aps'):
                self._aps = BackgroundScheduler()
                self._aps.start()
            job_id = f"cron_{hash(message)}_{int(time.time())}"
            parts = cron_expr.strip().split()
            if len(parts) == 5:
                self._aps.add_job(
                    lambda: self._fire(message),
                    trigger='cron',
                    minute=parts[0], hour=parts[1], day=parts[2],
                    month=parts[3], day_of_week=parts[4],
                    id=job_id
                )
            return f"Agendado: '{message}' com cron '{cron_expr}'"
        except ImportError:
            return "APScheduler não instalado. `pip install apscheduler`"

    def list_reminders(self):
        now = datetime.now()
        active = []
        for r in self._reminders:
            if not r["active"]:
                continue
            rt = datetime.fromisoformat(r["time"])
            remaining = (rt - now).total_seconds()
            if remaining > 0:
                active.append({**r, "remaining_min": int(remaining / 60)})
        return active

    def cancel_reminder(self, reminder_id):
        for r in self._reminders:
            if r["id"] == reminder_id:
                r["active"] = False
                self._save()
                return f"Lembrete {reminder_id} cancelado"
        return "Lembrete não encontrado"

    def _fire(self, message):
        if self._on_reminder:
            self._on_reminder(message)

    def _reschedule(self):
        if self._timer:
            self._timer.cancel()
        now = datetime.now()
        next_reminder = None
        for r in self._reminders:
            if not r["active"]:
                continue
            rt = datetime.fromisoformat(r["time"])
            if rt > now:
                if next_reminder is None or rt < next_reminder:
                    next_reminder = rt
        if next_reminder:
            delay = (next_reminder - now).total_seconds()
            self._timer = threading.Timer(delay, self._fire_reminders)
            self._timer.daemon = True
            self._timer.start()

    def _fire_reminders(self):
        now = datetime.now()
        for r in self._reminders:
            if not r["active"]:
                continue
            rt = datetime.fromisoformat(r["time"])
            if rt <= now:
                self._fire(r["message"])
                r["active"] = False
        self._save()
        self._reschedule()

    def _save(self):
        try:
            with open(os.path.join(MEMORY_DIR, "reminders.json"), "w") as f:
                json.dump(self._reminders, f)
        except Exception:
            pass

    def _load(self):
        try:
            path = os.path.join(MEMORY_DIR, "reminders.json")
            if os.path.exists(path):
                with open(path) as f:
                    self._reminders = json.load(f)
        except Exception:
            self._reminders = []

    def stop(self):
        if hasattr(self, '_aps'):
            self._aps.shutdown(wait=False)
