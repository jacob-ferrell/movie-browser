import os
import requests

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"


def _api_key():
    key = os.environ.get("TMDB_API_KEY")
    if not key:
        raise RuntimeError("TMDB_API_KEY not set")
    return key


def _get(path, params=None):
    params = params or {}
    params["api_key"] = _api_key()
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _normalize(item):
    media_type = item.get("media_type") or ("tv" if "name" in item else "movie")
    title = item.get("title") or item.get("name", "")
    release_date = item.get("release_date") or item.get("first_air_date", "")
    poster = item.get("poster_path")
    backdrop = item.get("backdrop_path")
    return {
        "id": item["id"],
        "media_type": media_type,
        "title": title,
        "poster_url": f"{IMAGE_BASE}{poster}" if poster else None,
        "backdrop_url": f"{BACKDROP_BASE}{backdrop}" if backdrop else None,
        "overview": item.get("overview", ""),
        "release_date": release_date,
        "vote_average": round(item.get("vote_average", 0), 1),
        "vote_count": item.get("vote_count", 0),
        "genre_ids": item.get("genre_ids", []),
    }


def get_trending(media_type="all", time_window="week", page=1):
    data = _get(f"/trending/{media_type}/{time_window}", {"page": page})
    return {
        "results": [_normalize(i) for i in data.get("results", [])],
        "page": data.get("page", 1),
        "total_pages": min(data.get("total_pages", 1), 500),
    }


def get_popular(media_type="movie", page=1):
    data = _get(f"/{media_type}/popular", {"page": page})
    results = []
    for item in data.get("results", []):
        item["media_type"] = media_type
        results.append(_normalize(item))
    return {
        "results": results,
        "page": data.get("page", 1),
        "total_pages": min(data.get("total_pages", 1), 500),
    }


def search(query, page=1):
    data = _get("/search/multi", {"query": query, "page": page, "include_adult": False})
    results = []
    for item in data.get("results", []):
        if item.get("media_type") in ("movie", "tv"):
            results.append(_normalize(item))
    return {
        "results": results,
        "page": data.get("page", 1),
        "total_pages": min(data.get("total_pages", 1), 500),
    }


def discover(media_type, genre_id, page=1):
    """media_type: 'movie' or 'tv'"""
    data = _get(f"/discover/{media_type}", {
        "with_genres": genre_id,
        "page": page,
        "sort_by": "popularity.desc",
    })
    results = []
    for item in data.get("results", []):
        item["media_type"] = media_type
        results.append(_normalize(item))
    return {
        "results": results,
        "page": data.get("page", 1),
        "total_pages": min(data.get("total_pages", 1), 500),
    }


def get_tv_seasons(tmdb_id):
    data = _get(f"/tv/{tmdb_id}")
    seasons = []
    for s in data.get("seasons", []):
        # Skip "Specials" (season 0) unless it has episodes
        if s["season_number"] == 0 and s.get("episode_count", 0) == 0:
            continue
        seasons.append({
            "season_number": s["season_number"],
            "name": s.get("name", f"Season {s['season_number']}"),
            "episode_count": s.get("episode_count", 0),
            "poster_url": f"{IMAGE_BASE}{s['poster_path']}" if s.get("poster_path") else None,
            "air_date": s.get("air_date", ""),
        })
    return seasons


def get_tv_episodes(tmdb_id, season_number):
    data = _get(f"/tv/{tmdb_id}/season/{season_number}")
    episodes = []
    for e in data.get("episodes", []):
        episodes.append({
            "episode_number": e["episode_number"],
            "name": e.get("name", f"Episode {e['episode_number']}"),
            "overview": e.get("overview", ""),
            "air_date": e.get("air_date", ""),
            "still_url": f"https://image.tmdb.org/t/p/w300{e['still_path']}" if e.get("still_path") else None,
            "runtime": e.get("runtime"),
        })
    return episodes


def get_watch_providers(media_type, tmdb_id, region="US"):
    data = _get(f"/{media_type}/{tmdb_id}/watch/providers")
    region_data = data.get("results", {}).get(region, {})

    def fmt_providers(providers):
        return [
            {
                "name": p["provider_name"],
                "logo_url": f"https://image.tmdb.org/t/p/original{p['logo_path']}"
                if p.get("logo_path")
                else None,
            }
            for p in providers
        ]

    return {
        "stream": fmt_providers(region_data.get("flatrate", [])),
        "rent": fmt_providers(region_data.get("rent", [])),
        "buy": fmt_providers(region_data.get("buy", [])),
        "link": region_data.get("link"),
    }
