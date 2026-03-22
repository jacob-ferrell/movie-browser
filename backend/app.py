from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import tmdb
import qbt
import db

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

db.migrate()


def error(msg, status=500):
    return jsonify({"error": msg}), status


@app.get("/api/trending")
def trending():
    media_type = request.args.get("type", "all")
    window = request.args.get("window", "week")
    page = int(request.args.get("page", 1))
    if media_type not in ("all", "movie", "tv"):
        return error("type must be all, movie, or tv", 400)
    if window not in ("day", "week"):
        return error("window must be day or week", 400)
    try:
        return jsonify(tmdb.get_trending(media_type, window, page))
    except Exception as e:
        return error(str(e))


@app.get("/api/popular")
def popular():
    media_type = request.args.get("type", "movie")
    page = int(request.args.get("page", 1))
    if media_type not in ("movie", "tv"):
        return error("type must be movie or tv", 400)
    try:
        return jsonify(tmdb.get_popular(media_type, page))
    except Exception as e:
        return error(str(e))


@app.get("/api/search")
def search():
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    if not query:
        return error("q parameter is required", 400)
    try:
        return jsonify(tmdb.search(query, page))
    except Exception as e:
        return error(str(e))


@app.get("/api/discover")
def discover():
    media_type = request.args.get("type", "movie")
    genre_id = request.args.get("genre", "").strip()
    page = int(request.args.get("page", 1))
    if media_type not in ("movie", "tv", "all"):
        return error("type must be movie, tv, or all", 400)
    if not genre_id:
        return error("genre is required", 400)
    try:
        if media_type == "all":
            movie_data = tmdb.discover("movie", genre_id, page)
            tv_data = tmdb.discover("tv", genre_id, page)
            combined = movie_data["results"] + tv_data["results"]
            combined.sort(key=lambda x: x.get("vote_count", 0), reverse=True)
            return jsonify({
                "results": combined,
                "page": page,
                "total_pages": max(movie_data["total_pages"], tv_data["total_pages"]),
            })
        return jsonify(tmdb.discover(media_type, genre_id, page))
    except Exception as e:
        return error(str(e))


@app.get("/api/providers")
def providers():
    media_type = request.args.get("type")
    tmdb_id = request.args.get("id")
    region = request.args.get("region", "US").upper()
    if media_type not in ("movie", "tv"):
        return error("type must be movie or tv", 400)
    if not tmdb_id:
        return error("id is required", 400)
    try:
        return jsonify(tmdb.get_watch_providers(media_type, tmdb_id, region))
    except Exception as e:
        return error(str(e))


@app.post("/api/qbt/add")
def qbt_add():
    body = request.get_json(silent=True) or {}
    magnet = (body.get("magnet") or "").strip()
    if not magnet.startswith("magnet:"):
        return error("magnet must be a valid magnet link", 400)
    try:
        qbt.add_magnet(
            magnet,
            save_path=body.get("savepath"),
            category=body.get("category"),
        )
        return jsonify({"ok": True})
    except Exception as e:
        return error(str(e))


@app.get("/api/qbt/folders")
def qbt_folders():
    base = request.args.get("base", "tv")
    path = "/hdd/tvshows" if base == "tv" else "/hdd/Movies"
    try:
        return jsonify(qbt.list_save_folders(path))
    except Exception as e:
        return error(str(e))


@app.get("/api/qbt/torrents")
def qbt_torrents():
    try:
        return jsonify(qbt.list_torrents())
    except Exception as e:
        return error(str(e))


@app.get("/api/items")
def list_items():
    flag = request.args.get("flag")
    if flag not in ("watched", "not_interested", "downloaded"):
        return error("flag must be watched, not_interested, or downloaded", 400)
    try:
        return jsonify(db.get_items_by_flag(flag))
    except Exception as e:
        return error(str(e))


@app.post("/api/items/mark")
def items_mark():
    body = request.get_json(silent=True) or {}
    tmdb_id = body.get("tmdb_id")
    media_type = body.get("media_type")
    flag = body.get("flag")
    value = bool(body.get("value", True))

    if not tmdb_id or media_type not in ("movie", "tv"):
        return error("tmdb_id and media_type are required", 400)
    if flag not in ("watched", "not_interested", "downloaded"):
        return error("flag must be watched, not_interested, or downloaded", 400)

    try:
        # Upsert the item first so the row exists
        db.upsert_item(
            tmdb_id,
            media_type,
            body.get("title", ""),
            body.get("poster_url"),
        )
        row = db.set_flag(tmdb_id, media_type, flag, value)
        return jsonify(row)
    except Exception as e:
        return error(str(e))


@app.post("/api/items/states")
def items_states():
    """Batch-fetch tracking states for a list of items."""
    body = request.get_json(silent=True) or {}
    items = body.get("items", [])  # list of {tmdb_id, media_type}
    try:
        pairs = [(int(i["tmdb_id"]), i["media_type"]) for i in items if "tmdb_id" in i]
        return jsonify(db.get_all_states(pairs))
    except Exception as e:
        import traceback; traceback.print_exc()
        return error(str(e))


@app.post("/api/downloads")
def add_download():
    body = request.get_json(silent=True) or {}
    tmdb_id = body.get("tmdb_id")
    media_type = body.get("media_type")
    title = body.get("title", "")
    save_path = body.get("save_path", "")
    if not tmdb_id or media_type not in ("movie", "tv"):
        return error("tmdb_id and media_type are required", 400)
    if not save_path:
        return error("save_path is required", 400)
    try:
        db.upsert_item(tmdb_id, media_type, title, body.get("poster_url"))
        db.set_flag(tmdb_id, media_type, "downloaded", True)
        row_id = db.add_download(
            tmdb_id, media_type, title, body.get("poster_url"), save_path,
            torrent_name=body.get("torrent_name"),
            torrent_hash=body.get("torrent_hash"),
            season_number=body.get("season_number"),
            episode_number=body.get("episode_number"),
            episode_name=body.get("episode_name"),
        )
        return jsonify({"id": row_id})
    except Exception as e:
        return error(str(e))


@app.get("/api/tv/<int:tmdb_id>/show-folder")
def tv_show_folder(tmdb_id):
    try:
        return jsonify({"folder": db.get_show_folder(tmdb_id)})
    except Exception as e:
        return error(str(e))


@app.get("/api/tv/<int:tmdb_id>/seasons")
def tv_seasons(tmdb_id):
    try:
        return jsonify(tmdb.get_tv_seasons(tmdb_id))
    except Exception as e:
        return error(str(e))


@app.get("/api/tv/<int:tmdb_id>/season/<int:season_number>")
def tv_episodes(tmdb_id, season_number):
    try:
        return jsonify(tmdb.get_tv_episodes(tmdb_id, season_number))
    except Exception as e:
        return error(str(e))


@app.get("/api/torrent/search")
def torrent_search():
    import requests as req
    query = request.args.get("q", "").strip()
    if not query:
        return error("q parameter is required", 400)
    try:
        resp = req.get(
            "http://192.168.1.18:8000/api/data/",
            params={"key": query},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return error(str(e))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
