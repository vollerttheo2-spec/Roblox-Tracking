"""Réglages de Roblox Radar. Tout ce que tu peux vouloir changer est ici."""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = pathlib.Path(os.environ.get("RADAR_DATA_DIR", ROOT / "data"))
DOCS_DIR = pathlib.Path(os.environ.get("RADAR_DOCS_DIR", ROOT / "docs"))
SNAP_DIR = DATA_DIR / "snapshots"
GAMES_FILE = DATA_DIR / "games.json"

# ---------- Collecte ----------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
PAGES_PER_SORT = 6          # nb de pages lues par liste Roblox (≈ 25-60 jeux/page)
MAX_TRACKED = 8000          # nb max de jeux suivis
KEEP_DAYS_NO_DISCOVERY = 21  # on arrête de suivre un jeu absent des listes depuis N jours...
KEEP_IF_PLAYING_AT_LEAST = 20  # ...sauf s'il a encore au moins ce nb de joueurs
REQUEST_PAUSE = 0.35        # pause (s) entre deux requêtes, pour rester poli

# Recherches par mot-clé pour élargir la découverte (best effort).
SEARCH_KEYWORDS = [
    "simulator", "tycoon", "tower defense", "obby", "clicker", "idle",
    "incremental", "farm", "fruit", "anime", "survival", "horror", "rpg",
    "pet", "egg hatch", "fishing", "brainrot", "garden", "merge", "cooking",
    "driving", "fighting", "roleplay", "story", "escape", "defense",
]

# ---------- Analyse ----------
HISTORY_DAYS = 30           # nb de snapshots relus pour les tendances
TOP_N = 300                 # nb de lignes gardées par onglet

GEM_MIN_VOTES = 150
GEM_MIN_LIKE = 0.80          # borne basse de Wilson minimum
GEM_CCU_RANGE = (30, 3000)   # "caché" = pas déjà énorme

NEW_MAX_AGE_DAYS = 60
NEW_MIN_CCU = 50
NEW_MIN_LIKE = 0.70

RISING_MIN_CCU = 80
RISING_MIN_BASE_CCU = 5
RISING_WINDOW_DAYS = 7

# Tags de concepts détectés dans le nom du jeu (regex, insensible à la casse).
TAGS = {
    "Simulator": r"simulator|\bsim\b",
    "Tycoon": r"tycoon",
    "Tower Defense": r"tower defen[cs]e|\btd\b",
    "Obby / Parkour": r"obby|parkour|obstacle",
    "Clicker / Idle": r"clicker|\bidle\b|incremental|\bafk\b",
    "Anime": r"anime",
    "Horreur": r"horror|scary|nightmare|backrooms|\bdoors\b",
    "RPG": r"\brpg\b|dungeon|quest",
    "Survie": r"surviv|\b99 nights\b",
    "Combat / PvP": r"fight|battle|pvp|arena|war\b",
    "Brainrot": r"brain\s?rot|skibidi|italian",
    "Ferme / Fruits": r"fruit|farm|garden|plant|harvest",
    "Pets / Oeufs": r"\bpets?\b|\begg|hatch",
    "Pêche": r"fish",
    "Voiture / Course": r"\bcar\b|cars|drive|driving|racing|\brace\b|drift",
    "Roleplay / Social": r"role\s?play|\brp\b|hangout|life|town|city",
    "Merge / Puzzle": r"merge|puzzle|match",
    "Cuisine / Resto": r"cook|restaurant|bakery|burger|pizza|cafe",
    "Escape / Story": r"escape|story|mystery|detective",
}
