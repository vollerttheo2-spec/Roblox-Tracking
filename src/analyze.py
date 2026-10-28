"""Lit les snapshots, calcule les scores, génère docs/index.html.

Usage : python src/analyze.py
"""
import datetime as dt
import json
import re

import numpy as np
import pandas as pd

import config as C


def wilson_lower(up, down, z=1.96):
    """Borne basse de l'intervalle de Wilson : ratio de likes 'honnête' selon le nb de votes."""
    n = (up + down).astype(float)
    p = np.where(n > 0, up / np.where(n > 0, n, 1), 0)
    denom = 1 + z * z / np.where(n > 0, n, 1)
    centre = p + z * z / (2 * np.where(n > 0, n, 1))
    margin = z * np.sqrt((p * (1 - p) + z * z / (4 * np.where(n > 0, n, 1))) / np.where(n > 0, n, 1))
    return np.where(n > 0, (centre - margin) / denom, 0)


def pct(s):
    return s.rank(pct=True) if len(s) else s


def load_snapshots():
    files = sorted(C.SNAP_DIR.glob("*.csv.gz"))[-C.HISTORY_DAYS:]
    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["date"] = pd.to_datetime(f.name.split(".")[0])
        frames.append(df)
    if not frames:
        raise SystemExit("Aucun snapshot dans data/snapshots. Lance d'abord collect.py (ou demo.py).")
    return pd.concat(frames, ignore_index=True)


def tag_games(names):
    pats = {t: re.compile(p, re.I) for t, p in C.TAGS.items()}
    return [[t for t, p in pats.items() if p.search(n or "")] for n in names]


def build_table():
    hist = load_snapshots()
    games = json.loads(C.GAMES_FILE.read_text(encoding="utf-8"))
    latest_date = hist["date"].max()
    now = hist[hist["date"] == latest_date].copy()
    n_snaps = hist["date"].nunique()

    # ---- baseline : moyenne des snapshots précédents dans la fenêtre
    win_start = latest_date - pd.Timedelta(days=C.RISING_WINDOW_DAYS)
    prev = hist[(hist["date"] < latest_date) & (hist["date"] >= win_start)]
    if len(prev):
        g = prev.groupby("universe_id")
        base = pd.DataFrame({
            "base_ccu": g["playing"].mean(),
            "base_date": g["date"].min(),
        })
        first = prev.sort_values("date").groupby("universe_id").first()
        base["base_visits"] = first["visits"]
        base["base_favs"] = first["favorites"]
        now = now.merge(base, left_on="universe_id", right_index=True, how="left")
        span = (latest_date - now["base_date"]).dt.days.clip(lower=1)
        now["visits_day"] = (now["visits"] - now["base_visits"]) / span
        now["favs_day"] = (now["favorites"] - now["base_favs"]) / span
        now["growth"] = now["playing"] / now["base_ccu"].where(now["base_ccu"] > 0) - 1
    else:
        for c in ("base_ccu", "visits_day", "favs_day", "growth"):
            now[c] = np.nan

    # ---- métadonnées
    meta = pd.DataFrame.from_dict(games, orient="index")
    meta.index = meta.index.astype(int)
    now = now.merge(meta, left_on="universe_id", right_index=True, how="left")
    now["name"] = now["name"].fillna("?")
    created = pd.to_datetime(now["created"], errors="coerce")
    now["age_days"] = (latest_date - created).dt.days
    now["like_ratio"] = np.where((now["up"] + now["down"]) > 0, now["up"] / (now["up"] + now["down"]).replace(0, 1), np.nan)
    now["wilson"] = wilson_lower(now["up"], now["down"])
    now["votes"] = now["up"] + now["down"]
    now["fav_rate"] = now["favorites"] / now["visits"].replace(0, np.nan)
    now["visits_per_day_life"] = now["visits"] / now["age_days"].clip(lower=1)
    now["tags"] = tag_games(now["name"])
    return now, latest_date, n_snaps, len(games)


def lists_from(now):
    out = {}
    N = C.TOP_N

    # TOP : joueurs actifs
    out["top"] = now.sort_values("playing", ascending=False).head(N).assign(score=lambda d: d["playing"])

    # PÉPITES : bon taux de likes, bon taux de favoris, pas encore énorme
    g = now[
        (now["votes"] >= C.GEM_MIN_VOTES)
        & (now["wilson"] >= C.GEM_MIN_LIKE)
        & (now["playing"].between(*C.GEM_CCU_RANGE))
    ].copy()
    if len(g):
        g["score"] = 100 * (0.55 * pct(g["wilson"]) + 0.30 * pct(g["fav_rate"].fillna(0)) + 0.15 * (1 - pct(g["playing"])))
    out["gems"] = g.sort_values("score", ascending=False).head(N) if len(g) else g

    # NOUVEAUX À POTENTIEL
    n = now[
        (now["age_days"] <= C.NEW_MAX_AGE_DAYS)
        & (now["playing"] >= C.NEW_MIN_CCU)
        & (now["wilson"] >= C.NEW_MIN_LIKE)
    ].copy()
    if len(n):
        n["score"] = 100 * (0.45 * pct(n["visits_per_day_life"]) + 0.30 * pct(n["wilson"]) + 0.25 * pct(n["playing"]))
    out["new"] = n.sort_values("score", ascending=False).head(N) if len(n) else n

    # EN HAUSSE (demande >= 2 snapshots)
    r = now[
        (now["playing"] >= C.RISING_MIN_CCU)
        & (now["base_ccu"] >= C.RISING_MIN_BASE_CCU)
        & now["growth"].notna()
        & (now["growth"] > 0)
    ].copy()
    if len(r):
        r["score"] = r["growth"].clip(upper=20) * np.log10(r["playing"] + 10) * 100
    out["rising"] = r.sort_values("score", ascending=False).head(N) if len(r) else r
    return out


def niche_table(now):
    rows = []
    exploded = now.explode("tags")
    exploded = exploded[exploded["tags"].notna()]
    for tag, d in exploded.groupby("tags"):
        new = d[d["age_days"] <= C.NEW_MAX_AGE_DAYS]
        winners = new[new["playing"] >= 100]
        rows.append({
            "tag": tag,
            "games": int(len(d)),
            "total_ccu": int(d["playing"].sum()),
            "median_ccu": int(d["playing"].median()),
            "like": round(float(np.nanmean(d["like_ratio"])) * 100, 1) if d["like_ratio"].notna().any() else None,
            "new_games": int(len(new)),
            "new_winners": int(len(winners)),
            "win_rate": round(len(winners) / len(new) * 100, 1) if len(new) else None,
            "ccu_per_game": int(d["playing"].sum() / max(len(d), 1)),
        })
    return sorted(rows, key=lambda x: x["total_ccu"], reverse=True)


def clean(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return v


def rows_json(df):
    cols = ["universe_id", "name", "place", "genre", "creator", "playing", "visits", "favorites",
            "like_ratio", "votes", "age_days", "growth", "base_ccu", "visits_day", "favs_day", "score", "tags", "sorts"]
    res = []
    for _, r in df.iterrows():
        o = {}
        for c in cols:
            v = r.get(c)
            if isinstance(v, (list, tuple)):
                o[c] = list(v)
            else:
                o[c] = clean(v)
        res.append(o)
    return res


def main():
    now, latest, n_snaps, n_known = build_table()
    lists = lists_from(now)
    payload = {
        "date": latest.strftime("%Y-%m-%d"),
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "snapshots": int(n_snaps),
        "tracked": int(len(now)),
        "total_ccu": int(now["playing"].sum()),
        "lists": {k: rows_json(v) for k, v in lists.items()},
        "niches": niche_table(now),
        "genres": sorted({g for g in now["genre"].dropna().unique() if g}),
        "tag_names": list(C.TAGS.keys()),
    }
    C.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    tpl = (C.ROOT / "src" / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (C.DOCS_DIR / "index.html").write_text(tpl.replace("__DATA__", blob), encoding="utf-8")
    (C.DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    sizes = {k: len(v) for k, v in lists.items()}
    print(f"Dashboard généré : {latest.date()} | {len(now)} jeux | {n_snaps} snapshot(s) | listes {sizes}")


if __name__ == "__main__":
    main()
