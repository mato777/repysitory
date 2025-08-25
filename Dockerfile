FROM python:3.13-alpine

# Install bash, curl, and runtime libs (e.g., libpq for asyncpg)
RUN apk add --no-cache bash curl ca-certificates postgresql-libs

# Install build dependencies for packages with native extensions (removed later)
RUN apk add --no-cache --virtual .build-deps build-base libffi-dev openssl-dev postgresql-dev

RUN apk add --no-cache docker-cli

# Install uv via Astral's installer
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# Ensure uv is on PATH for all users and subsequent steps
ENV PATH="/root/.local/bin:${PATH}"

# Verify installation (also caches uv in the layer)
RUN uv --version

# Use bash for subsequent RUN commands and as default shell when entering the container
SHELL ["/bin/bash", "-lc"]

WORKDIR /app

# Make the project venv the default Python
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Copy project metadata first and install dependencies (cached layer)
COPY pyproject.toml uv.lock /app/
# Install all groups (dev included) and respect lockfile if present
RUN uv sync --frozen --all-groups || true

# Copy the rest of the project
COPY . /app

# Ensure Python can import the top-level `src` package from the repo root
ENV PYTHONPATH="/app"

# Remove build dependencies to reduce image size
RUN apk del .build-deps || true

# Default to an interactive bash session
CMD ["bash"]
