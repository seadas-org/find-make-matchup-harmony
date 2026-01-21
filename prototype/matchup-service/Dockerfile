FROM continuumio/miniconda3:24.9.2-0

WORKDIR /home

# Install/upgrade pip tooling in the base conda environment
RUN conda install --yes pip && pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies into base conda env
COPY environment.yml .
RUN conda env update --file environment.yml -n base && conda clean -afy

# Copy the app last so dependency layers cache well
COPY . .

ENTRYPOINT ["python", "-m", "harmony_service_example"]

