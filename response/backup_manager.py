# ============================================================
# ENTROPY - Backup & Recovery Manager
# response/backup_manager.py
#
# WHAT THIS DOES:
# Captures hash-verified clean versions of watched files and
# restores the last known-good version after a confirmed threat.
#
# DESIGN NOTES:
# - Versions are stored content-addressed (by SHA-256), so
#   identical content is deduplicated and tampering with a
#   stored blob is detectable via the manifest hash.
# - "Clean" = entropy at capture time was below the detection
#   threshold. Restore only ever considers clean versions that
#   were captured BEFORE the threat event, so the system can
#   never restore attacker-written content.
# - Capture is additive (reads the victim file, writes only to
#   backup_storage/) and therefore runs even in dry-run mode.
# - Restore is a repair action: in dry-run mode the backup is
#   verified but the victim file is left untouched; with
#   ENTROPY_DRY_RUN=false the clean version is restored in
#   place (atomic write + post-write hash verification).
#
# NOTE ON "DECRYPTION":
# Ransomware-encrypted files cannot be decrypted — the key is
# held by the attacker. Recovery in this system means restoring
# a known-good copy captured before the attack.
# ============================================================

import json
import math
import os
import shutil
import time
from datetime import datetime
from threading import Lock

import config
from storage.hashing import sha256_file


def _file_entropy_sample(file_path: str, sample_size: int | None = None):
    """Bounded Shannon entropy of a file's first *sample_size* bytes."""
    sample_size = sample_size or config.SAMPLE_SIZE_BYTES
    try:
        with open(file_path, "rb") as handle:
            data = handle.read(sample_size)
    except OSError:
        return None
    if not data:
        return 0.0
    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _is_clean(file_path: str, entropy, strict: bool = False,
              last_clean_entropy: float | None = None) -> bool:
    """Label a version clean using the same ranges as the detector.

    Known file types are compared against their per-extension normal
    range (with the detector's 0.5 measurement-noise margin); unknown
    types fall back to the global entropy threshold.

    ``strict`` (event-time captures): the content must look NATIVE to
    the file type — inside its normal range with no noise margin —
    and, when the last clean version's entropy is known, must not be a
    dramatic change from it (>= ENTROPY_DELTA_THRESHOLD apart).
    Ransomware ciphertext for office formats (7.8-8.0) fails the
    range test (xlsx/docx/jpg) and the delta test (pdf/txt); in-range
    media ciphertext (the documented blind spot) can still pass — no
    entropy rule can separate it from native content, so such files
    are the known, accepted residual risk.
    """
    if entropy is None:
        return False
    entropy = float(entropy)
    _, ext = os.path.splitext(file_path)
    normal = config.NORMAL_ENTROPY_RANGES.get(ext.lower())
    if not strict:
        if normal:
            return entropy <= normal[1] + 0.5
        return entropy < config.ENTROPY_THRESHOLD
    if normal is None:
        # Unknown type at event time: the content cannot be vouched
        # for — forensics only, never a restore source.
        return False
    if entropy > normal[1]:
        return False
    if (last_clean_entropy is not None
            and abs(entropy - last_clean_entropy)
            >= config.ENTROPY_DELTA_THRESHOLD):
        return False
    return True


class BackupManager:
    """Hash-verified, versioned backup store for watched files."""

    def __init__(self, backup_dir: str | None = None,
                 max_versions: int | None = None):
        self.backup_dir = backup_dir or config.BACKUP_DIR
        self.versions_dir = os.path.join(self.backup_dir, "versions")
        self.manifest_path = os.path.join(self.backup_dir, "manifest.json")
        self.max_versions = max_versions or config.BACKUP_MAX_VERSIONS_PER_FILE
        self.lock = Lock()
        os.makedirs(self.versions_dir, exist_ok=True)

    # ── Manifest ─────────────────────────────────────────────

    def _load_manifest(self) -> dict:
        try:
            with open(self.manifest_path, encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_manifest(self, manifest: dict) -> None:
        temporary = self.manifest_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.manifest_path)

    # ── Version store ────────────────────────────────────────

    def _version_path(self, sha256: str) -> str:
        return os.path.join(self.versions_dir, sha256)

    def _store_blob(self, file_path: str) -> str | None:
        """Copy *file_path* into the content-addressed store."""
        digest = sha256_file(file_path)
        if not digest:
            return None
        target = self._version_path(digest)
        if not os.path.exists(target):
            os.makedirs(self.versions_dir, exist_ok=True)
            temporary = f"{target}.tmp.{os.getpid()}"
            try:
                shutil.copy2(file_path, temporary)
                if sha256_file(temporary) != digest:
                    os.unlink(temporary)
                    return None
                os.replace(temporary, target)
            except OSError:
                if os.path.exists(temporary):
                    os.unlink(temporary)
                return None
        return digest

    def _evict_unreferenced_blobs(self, manifest: dict) -> None:
        """Remove version blobs no manifest entry references.

        Only names that look like SHA-256 digests (64 hex chars) are
        considered; temporary and foreign files are left alone.
        """
        referenced = {
            entry["sha256"]
            for versions in manifest.values()
            for entry in versions
        }
        try:
            for blob in os.listdir(self.versions_dir):
                if len(blob) != 64:
                    continue
                if blob not in referenced:
                    path = os.path.join(self.versions_dir, blob)
                    if os.path.isfile(path):
                        try:
                            from response.defender_actions import \
                                get_registry
                            get_registry().record_moved_away(path)
                        except Exception:
                            pass
                        os.unlink(path)
        except OSError:
            pass

    # ── Capture ──────────────────────────────────────────────

    def capture(self, file_path: str, event: dict | None = None,
                *, strict: bool = False) -> dict:
        """Store the current content of *file_path* as a new version.

        Capture is additive: it reads the victim file and writes only
        into the backup store, so it is safe in every mode.

        ``strict`` marks the version with the no-margin clean rule —
        use it for event-time captures, where the triggering event is
        itself suspicious and the current content is the "after" state.
        """
        event = event or {}
        result = {
            "success": False,
            "captured": False,
            "version": None,
            "sha256": None,
            "clean": None,
            "message": "",
            "timestamp": datetime.now().isoformat(),
            "dry_run": bool(config.DRY_RUN),
        }

        if not file_path or not os.path.isfile(file_path):
            result["message"] = "File not found (capture skipped)"
            return result

        entropy = event.get("entropy_overall")

        with self.lock:
            # Clean label is computed atomically against the current
            # manifest: strict (event-time) captures compare against
            # the last clean version's entropy.
            manifest = self._load_manifest()
            existing = manifest.get(file_path) or []
            last_clean_entropy = None
            for v in reversed(existing):
                if v.get("clean") and v.get("entropy") is not None:
                    last_clean_entropy = float(v["entropy"])
                    break
            clean = _is_clean(file_path, entropy, strict=strict,
                              last_clean_entropy=last_clean_entropy)
            try:
                digest = self._store_blob(file_path)
            except Exception as exc:
                result["message"] = f"Capture error: {exc}"
                return result

            if not digest:
                result["message"] = "Capture failed: could not fingerprint file"
                return result

            versions = manifest.setdefault(file_path, [])
            version = max((v.get("version", 0) for v in versions), default=0) + 1

            versions.append({
                "version": version,
                "sha256": digest,
                "size_bytes": os.path.getsize(file_path),
                "captured_at": result["timestamp"],
                "event_type": event.get("event_type", ""),
                "entropy": entropy,
                "clean": clean,
            })

            # Keep the store bounded: drop the oldest versions beyond
            # the configured cap, renumber, then evict orphaned blobs.
            if len(versions) > self.max_versions:
                del versions[: len(versions) - self.max_versions]
                for index, v in enumerate(versions, start=1):
                    v["version"] = index
                self._evict_unreferenced_blobs(manifest)

            try:
                self._save_manifest(manifest)
            except OSError as exc:
                result["message"] = f"Manifest error: {exc}"
                return result

        result.update({
            "success": True,
            "captured": True,
            "version": version,
            "sha256": digest,
            "clean": clean,
            "message": f"Version {version} captured"
                       + ("" if clean else " (above entropy threshold)"),
        })
        return result

    def snapshot_directory(self, root: str,
                           source: str = "startup_baseline") -> int:
        """Capture a pre-watch baseline of every file under *root*.

        Returns the number of files captured. This is what makes
        restore possible for files that existed before the monitor
        started.
        """
        captured = 0
        if not os.path.isdir(root):
            return 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not os.path.isfile(path):
                    continue
                # The snapshot has no pipeline event, so measure the
                # entropy here — this labels the baseline clean/dirty
                # the same way live events do.
                event = {
                    "event_type": source,
                    "file_path": path,
                    "timestamp": datetime.now().isoformat(),
                    "entropy_overall": _file_entropy_sample(path),
                }
                if self.capture(path, event=event)["success"]:
                    captured += 1
        return captured

    def transfer(self, old_path: str, new_path: str) -> bool:
        """Move the version history from *old_path* to *new_path*.

        Ransomware encrypts in place and then RENAMES (disguise).
        Without this, the clean versions captured before the rename
        are orphaned under the old path and restore — which looks up
        by current path — can never find them. The monitor already
        transfers entropy history across renames; the backup store
        must do the same or rename-based attacks are unrecoverable.

        Returns True if versions were moved.
        """
        if not old_path or not new_path or old_path == new_path:
            return False
        with self.lock:
            try:
                manifest = self._load_manifest()
                versions = manifest.pop(old_path, None)
                if not versions:
                    return False
                manifest.setdefault(new_path, []).extend(versions)
                self._save_manifest(manifest)
                return True
            except OSError:
                return False

    # ── Restore ─────────────────────────────────────────────

    def find_restore_candidate(self, file_path: str,
                               before_iso: str | None = None) -> dict | None:
        """Latest CLEAN version captured before *before_iso* (if given)."""
        manifest = self._load_manifest()
        versions = manifest.get(file_path) or []
        clean_versions = [v for v in versions if v.get("clean")]
        if before_iso:
            clean_versions = [
                v for v in clean_versions
                if v.get("captured_at", "") <= before_iso
            ]
        if not clean_versions:
            return None
        best = max(clean_versions, key=lambda v: (v.get("captured_at", ""),
                                                   v.get("version", 0)))
        blob = self._version_path(best["sha256"])
        if not os.path.isfile(blob):
            return None
        try:
            if sha256_file(blob) != best["sha256"]:
                return None  # stored blob no longer verifies — refuse
        except OSError:
            return None
        return best

    def restore(self, file_path: str, event: dict | None = None) -> dict:
        """Restore the last known-good version of *file_path*.

        Dry-run: the candidate backup is verified but the file is
        left untouched. Live mode: atomic replace + post-write
        hash verification.
        """
        event = event or {}
        result = {
            "success": False,
            "restored": False,
            "dry_run": bool(config.DRY_RUN),
            "sha256": None,
            "version": None,
            "message": "",
            "timestamp": datetime.now().isoformat(),
        }

        candidate = self.find_restore_candidate(
            file_path, before_iso=event.get("timestamp")
        )
        if candidate is None:
            result["message"] = "No clean backup available to restore"
            return result

        result["sha256"] = candidate["sha256"]
        result["version"] = candidate.get("version")

        if config.DRY_RUN:
            result.update({
                "success": True,
                "restored": False,
                "message": (
                    f"Dry-run: restore simulated (clean v"
                    f"{candidate.get('version')} verified, file left in place)"
                ),
            })
            return result

        blob = self._version_path(candidate["sha256"])
        directory = os.path.dirname(os.path.abspath(file_path)) or "."
        temporary = os.path.join(
            directory, f".restore_tmp.{os.getpid()}.{int(time.time_ns())}"
        )
        try:
            os.makedirs(directory, exist_ok=True)
            shutil.copy2(blob, temporary)
            if sha256_file(temporary) != candidate["sha256"]:
                raise OSError("Post-copy hash mismatch during restore")
            os.replace(temporary, file_path)  # atomic on POSIX/NTFS
        except Exception as exc:
            if os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            result["message"] = f"Restore failed: {exc}"
            return result

        result.update({
            "success": True,
            "restored": True,
            "message": (
                f"Restored clean v{candidate.get('version')} "
                f"(captured {candidate.get('captured_at')})"
            ),
        })
        return result

    # ── Introspection ────────────────────────────────────────

    def list_backups(self) -> list:
        """Per-file summary of the backup store."""
        manifest = self._load_manifest()
        summary = []
        for file_path in sorted(manifest):
            versions = manifest[file_path]
            clean = [v for v in versions if v.get("clean")]
            latest = max(versions, key=lambda v: v.get("version", 0)) \
                if versions else None
            summary.append({
                "file_path": file_path,
                "versions": len(versions),
                "clean_versions": len(clean),
                "latest_version": latest.get("version") if latest else 0,
                "latest_sha256": latest.get("sha256") if latest else None,
                "latest_captured_at": latest.get("captured_at") if latest else None,
                "restorable": bool(clean),
            })
        return summary

    def stats(self) -> dict:
        summary = self.list_backups()
        return {
            "files_protected": len(summary),
            "versions_stored": sum(s["versions"] for s in summary),
            "files_restorable": sum(1 for s in summary if s["restorable"]),
            "backup_dir": self.backup_dir,
        }
