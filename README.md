# Discord Rich Presence Manager

Application portable qui affiche automatiquement une Rich Presence
Discord différente selon l'application/le jeu lancé sur Windows,
sans tâche planifiée : elle tourne en arrière-plan avec une icône
dans la zone de notification (comme CustomRP), et se configure via
une interface graphique.

## Structure du dossier

```
DiscordRichPresenceManager/
├── app.pyw            <- à lancer (interface + icône système)
├── core.py             <- moteur de détection/RPC (ne pas lancer directement)
├── winstartup.py        <- gestion du démarrage automatique Windows
├── requirements.txt
├── config/
│   └── games.json      <- ta configuration (modifiable via l'UI ou à la main)
└── README.md
```

## Installation (une seule fois)

1. Installer Python 3.9+ depuis https://python.org (cocher "Add
   python.exe to PATH" pendant l'installation).
2. Ouvrir une invite de commande dans ce dossier et lancer :

   ```
   pip install -r requirements.txt
   ```

## Lancement

- Double-clique sur `app.pyw`. Windows associe l'extension `.pyw` à
  `pythonw.exe`, donc **aucune fenêtre de console ne s'affiche** :
  l'application se réduit directement dans la zone de notification
  (icône bleue en forme de visage souriant).
- Clic sur l'icône (ou double-clic) → ouvre la fenêtre de
  configuration.
- Clic droit sur l'icône → menu "Ouvrir" / "Quitter".

## Utilisation

- **Ajouter / Modifier / Supprimer** une présence via les boutons à
  droite de la liste.
- **Monter / Descendre** change la priorité : si plusieurs
  exécutables surveillés tournent en même temps, celui du haut de la
  liste l'emporte.
- Une présence peut être **désactivée** sans être supprimée (case à
  cocher dans la fenêtre d'édition).
- **Intervalle de vérification** : fréquence (en secondes) à laquelle
  l'app regarde les processus actifs.
- **Démarrer automatiquement avec Windows** : ajoute (ou retire) une
  entrée dans la clé de registre `Run` de ton utilisateur Windows,
  pointant vers `pythonw.exe app.pyw`. Ça remplace la tâche
  planifiée — aucun droit administrateur requis.
- N'oublie pas de cliquer sur **Enregistrer** après une modification
  pour écrire `config/games.json` et recharger la config à chaud
  (pas besoin de relancer l'application).

## Pour chaque application/jeu à ajouter

1. Va sur https://discord.com/developers/applications, crée une
   application, récupère son **Application ID** (= Client ID).
   C'est ce nom d'application Discord qui apparaît en gras sur ton
   profil Discord.
2. (Optionnel) Dans l'onglet "Rich Presence > Art Assets" de cette
   application Discord, uploade une image et donne-lui une **clé**
   (ex : `dokkan`) — c'est cette clé qu'il faut mettre dans le champ
   "Clé image (large_image)".
3. Dans l'application, clique sur **Ajouter**, renseigne :
   - Exécutable : le nom du process Windows (ex : `jeu.exe`, visible
     dans le Gestionnaire des tâches, onglet "Détails")
   - Client ID Discord : l'Application ID récupéré à l'étape 1
   - Ligne 1 / Ligne 2 : les deux lignes de texte affichées sous le
     nom de l'application sur Discord
   - Clé image / texte au survol : optionnels

## Portable / distribution

Tout le dossier `DiscordRichPresenceManager/` peut être zippé et copié
tel quel sur une autre machine Windows : il suffit d'installer
Python + `pip install -r requirements.txt` une fois là-bas, aucune
autre installation n'est nécessaire.
