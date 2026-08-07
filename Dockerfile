# --------------------------------------------------------------------------
# Canopy v2.0 Converter — Docker Image
# --------------------------------------------------------------------------
# Converts pre-v2.0 ADAT files (array-normalized and/or NGS-normalized) into
# the v2.0 combined format.
#
# Build:
#   docker build -t canopy-v2-converter .
#
# Run:
#   docker run --rm -v /path/to/adats:/data canopy-v2-converter \
#       /data/input.adat -o /data/output_v2.adat
#
# --------------------------------------------------------------------------

FROM python:3.11-slim

LABEL maintainer="SomaLogic/Standard BioTools <support@somalogic.com>"
LABEL description="ADAT v2.0 converter (somadata)"

# Prevent .pyc files and enable unbuffered stdout/stderr for logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# --------------------------------------------------------------------------
# Copy source and install the package (dependencies resolved from pyproject.toml)
# --------------------------------------------------------------------------
COPY pyproject.toml README.md ./
COPY somadata/ ./somadata/
COPY bin/ ./bin/

RUN pip install --no-cache-dir .

# Default working directory for bind-mounted data
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["python", "/app/bin/somadata_convert_v2"]
