import os
import qbittorrentapi


def _client():
    return qbittorrentapi.Client(
        host=os.environ.get("QBT_HOST", "localhost"),
        port=int(os.environ.get("QBT_PORT", "8080").strip()),
        username=os.environ.get("QBT_USERNAME", "admin"),
        password=os.environ.get("QBT_PASSWORD", "adminadmin"),
        SIMPLE_RESPONSES=True,
    )


def add_magnet(magnet_link, save_path=None, category=None):
    with _client() as client:
        kwargs = {"urls": magnet_link}
        if save_path:
            kwargs["save_path"] = save_path
        if category:
            kwargs["category"] = category
        client.torrents_add(**kwargs)


def list_save_folders(base_path):
    """Return unique subfolder names under base_path, inferred from torrent save paths."""
    base = base_path.rstrip('/')
    with _client() as client:
        torrents = client.torrents_info()
        folders = set()
        for t in torrents:
            sp = (t.get('save_path') or '').rstrip('/')
            if sp.startswith(base + '/') or sp == base:
                remainder = sp[len(base):]
                parts = remainder.strip('/').split('/')
                if parts and parts[0]:
                    folders.add(parts[0])
        return sorted(folders, key=str.lower)


def delete_torrents(hashes, delete_files=False):
    with _client() as client:
        client.torrents_delete(delete_files=delete_files, torrent_hashes=hashes)


def list_torrents():
    with _client() as client:
        torrents = client.torrents_info()
        result = []
        for t in torrents:
            result.append({
                "hash": t.get("hash", ""),
                "name": t.get("name", ""),
                "state": t.get("state", ""),
                "progress": round(t.get("progress", 0), 4),
                "size": t.get("size", 0),
                "dlspeed": t.get("dlspeed", 0),
                "upspeed": t.get("upspeed", 0),
                "eta": t.get("eta", 0),
                "category": t.get("category", ""),
                "added_on": t.get("added_on", 0),
                "num_seeds": t.get("num_seeds", 0),
                "num_leechs": t.get("num_leechs", 0),
            })
        return sorted(result, key=lambda x: x["added_on"], reverse=True)
