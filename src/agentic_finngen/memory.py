import json
import os
from typing import Dict, Any, List

class FileBasedMemory:
    def __init__(self, file_path: str = "agent_memory.json"):
        self.file_path = file_path
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {"sessions": {}}

    def _save_memory(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.data["sessions"].get(session_id, {"history": [], "context": {}})

    def update_session(self, session_id: str, key: str, value: Any):
        if session_id not in self.data["sessions"]:
            self.data["sessions"][session_id] = {"history": [], "context": {}}
        self.data["sessions"][session_id]["context"][key] = value
        self._save_memory()

    def add_history(self, session_id: str, role: str, content: str):
        if session_id not in self.data["sessions"]:
            self.data["sessions"][session_id] = {"history": [], "context": {}}
        self.data["sessions"][session_id]["history"].append({"role": role, "content": content})
        self._save_memory()
