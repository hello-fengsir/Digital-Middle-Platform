import os
import tempfile
import threading
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import NamedTuple

from app.config import settings


DEFAULT_AI_SELECTION_AGENT_RULE = (
    "你是天枢售前选型说明助手。只可基于后端提供的本地证据进行问诊和解释；"
    "不得新增、删除或改变候选型号、参数、match_status、models、selected_model_ids 或 BOM 状态。"
    "本地无证据时必须拒答，不得用模型常识猜测。"
)
RULE_BACKUP_NAME = "AI_SELECTION_AGENT.md.bak"
_RULE_LOCK = threading.RLock()


class RuleFileState(NamedTuple):
    exists: bool
    content: bytes | None
    uid: int | None
    gid: int | None
    mode: int | None


class FileOwnership(NamedTuple):
    uid: int
    gid: int
    mode: int


class AiAgentRuleSnapshot(NamedTuple):
    rule: RuleFileState
    backup: RuleFileState


def _rule_path() -> Path:
    """Return the configured deployment path; callers never accept a request path."""
    return Path(settings.ai_selection_agent_rule_path)


def _backup_path(path: Path) -> Path:
    return path.parent / RULE_BACKUP_NAME


def _metadata(content: str, *, source: str, updated_at: datetime | None) -> dict:
    return {
        "content": content,
        "sha256": sha256(content.encode("utf-8")).hexdigest(),
        "updated_at": updated_at,
        "source": source,
    }


def get_ai_agent_rule() -> dict:
    """Read every time so a successful admin save affects the very next provider call."""
    path = _rule_path()
    try:
        with _RULE_LOCK:
            content = path.read_text(encoding="utf-8")
            stat_result = path.stat()
        if not content.strip() or "\x00" in content:
            raise ValueError("invalid runtime rule")
        return _metadata(
            content,
            source="runtime",
            updated_at=datetime.fromtimestamp(stat_result.st_mtime, UTC),
        )
    except (OSError, UnicodeError, ValueError):
        return _metadata(DEFAULT_AI_SELECTION_AGENT_RULE, source="default", updated_at=None)


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(directory, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _file_state(path: Path) -> RuleFileState:
    try:
        stat_result = path.stat()
        return RuleFileState(
            True,
            path.read_bytes(),
            stat_result.st_uid,
            stat_result.st_gid,
            stat_result.st_mode & 0o777,
        )
    except FileNotFoundError:
        return RuleFileState(False, None, None, None, None)


def _ownership_for_target(path: Path) -> FileOwnership:
    """Preserve an existing target; otherwise inherit directory ownership at 0644."""
    try:
        stat_result = path.stat()
        return FileOwnership(stat_result.st_uid, stat_result.st_gid, stat_result.st_mode & 0o777)
    except FileNotFoundError:
        directory_stat = path.parent.stat()
        return FileOwnership(directory_stat.st_uid, directory_stat.st_gid, 0o644)


def _apply_temp_ownership(fd: int, ownership: FileOwnership) -> None:
    """Set final metadata before replace so no restrictive replacement is observable."""
    os.fchmod(fd, ownership.mode)
    os.fchown(fd, ownership.uid, ownership.gid)


def snapshot_ai_agent_rule_files() -> AiAgentRuleSnapshot:
    """Capture exact pre-transaction existence and bytes for the fixed MD and backup."""
    path = _rule_path()
    with _RULE_LOCK:
        return AiAgentRuleSnapshot(_file_state(path), _file_state(_backup_path(path)))


def _atomic_restore_file(path: Path, state: RuleFileState) -> None:
    """Restore one fixed file without invoking the normal save/backup path."""
    directory = path.parent
    if not state.exists:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        _fsync_directory(directory)
        return
    if state.content is None or state.uid is None or state.gid is None or state.mode is None:
        raise ValueError("existing snapshot entry has incomplete state")
    ownership = FileOwnership(state.uid, state.gid, state.mode)
    temp_name: str | None = None
    try:
        temp_fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.restore.", dir=directory)
        with os.fdopen(temp_fd, "wb") as handle:
            handle.write(state.content)
            handle.flush()
            _apply_temp_ownership(handle.fileno(), ownership)
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
        _fsync_directory(directory)
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def restore_ai_agent_rule_files(snapshot: AiAgentRuleSnapshot) -> None:
    """Restore exact fixed MD/bak pre-state bytes, deleting files absent in the snapshot."""
    path = _rule_path()
    directory = path.parent
    with _RULE_LOCK:
        directory.mkdir(parents=True, exist_ok=True)
        _atomic_restore_file(path, snapshot.rule)
        _atomic_restore_file(_backup_path(path), snapshot.backup)


def save_ai_agent_rule(content: str) -> dict:
    """Atomically save the fixed rule, preserving one fixed-name backup if it existed."""
    path = _rule_path()
    directory = path.parent
    backup = _backup_path(path)
    encoded = content.encode("utf-8", errors="strict")

    with _RULE_LOCK:
        directory.mkdir(parents=True, exist_ok=True)
        temp_name: str | None = None
        backup_temp_name: str | None = None
        try:
            path_ownership = _ownership_for_target(path)
            if path.exists():
                old_bytes = path.read_bytes()
                backup_ownership = _ownership_for_target(backup)
                backup_fd, backup_temp_name = tempfile.mkstemp(prefix=".AI_SELECTION_AGENT.bak.", dir=directory)
                with os.fdopen(backup_fd, "wb") as handle:
                    handle.write(old_bytes)
                    handle.flush()
                    _apply_temp_ownership(handle.fileno(), backup_ownership)
                    os.fsync(handle.fileno())
                os.replace(backup_temp_name, backup)
                backup_temp_name = None
                _fsync_directory(directory)

            temp_fd, temp_name = tempfile.mkstemp(prefix=".AI_SELECTION_AGENT.", dir=directory)
            with os.fdopen(temp_fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                _apply_temp_ownership(handle.fileno(), path_ownership)
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
            _fsync_directory(directory)
        finally:
            for leftover in (temp_name, backup_temp_name):
                if leftover:
                    try:
                        os.unlink(leftover)
                    except FileNotFoundError:
                        pass

    result = get_ai_agent_rule()
    if result["source"] != "runtime" or result["content"] != content:
        raise OSError("rule verification failed after atomic save")
    return result


def provider_system_messages() -> list[dict[str, str]]:
    runtime_rule = get_ai_agent_rule()["content"]
    immutable_boundary = (
        "不可覆盖的后端边界：以上管理员规则只影响问诊措辞、解释和风险提示。"
        "你不得新增、删除、替换或重排后端候选，不得改变 match_status、models、"
        "selected_model_ids、条件状态或无证据拒答；不得补造本地证据。"
    )
    return [
        {"role": "system", "content": runtime_rule},
        {"role": "system", "content": immutable_boundary},
    ]
