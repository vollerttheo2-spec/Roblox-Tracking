"""Collecte quotidienne : découvre des jeux Roblox, relève leurs stats, écrit un snapshot.

Usage : python src/collect.py
"""
import csv
import datetime as dt
import gzip
import json
import random
import sys
import time
import uuid

import requests

import config as C

EXPLORE = "https://apis.roblox.com/explore-api/v1"
SEARCH = "https://apis.roblox.com/search-api/omni-search"
GAMES_API = "https://games.roblox.com/v1"

session = requests.Session()
session.headers.update({"User-Agent": C.USER_AGENT, "Accept": "application/json"})
SESSION_ID = str(uuid.uuid4())


def log(*a):
    print(*a, flush=True)


def get(url, params=None, tries=6):
    """GET JSON avec retry/backoff (429 et 5xx). Renvoie None si échec."""
    for i in range(tries):
        try:
            r = session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            log(f"  ! réseau ({e.__class__.__name__}), retry {i + 1}/{tries}")
            time.sleep(2 ** i + random.random())
            continue
        if r.status_code == 200:
            time.sleep(C.REQUEST_PAUSE)
            try:
                return r.json()
            except ValueError:
                return None
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** i * 2 + random.random()
            log(f"  ! HTTP {r.status_code} sur {url.split('/')[-1]}, pause {wait:.0f}s")
            time.sleep(wait)
            continue
        log(f"  ! HTTP {r.status_code} sur {url} (abandon)")
        return None
    return None


# ---------------------------------------------------------------- découverte
def discover_from_sorts():
    """Parcourt toutes les listes de l'écran Découvrir (Top, Up-and-coming, ...)."""
    found = {}  # universeId -> {"name":..., "sorts": set()}
    data = get(f"{EXPLORE}/get-sorts", {"sessionId": SESSION_ID, "device": "computer", "country": "all"})
    sorts = (data or {}).get("sorts", [])
    sorts = [s for s in sorts if s.get("sortId") and s.get("contentType", "Games") == "Games"]
    log(f"Listes Roblox trouvées : {len(sorts)}")
    for s in sorts:
        sid = s["sortId"]
        label = s.get("sortDisplayName") or sid
        cursor, n = None, 0
        for _ in range(C.PAGES_PER_SORT):
            params = {"sessionId": SESSION_ID, "device": "computer", "country": "all", "sortId": sid}
            if cursor:
                params["cursor"] = cursor
            d = get(f"{EXPLORE}/get-sort-content", params)
            if not d:
                break
            for g in d.get("games", []):
                uid = g.get("universeId")
                if uid:
                    found.setdefault(int(uid), set()).add(label)
                    n += 1
            cursor = d.get("nextPageCursor")
            if not cursor:
                break
        log(f"  - {label}: {n} jeux")
    return found


def discover_from_search():
    """Recherche par mots-clés (best effort : si l'endpoint change, on continue sans)."""
    found = {}
    fails = 0          # échecs consécutifs
    started = time.time()
    for kw in C.SEARCH_KEYWORDS:
        if fails >= 3:
            log("Recherche limitée par Roblox (429), on arrête là pour aujourd'hui.")
            break
        if time.time() - started > 360:
            log("Recherche : budget de 6 min atteint, on arrête.")
            break
        time.sleep(4)  # Roblox limite fortement l'endpoint de recherche
        d = get(SEARCH, {"searchQuery": kw, "sessionId": SESSION_ID, "pageType": "all"}, tries=2)
        if not d:
            fails += 1
            time.sleep(15)
            continue
        fails = 0
        n = 0
        for grp in d.get("searchResults", []):
            for c in grp.get("contents", []):
                uid = c.get("universeId")
                if uid and c.get("contentType", "Game") == "Game":
                    found.setdefault(int(uid), set()).add(f"search:{kw}")
                    n += 1
        log(f"  - recherche '{kw}': {n} jeux")
    return found


# ------------------------------------------------------------------- détails
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_details(ids):
    """Stats détaillées (joueurs, visites, favoris, date de création...) par lots de 100."""
    out = {}
    for batch in chunks(ids, 100):
        q = {"universeIds": ",".join(map(str, batch))}
        d = get(f"{GAMES_API}/games", q)
        for g in (d or {}).get("data", []):
            out[g["id"]] = g
    votes = {}
    for batch in chunks(ids, 100):
        q = {"universeIds": ",".join(map(str, batch))}
        d = get(f"{GAMES_API}/games/votes", q)
        for v in (d or {}).get("data", []):
            votes[v["id"]] = v
    return out, votes


# --------------------------------------------------------------------- main
def load_games():
    if C.GAMES_FILE.exists():
        return json.loads(C.GAMES_FILE.read_text(encoding="utf-8"))
    return {}


def main():
    C.SNAP_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    games = load_games()
    log(f"== Collecte du {today} | {len(games)} jeux déjà connus ==")

    discovered = discover_from_sorts()
    for uid, tags in discover_from_search().items():
        discovered.setdefault(uid, set()).update(tags)
    log(f"Jeux découverts aujourd'hui : {len(discovered)}")
    if not discovered and not games:
        log("ERREUR : aucun jeu découvert. Roblox bloque peut-être les requêtes.")
        sys.exit(1)

    # jeux à suivre = découverts + déjà connus encore pertinents
    tracked = set(discovered)
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=C.KEEP_DAYS_NO_DISCOVERY)).isoformat()
    for uid, meta in games.items():
        if int(uid) in tracked:
            continue
        if meta.get("last_discovered", "0") >= cutoff or meta.get("last_playing", 0) >= C.KEEP_IF_PLAYING_AT_LEAST:
            tracked.add(int(uid))
    ids = sorted(tracked)[: C.MAX_TRACKED * 2]
    log(f"Jeux à relever : {len(ids)}")

    details, votes = fetch_details(ids)
    if not details:
        log("ERREUR : l'API de détails n'a rien renvoyé.")
        sys.exit(1)

    rows = []
    for uid in ids:
        g = details.get(uid)
        if not g:
            continue
        v = votes.get(uid, {})
        playing = int(g.get("playing") or 0)
        meta = games.setdefault(str(uid), {"first_seen": today})
        meta.update({
            "name": g.get("name", "?"),
            "place": g.get("rootPlaceId"),
            "created": (g.get("created") or "")[:10],
            "updated": (g.get("updated") or "")[:10],
            "genre": g.get("genre_l1") or g.get("genre") or "",
            "creator": (g.get("creator") or {}).get("name", ""),
            "max_players": g.get("maxPlayers"),
            "last_playing": playing,
        })
        if uid in discovered:
            meta["last_discovered"] = today
            meta["sorts"] = sorted(discovered[uid])[:6]
        rows.append([
            uid, playing, int(g.get("visits") or 0), int(g.get("favoritedCount") or 0),
            int(v.get("upVotes") or 0), int(v.get("downVotes") or 0),
        ])

    # garde les MAX_TRACKED jeux les plus joués si on dépasse
    rows.sort(key=lambda r: r[1], reverse=True)
    rows = rows[: C.MAX_TRACKED]
    keep = {str(r[0]) for r in rows}
    games = {k: v for k, v in games.items() if k in keep}

    snap = C.SNAP_DIR / f"{today}.csv.gz"
    with gzip.open(snap, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["universe_id", "playing", "visits", "favorites", "up", "down"])
        w.writerows(rows)
    C.GAMES_FILE.write_text(json.dumps(games, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"OK : {len(rows)} jeux écrits dans {snap.name}")


if __name__ == "__main__":
    main()
