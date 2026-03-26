import os
import psycopg2
import psycopg2.extras


def _conn():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432").strip()),
        dbname=os.environ.get("PG_DB", "movie-browser"),
        user=os.environ.get("PG_USER", "postgres"),
        password=os.environ.get("PG_PASSWORD", ""),
        connect_timeout=5,
    )


def migrate():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracked_items (
                id           SERIAL PRIMARY KEY,
                tmdb_id      INTEGER     NOT NULL,
                media_type   VARCHAR(10) NOT NULL,
                title        TEXT        NOT NULL,
                poster_url   TEXT,
                watched      BOOLEAN     NOT NULL DEFAULT FALSE,
                not_interested BOOLEAN   NOT NULL DEFAULT FALSE,
                downloaded   BOOLEAN     NOT NULL DEFAULT FALSE,
                watched_at   TIMESTAMP,
                downloaded_at TIMESTAMP,
                created_at   TIMESTAMP   NOT NULL DEFAULT NOW(),
                UNIQUE (tmdb_id, media_type)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id             SERIAL PRIMARY KEY,
                tmdb_id        INTEGER     NOT NULL,
                media_type     VARCHAR(10) NOT NULL,
                title          TEXT        NOT NULL,
                poster_url     TEXT,
                season_number  INTEGER,
                episode_number INTEGER,
                episode_name   TEXT,
                torrent_name   TEXT,
                torrent_hash   TEXT,
                save_path      TEXT        NOT NULL,
                added_at       TIMESTAMP   NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS downloads_tmdb_idx ON downloads(tmdb_id, media_type)")
        conn.commit()


def upsert_item(tmdb_id, media_type, title, poster_url):
    """Ensure a row exists; return it."""
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO tracked_items (tmdb_id, media_type, title, poster_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tmdb_id, media_type) DO UPDATE
                SET title = EXCLUDED.title,
                    poster_url = COALESCE(EXCLUDED.poster_url, tracked_items.poster_url)
            RETURNING *
        """, (tmdb_id, media_type, title, poster_url))
        conn.commit()
        return dict(cur.fetchone())


def set_flag(tmdb_id, media_type, flag, value):
    """Set watched / not_interested / downloaded. Returns updated row."""
    allowed = {"watched", "not_interested", "downloaded"}
    if flag not in allowed:
        raise ValueError(f"Unknown flag: {flag}")

    ts_col = {"watched": "watched_at", "downloaded": "downloaded_at"}.get(flag)
    ts_expr = f", {ts_col} = {'NOW()' if value else 'NULL'}" if ts_col else ""

    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            UPDATE tracked_items
            SET {flag} = %s{ts_expr}
            WHERE tmdb_id = %s AND media_type = %s
            RETURNING *
        """, (value, tmdb_id, media_type))
        conn.commit()
        row = cur.fetchone()
        return dict(row) if row else None


def add_download(tmdb_id, media_type, title, poster_url, save_path,
                 torrent_name=None, torrent_hash=None,
                 season_number=None, episode_number=None, episode_name=None):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO downloads
              (tmdb_id, media_type, title, poster_url, save_path,
               torrent_name, torrent_hash, season_number, episode_number, episode_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (tmdb_id, media_type, title, poster_url, save_path,
              torrent_name, torrent_hash, season_number, episode_number, episode_name))
        conn.commit()
        return cur.fetchone()[0]


def mark_watched_by_hashes(hashes):
    """Look up items by torrent hash in downloads and mark them as watched.
    Returns the number of distinct items marked."""
    if not hashes:
        return 0
    placeholders = ','.join(['%s'] * len(hashes))
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT tmdb_id, media_type, title, poster_url
            FROM downloads
            WHERE torrent_hash IN ({placeholders})
        """, hashes)
        items = cur.fetchall()

    count = 0
    for tmdb_id, media_type, title, poster_url in items:
        upsert_item(tmdb_id, media_type, title, poster_url)
        set_flag(tmdb_id, media_type, 'watched', True)
        count += 1
    return count


def get_show_folder(tmdb_id):
    """Return the show-level folder name for a TV show from the most recent download."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT save_path FROM downloads
            WHERE tmdb_id = %s AND media_type = 'tv'
            ORDER BY added_at DESC LIMIT 1
        """, (tmdb_id,))
        row = cur.fetchone()
        if not row:
            return None
        # save_path = /hdd/tvshows/Show.Name/Show.S04E02
        # parent    = /hdd/tvshows/Show.Name  →  basename = Show.Name
        path = row[0].rstrip('/')
        parent = os.path.dirname(path)
        if '/tvshows/' in parent:
            return os.path.basename(parent)
        return None


def get_items_by_flag(flag):
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT tmdb_id AS id, media_type, title, poster_url,
                   watched, not_interested, downloaded
            FROM tracked_items
            WHERE {flag} = TRUE
            ORDER BY created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def get_hashes_by_paths(paths):
    """Return {save_path: torrent_hash} for the given save_paths.
    Normalizes trailing slashes so /hdd/Movies/Foo and /hdd/Movies/Foo/ both match."""
    if not paths:
        return {}
    normalized = [p.rstrip('/') for p in paths]
    placeholders = ','.join(['%s'] * len(normalized))
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT ON (rtrim(save_path, '/'))
                rtrim(save_path, '/') AS save_path,
                torrent_hash
            FROM downloads
            WHERE rtrim(save_path, '/') IN ({placeholders})
              AND torrent_hash IS NOT NULL
            ORDER BY rtrim(save_path, '/'), added_at DESC
        """, normalized)
        return {row[0]: row[1] for row in cur.fetchall()}


def get_item(tmdb_id, media_type):
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM tracked_items WHERE tmdb_id = %s AND media_type = %s",
            (tmdb_id, media_type)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_states(tmdb_ids_by_type):
    """
    Fetch tracking state for a batch of items.
    tmdb_ids_by_type: list of (tmdb_id, media_type) tuples
    Returns: dict keyed by "{tmdb_id}:{media_type}" → {watched, not_interested, downloaded}
    """
    if not tmdb_ids_by_type:
        return {}
    # Build: WHERE (tmdb_id, media_type) IN ((%s,%s), (%s,%s), ...)
    placeholders = ','.join(['(%s,%s)'] * len(tmdb_ids_by_type))
    params = [x for pair in tmdb_ids_by_type for x in (int(pair[0]), str(pair[1]))]
    with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT tmdb_id, media_type, watched, not_interested, downloaded
            FROM tracked_items
            WHERE (tmdb_id, media_type) IN ({placeholders})
        """, params)
        result = {}
        for row in cur.fetchall():
            key = f"{row['tmdb_id']}:{row['media_type']}"
            result[key] = {
                "watched": row["watched"],
                "not_interested": row["not_interested"],
                "downloaded": row["downloaded"],
            }
        return result
