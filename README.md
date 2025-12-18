# Générateur de documents scolaires (Django + DRF + LaTeX)

Projet complet pour produire Bulletins et Tableaux d'honneur en PDF via XeLaTeX, avec API DRF, Celery, WebSockets de métriques et client web.

## Architecture rapide
- `config/` : settings, urls, ASGI/Wsgi, Celery.
- `documents/` : modèle `Document`, builder de contexte, renderer LaTeX, stockage, métriques, API, tâches Celery.
- `schools/` : modèles métier (`School`, `Class`, `Student`, `Subject`, `Grade`, `TermResult`, `FollowUp`).
- `templates_latex/` : sources LaTeX (`bulletin.tex`, `tableau_honneur.tex`, `filigrane.tex`).
- `assets/` : logo et filigrane (copiés automatiquement dans les runs LaTeX).
- `client_web/` : front HTML/JS de test (auth basic).
- `media/latex_logs/<doc_type>/` : logs/tex archivés par génération.
- `media/batches/` : archives ZIP pour les générations par lot.

## Prérequis
- Python 3.11+ recommandé
- XeLaTeX (TexLive) installé et dans le PATH (`XELATEX_BIN` sinon)
- Redis (broker Celery)

## Installation
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## Variables d’environnement utiles
- Django : `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- DB : `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Celery : `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_WORKER_CONCURRENCY`, `CELERY_WORKER_PREFETCH_MULTIPLIER`
- LaTeX : `XELATEX_BIN`, `LATEX_TMP_DIR`, `LATEX_DEFAULT_PASSES` (défaut 2)
- Logs LaTeX : `LATEX_LOG_DIR` (sinon fallback `media/latex_logs`)
- Thèmes : `BULLETIN_THEME_FILE`, `HONOR_THEME_FILE`
- Stockage : `DOCUMENT_STORAGE` (`local` par défaut, `s3`), `DOCUMENT_BASE_URL`, `DOCUMENT_STORAGE_PATH` (local), ou `AWS_*` si S3.

## Lancement (dev)
```bash
celery -A config worker -l info  # worker (queue "documents")
python manage.py runserver       # API/WS (ou python -m daphne config.asgi:application pour WS)
```

## API
### Async avec stockage (Document créé)
- `POST /api/documents/bulletin/` body `{"student_id":1,"term":"T1","force_new":false}`
- `POST /api/documents/honor-board/` même payload
- `GET /api/documents/{id}/download/` pour récupérer l’URL/chemin une fois READY

### Streaming éphémère (pas de stockage)
- `POST /api/documents/bulletin/stream/` body `{"student_id":1,"term":"T1"}`
- `POST /api/documents/honor-board/stream/` même payload  
Renvoie directement le PDF (`Content-Disposition: attachment`), aucun `Document` ni persistance.

### Batch (ZIP)
- `POST /api/batches/`  
  Payload :
  ```json
  {
    "items": [
      {"student_id":1, "term":"T1", "type":"BULLETIN"},
      {"student_id":2, "term":"T2", "type":"HONOR"}
    ]
  }
  ```
  Retourne `batch_id`, le lot est traité en tâche Celery.
- `GET /api/batches/{id}/` : statut (READY/PENDING/FAILED), compte des documents et chemin/URL du zip si prêt.
- `GET /api/batches/{id}/download/` : télécharge le zip quand il est prêt.

### Métriques
- WebSocket : `ws://<host>/ws/documents/metrics/`
- Reset : `POST /api/metrics/reset/`

## Assets (logo / filigrane)
- Place `assets/logo.png` et `assets/filigrane.pdf` (ou `filigrane.png/filigrame.*`).  
- `builder.py` copie `assets/` dans le répertoire temp LaTeX ; les thèmes par défaut pointent sur `assets/...`.
- Si `assets/filigrane.pdf` est absent, le builder tente de recompiler `templates_latex/filigrane.tex` automatiquement dans `assets/`.

## Thèmes
- Fichiers JSON : `config/themes/bulletin_theme.json`, `config/themes/honor_theme.json`
- Clés : `colors`, `logo.enabled/path/override_school_logo`, `watermark.enabled/path`, `school` (nom, ville, pays, etc.)
- Chemins relatifs à `BASE_DIR` ou absolus ; par défaut `assets/logo.png` et `assets/filigrane.pdf`.

## Templates LaTeX (aperçu)
- `bulletin.tex` : mise en page 1 page, matières principales/complementaires, rappels T1/T2/T3 (affichés uniquement si term = 3 et données présentes), date en français, logo et filigrane depuis assets.
- `tableau_honneur.tex` : carte luxe, filigrane vectoriel ou image depuis assets, couleur selon distinction.
- `filigrane.tex` : standalone, compile vers `assets/filigrane.pdf` (motif guilloché + image centrale).

## Logs LaTeX
- Archivés automatiquement dans `media/latex_logs/<doc_type>/` à chaque génération (inclut `.log`, `.compile.log`, `.tex`).
- Purge : `python manage.py purge_latex_logs --days 7` (ou `--max-files`).

## Client web de test
- Fichier : `client_web/index.html`
- Fonctions :
  - Choix Bulletin / Honor
  - Choix T1/T2/T3, student_id, force_new
  - Mode streaming (PDF direct, pas de stockage)
  - Suivi métriques en temps réel via WebSocket
  - Simulation de charge (100/1000/10000 requêtes)
- Auth : basic (user/pass).

## Mode “pas de stockage”
- Utilise les endpoints `/stream/` (cf. ci-dessus).  
- La tâche ne crée pas de `Document` ni de fichier persistant ; réponse HTTP = PDF.
- Les tmpdir LaTeX sont nettoyés automatiquement après compilation.

## Notes sur la persistance des lots
- Les PDFs individuels restent stockés selon `DOCUMENT_STORAGE` (local ou S3).
- Les ZIPs sont écrits dans `media/batches/` (chemin paramétrable via `MEDIA_ROOT`).
- Si vous ne voulez conserver aucun PDF côté serveur, utilisez les endpoints `/stream/` pour des téléchargements éphémères (pas de lot).

## Commandes utiles
```bash
# Migration / superuser
python manage.py migrate
python manage.py createsuperuser

# Seed/demo (si fourni)
python manage.py seed_demo      # crée école, classe, élèves, notes, termresults
python manage.py fill_students_data  # remplit les élèves existants (notes, termresults)

# Worker
celery -A config worker -l info  # concurrence via env CELERY_WORKER_CONCURRENCY

# Serveur API
python manage.py runserver
# ou ASGI/WebSocket
python -m daphne config.asgi:application

# Purge logs LaTeX
python manage.py purge_latex_logs --days 7
```

## Sécurité / robustesse
- Pas d’exécution LaTeX arbitraire : simple remplacement de tokens.
- Compilation en répertoire temporaire isolé, timeout 60s, 2 passes XeLaTeX par défaut.
- Retries Celery avec backoff.  
- Auth DRF requise sur toutes les routes.  
- Option “pas de stockage” pour éviter la conservation des PDFs côté serveur.
