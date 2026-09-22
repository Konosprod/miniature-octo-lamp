app_dir := "src/animereco"

# List available recipes
default:
    just --list

# Start the postgres+pgvector container (idempotent, survives reboots)
db-up:
    podman compose up -d db

# Stop the postgres container (data is kept in the volume)
db-down:
    podman compose stop db

# Tail the postgres container logs
db-logs:
    podman compose logs -f db

# Open a psql shell in the running container
psql:
    podman compose exec db psql -U postgres -d anireco

# Apply pending Alembic migrations
migrate:
    cd {{app_dir}} && uv run alembic upgrade head

# Run the FastAPI app with auto-reload
run:
    cd {{app_dir}} && uv run uvicorn main:app --reload

# Download the AniList dataset (Kaggle) into src/animereco/data/anime.pkl
fetch-data:
    uv run python scripts/fetch_dataset.py

# Fetch/refresh embeddings for new anime and load them into the DB (calls Scaleway, costs money)
load:
    cd {{app_dir}} && uv run python main.py

# Merge AniList's `recommendations` field into already-loaded anime rows (local pickle only, no API calls)
backfill-recos:
    cd {{app_dir}} && uv run python backfill_recommendations.py

# Diff our recommendations for an anime against AniList's own community recommendations
diff-recos anime_id:
    cd {{app_dir}} && uv run python diff_recommendations.py {{anime_id}}

# Start the DB and apply migrations in one go
dev: db-up
    sleep 2
    just migrate

# Build the app's Docker image locally
docker-build:
    podman compose build app

# Run the full stack (db + app) from the built image, migrations run automatically
up:
    podman compose up -d --build

down:
    podman compose down
