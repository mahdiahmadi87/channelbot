import asyncio
import json
import logging
import shutil
from pathlib import Path

class StorageService:
    def __init__(self, filepath: Path, backup_count: int = 3):
        self.filepath = filepath
        self.backup_count = backup_count
        self.lock = asyncio.Lock()
        self._initialize_file()

    def _initialize_file(self):
        """Ensures the admin file exists and is valid JSON."""
        if not self.filepath.exists():
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"admins": []}, f, indent=2)
        else:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    json.load(f)
            except (json.JSONDecodeError, ValueError):
                logging.error(f"Error: {self.filepath} is malformed. Please fix it or delete it to start fresh.")
                raise ValueError(f"Malformed JSON in {self.filepath}")

    async def _rotate_backups(self):
        """Manages backup rotation."""
        if not self.filepath.exists():
            return
        
        # Delete the oldest backup if we've reached the limit
        oldest_backup = self.filepath.with_suffix(f".bak{self.backup_count}")
        if oldest_backup.exists():
            oldest_backup.unlink()

        # Shift existing backups
        for i in range(self.backup_count - 1, 0, -1):
            src = self.filepath.with_suffix(f".bak{i}")
            dst = self.filepath.with_suffix(f".bak{i+1}")
            if src.exists():
                shutil.move(src, dst)
        
        # Create the newest backup
        shutil.copy(self.filepath, self.filepath.with_suffix(".bak1"))

    async def _read_data(self):
        async with self.lock:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"admins": []}

    async def _write_data(self, data):
        async with self.lock:
            await self._rotate_backups()
            temp_filepath = self.filepath.with_suffix(".tmp")
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomic move
            temp_filepath.rename(self.filepath)

    async def get_admins(self):
        data = await self._read_data()
        return data.get("admins", [])

    async def add_admin(self, user_id: int, alias: str):
        data = await self._read_data()
        admins = data.get("admins", [])
        # Avoid duplicates
        if not any(admin["id"] == user_id for admin in admins):
            admins.append({"id": user_id, "alias": alias})
            data["admins"] = admins
            await self._write_data(data)

    async def remove_admin(self, user_id: int) -> bool:
        data = await self._read_data()
        admins = data.get("admins", [])
        original_len = len(admins)
        admins = [admin for admin in admins if admin["id"] != user_id]
        if len(admins) < original_len:
            data["admins"] = admins
            await self._write_data(data)
            return True
        return False