# Sampler (version web)

Version HTML du Sampler macOS : la même grille de touches, et chaque clip se lit dans la page, sous l'en-tête.

- Clic sur une touche : lance le clip (ou affiche l'image). Un second clic, un clic sur la vidéo ou Échap l'arrête.
- Le bouton en haut à droite passe la page en plein écran.
- `index.html` s'ouvre aussi directement depuis le disque, sans serveur.

## Mettre à jour les clips

Les clips sont générés à partir du dossier du Sampler natif (`../sampler` par défaut) :

```bash
python3 tools/import.py ../sampler
```

Le script réencode les vidéos pour le web (H.264 CRF 23, AAC 128k), crée les vignettes dans `thumbs/` et réécrit `deck.js`.
Les fichiers déjà convertis sont ignorés : supprime-les pour les régénérer.
