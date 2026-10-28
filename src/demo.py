"""Génère de FAUSSES données pour tester l'analyse et prévisualiser le dashboard.

Usage :
    RADAR_DATA_DIR=demo_data RADAR_DOCS_DIR=demo_docs python src/demo.py
    RADAR_DATA_DIR=demo_data RADAR_DOCS_DIR=demo_docs python src/analyze.py
"""
import csv
import datetime as dt
import gzip
import json
import random

import config as C

random.seed(7)
WORDS_A = ["Fruit", "Pet", "Anime", "Tower", "Brainrot", "Garden", "Fishing", "Dungeon", "Cooking", "Car", "Mega", "Idle", "Ninja", "Space", "Zombie"]
WORDS_B = ["Simulator", "Tycoon", "Defense", "Clicker", "Obby", "Farm", "Battle", "Quest", "Rush", "Legends", "Hatch", "Survival", "Merge"]


def main():
    C.SNAP_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    games = {}
    state = {}
    for i in range(900):
        uid = 100000 + i
        age = random.choice([5, 10, 20, 35, 50, 80, 200, 600, 1500])
        pop = max(5, int(random.lognormvariate(4.2, 1.6)))
        trend = random.choice([0.0] * 6 + [0.05, 0.12, 0.3, -0.05, -0.1])
        games[str(uid)] = {
            "name": f"{random.choice(WORDS_A)} {random.choice(WORDS_B)} {random.choice(['', '2', 'X', '[UPDATE]'])}".strip(),
            "place": uid * 3, "created": (today - dt.timedelta(days=age)).isoformat(),
            "genre": random.choice(["Action", "Adventure", "Simulation", "RPG", "Strategy"]),
            "creator": f"Studio{random.randint(1, 300)}", "first_seen": today.isoformat(),
            "last_discovered": today.isoformat(), "last_playing": pop,
        }
        like = min(0.98, max(0.4, random.gauss(0.84, 0.1)))
        votes = int(pop * random.uniform(5, 60))
        state[uid] = dict(pop=pop, trend=trend, visits=pop * age * random.randint(40, 120), favs=int(pop * random.uniform(20, 300)), like=like, votes=votes)
    days = 10
    for d in range(days, -1, -1):
        date = today - dt.timedelta(days=d)
        rows = []
        for uid, s in state.items():
            s["pop"] = max(1, s["pop"] * (1 + s["trend"] + random.gauss(0, 0.04)))
            s["visits"] += int(s["pop"] * 90)
            up = int(s["votes"] * s["like"]); down = s["votes"] - up
            rows.append([uid, int(s["pop"]), s["visits"], s["favs"], up, down])
        with gzip.open(C.SNAP_DIR / f"{date.isoformat()}.csv.gz", "wt", newline="") as f:
            w = csv.writer(f); w.writerow(["universe_id", "playing", "visits", "favorites", "up", "down"]); w.writerows(rows)
    C.GAMES_FILE.write_text(json.dumps(games))
    print(f"Démo : {len(games)} jeux, {days + 1} jours dans {C.DATA_DIR}")


if __name__ == "__main__":
    main()
