# Roblox Radar

Collecte chaque jour les stats de milliers de jeux Roblox (GitHub Actions, gratuit), garde l'historique, et publie un dashboard avec :

- **Top performance** : jeux les plus joués
- **Pépites cachées** : très bien notés, beaucoup de favoris, pas encore énormes
- **Nouveaux à potentiel** : < 60 jours, déjà des joueurs, bons avis
- **En hausse** : joueurs actifs en forte progression vs les jours précédents
- **Concepts / niches** : quels types de jeux (simulator, tycoon, ferme, pets…) marchent, et où les nouveaux percent encore

## Mise en route (10 min)

1. Crée un repo **public** sur GitHub (ex. `roblox-radar`). Public = GitHub Pages gratuit. Ce sont des stats publiques Roblox, rien de sensible.
2. Mets-y tout le contenu de ce dossier, **y compris le dossier `.github`** (c'est lui qui contient le workflow).
   Le plus simple : `git init`, `git add .`, `git commit -m init`, `git remote add origin <url>`, `git push -u origin main`.
3. Onglet **Actions** → **Roblox Radar** → **Run workflow** pour le premier run. Ça prend quelques minutes.
4. Si le run est vert : onglet **Settings → Pages** → Source : *Deploy from a branch* → branche `main`, dossier `/docs` → Save.
5. Ton dashboard est sur `https://TON-PSEUDO.github.io/roblox-radar/`.

Ensuite tout tourne seul chaque jour (~18h UTC). Tu peux aussi relancer à la main quand tu veux.

Si le push du bot échoue (« permission denied ») : Settings → Actions → General → Workflow permissions → *Read and write permissions*.

## Ce qu'il faut savoir

- **« En hausse » est vide le 1er jour**, il faut au moins 2 snapshots. Les comparaisons deviennent fiables après ~1 semaine.
- **Les joueurs actifs varient selon l'heure.** Le snapshot est toujours pris à la même heure pour comparer ce qui est comparable, mais une seule mesure par jour reste bruitée.
- **Biais de survie** : on ne voit que les jeux que Roblox met en avant ou qui remontent dans les recherches. Les « parts de nouveaux qui réussissent » par niche sont gonflées. Compare les niches entre elles, n'y lis pas une probabilité de succès.
- **Un bon score ne veut pas dire « facile à copier ».** C'est un signal pour trouver des concepts à étudier, pas une décision.
- Le code utilise les API publiques non documentées de Roblox (explore-api, games). Elles peuvent changer. La partie « recherche par mots-clés » est la plus fragile : si elle casse, la collecte continue avec les listes Découvrir.

## Régler

Tout est dans `src/config.py` : mots-clés de recherche, seuils des pépites / nouveaux / hausse, tags de concepts (regex sur le nom du jeu), nombre de jeux suivis.

## Tester sans Roblox

```
RADAR_DATA_DIR=demo_data RADAR_DOCS_DIR=demo_docs python src/demo.py
RADAR_DATA_DIR=demo_data RADAR_DOCS_DIR=demo_docs python src/analyze.py
```
Puis ouvre `demo_docs/index.html` (données fictives).

## Structure

```
src/collect.py     découverte + relevé des stats -> data/snapshots/AAAA-MM-JJ.csv.gz
src/analyze.py     scores + génération du dashboard -> docs/index.html
src/template.html  page du dashboard
src/config.py      réglages
.github/workflows/radar.yml   exécution quotidienne
```
