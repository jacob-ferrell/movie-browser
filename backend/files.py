import os
import shutil
import stat

JAIL = "/hdd"


def _safe(path):
    """Resolve path and verify it stays within JAIL. Returns the real absolute path."""
    real = os.path.realpath(path)
    if real != JAIL and not real.startswith(JAIL + "/"):
        raise PermissionError(f"Path outside {JAIL}")
    return real


def list_dir(path):
    """Return sorted directory listing: dirs first, then files.

    Each entry: {name, is_dir, size (None for dirs), modified (unix ts), path (full)}
    """
    safe = _safe(path)
    if not os.path.isdir(safe):
        raise NotADirectoryError(f"Not a directory: {path}")
    entries = []
    for name in os.listdir(safe):
        if name.startswith('.fuse_hidden'):
            continue
        full = os.path.join(safe, name)
        try:
            st = os.stat(full)
            is_dir = os.path.isdir(full)
            entries.append({
                "name": name,
                "is_dir": is_dir,
                "size": None if is_dir else st.st_size,
                "modified": int(st.st_mtime),
                "path": full,
            })
        except OSError:
            continue
    # Dirs first, then files — both alphabetically (case-insensitive)
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries


def delete_path(path):
    """Delete a file or directory tree.

    Walks bottom-up so we see the exact file/dir that fails rather than a
    cryptic 'Directory not empty' from the parent.
    """
    safe = _safe(path)
    if safe == JAIL:
        raise PermissionError("Cannot delete the root /hdd directory")
    if os.path.isdir(safe):
        errors = []
        for root, dirs, files in os.walk(safe, topdown=False, followlinks=False):
            for name in files:
                fp = os.path.join(root, name)
                try:
                    os.unlink(fp)
                except Exception as e:
                    # Try chmod first in case the file is read-only
                    try:
                        os.chmod(fp, stat.S_IRUSR | stat.S_IWUSR)
                        os.unlink(fp)
                    except Exception:
                        errors.append(f"{fp}: {e}")
            for name in dirs:
                dp = os.path.join(root, name)
                try:
                    os.rmdir(dp)
                except Exception as e:
                    errors.append(f"{dp}: {e}")
        try:
            os.rmdir(safe)
        except Exception as e:
            errors.append(f"{safe}: {e}")
        if errors:
            fuse_blocked = [e for e in errors if '.fuse_hidden' in e]
            other = [e for e in errors if '.fuse_hidden' not in e]
            if fuse_blocked and not other:
                raise OSError(
                    "Some files are held open by another process (ntfs-3g .fuse_hidden). "
                    "Pause or remove the torrent in qBittorrent first, then try again."
                )
            raise OSError("\n".join(errors))
    else:
        os.remove(safe)


def path_size(path):
    """Return total byte size of a file or directory tree."""
    safe = _safe(path)
    if os.path.isfile(safe):
        return os.path.getsize(safe)
    total = 0
    for root, _dirs, files in os.walk(safe, followlinks=False):
        for name in files:
            if name.startswith('.fuse_hidden'):
                continue
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def disk_usage():
    """Return disk usage for /hdd as {total, used, free} in bytes."""
    usage = shutil.disk_usage(JAIL)
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def rename_path(path, new_name):
    """Rename a file or directory in place. new_name must be a plain basename."""
    if not new_name or "/" in new_name or new_name in (".", ".."):
        raise ValueError("new_name must be a plain filename with no slashes")
    safe = _safe(path)
    if safe == JAIL:
        raise PermissionError("Cannot rename the root /hdd directory")
    dest = os.path.join(os.path.dirname(safe), new_name)
    # Validate destination is also within jail
    _safe(dest)
    if os.path.exists(dest):
        raise FileExistsError(f"'{new_name}' already exists")
    os.rename(safe, dest)


def move_path(src, dest_dir):
    """Move src into dest_dir (result: dest_dir/basename(src))."""
    safe_src = _safe(src)
    safe_dest_dir = _safe(dest_dir)
    if safe_src == JAIL:
        raise PermissionError("Cannot move the root /hdd directory")
    if not os.path.isdir(safe_dest_dir):
        raise NotADirectoryError(f"Destination is not a directory: {dest_dir}")
    dest = os.path.join(safe_dest_dir, os.path.basename(safe_src))
    if os.path.exists(dest):
        raise FileExistsError(f"'{os.path.basename(safe_src)}' already exists in destination")
    shutil.move(safe_src, dest)
