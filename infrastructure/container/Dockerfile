FROM continuumio/miniconda3:24.1.2-0 AS builder

COPY infrastructure/env/occupancy_env.yml /tmp/occupancy_env.yml
RUN conda env create -f /tmp/occupancy_env.yml \
    && conda clean -afy \
    && rm /tmp/occupancy_env.yml

FROM continuumio/miniconda3:24.1.2-0

LABEL org.opencontainers.image.source="https://github.com/UU-BUEM/occupancy"
LABEL org.opencontainers.image.description="Occupancy module for UU-BUEM"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/conda/envs/occupancy_env /opt/conda/envs/occupancy_env

ENV PATH=/opt/conda/envs/occupancy_env/bin:$PATH
ENV CONDA_DEFAULT_ENV=occupancy_env
ENV PYTHONPATH=/app/src

WORKDIR /app
CMD ["python", "-m", "occupancy", "--help"]
