import uuid
import threading
from datetime import datetime
from app.logger import get_logger

logger = get_logger(__name__)


class ActionQueue:
    def __init__(self):
        self._actions = {}
        self._lock = threading.Lock()

    def add(self, action: dict) -> str:
        action_id = str(uuid.uuid4())
        entry = {
            "action_id": action_id,
            "type": action.get("type"),
            "data": {k: v for k, v in action.items() if k != "type"},
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

        with self._lock:
            self._actions[action_id] = entry

        logger.info("Action queued | id=%s | type=%s", action_id, action.get("type"))
        return action_id

    def get_pending(self) -> list[dict]:
        with self._lock:
            pending = [
                a for a in self._actions.values()
                if a["status"] == "pending"
            ]

        logger.info("Pending actions requested | count=%d", len(pending))
        return pending

    def complete(self, action_id: str) -> bool:
        with self._lock:
            if action_id in self._actions:
                self._actions[action_id]["status"] = "complete"
                logger.info("Action completed | id=%s", action_id)
                return True

        logger.warning("Action not found | id=%s", action_id)
        return False

    def get_all(self) -> list[dict]:
        with self._lock:
            return list(self._actions.values())


action_queue = ActionQueue()