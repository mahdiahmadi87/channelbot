import pytest
import json
from pathlib import Path
from app.services.storage import StorageService

@pytest.fixture
def temp_storage_file(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d / "test_admins.json"

@pytest.mark.asyncio
async def test_add_admin(temp_storage_file: Path):
    storage = StorageService(temp_storage_file)
    await storage.add_admin(123, "test_user")
    admins = await storage.get_admins()
    assert len(admins) == 1
    assert admins[0]["id"] == 123
    assert admins[0]["alias"] == "test_user"

@pytest.mark.asyncio
async def test_remove_admin(temp_storage_file: Path):
    storage = StorageService(temp_storage_file)
    await storage.add_admin(123, "test_user")
    await storage.add_admin(456, "another_user")
    
    removed = await storage.remove_admin(123)
    assert removed is True
    
    admins = await storage.get_admins()
    assert len(admins) == 1
    assert admins[0]["id"] == 456
    
    not_removed = await storage.remove_admin(999)
    assert not_removed is False

@pytest.mark.asyncio
async def test_backup_rotation(temp_storage_file: Path):
    storage = StorageService(temp_storage_file, backup_count=2)
    
    # First write
    await storage.add_admin(1, "a")
    assert temp_storage_file.with_suffix(".bak1").exists() is True
    assert temp_storage_file.with_suffix(".bak2").exists() is False

    # Second write
    await storage.add_admin(2, "b")
    assert temp_storage_file.with_suffix(".bak1").exists() is True
    assert temp_storage_file.with_suffix(".bak2").exists() is True
    
    # Third write - should rotate
    await storage.add_admin(3, "c")
    assert temp_storage_file.with_suffix(".bak1").exists() is True
    assert temp_storage_file.with_suffix(".bak2").exists() is True
    assert temp_storage_file.with_suffix(".bak3").exists() is False
    
    # check content of backup 2
    with open(temp_storage_file.with_suffix(".bak2"), 'r') as f:
        data = json.load(f)
        assert len(data['admins']) == 1