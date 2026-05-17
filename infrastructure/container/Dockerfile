FROM anaconda/miniconda3:latest AS builder

COPY infrastructure/env/occupancy_env.yml /tmp/occupancy_env.yml
RUN conda env create -f /tmp/occupancy_env.yml \
    && conda clean -afy \
    && rm /tmp/occupancy_env.yml

FROM anaconda/miniconda3:latest

COPY --from=builder /opt/conda/envs/occupancy_env /opt/conda/envs/occupancy_env

ENV PATH=/opt/conda/envs/occupancy_env/bin:$PATH
ENV CONDA_DEFAULT_ENV=occupancy_env
ENV PYTHONPATH=/app/src

WORKDIR /app
COPY src/ /app/src/
COPY configs/ /app/configs/
CMD ["python", "-m", "occupancy", "--help"]
