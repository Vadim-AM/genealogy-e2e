# Browser e2e suite image: Python 3.12 + Playwright Chromium + pytest deps.
#
# Built once, reused for every CI run. Backend lives in a separate image
# (built from genealogy/Dockerfile with GENEALOGY_TESTING=1) and is wired
# in via docker-compose so this image stays generic.

FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /e2e

# Install Python deps first to keep layer caching effective.
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    playwright install --with-deps chromium

# Copy framework + test sources. Order: least-changing first.
COPY conftest.py pyproject.toml ./
COPY config/ ./config/
COPY framework/ ./framework/
COPY assertions/ ./assertions/
COPY api/ ./api/
COPY models/ ./models/
COPY src/ ./src/
COPY pages/ ./pages/
COPY fixtures/ ./fixtures/
COPY helpers/ ./helpers/
COPY test_data/ ./test_data/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Default: run the full suite (two passes).
# Compose can override with `command:` for partial runs.
CMD ["sh", "-c", "pytest tests/ -m 'not serial' -n 4 --dist load -v --tb=short && pytest tests/ -m serial -p no:xdist -v --tb=short"]
