# Immagine Airflow con le librerie della pipeline e del render.
FROM apache/airflow:2.10.5-python3.12

# ffmpeg serve a montare i fotogrammi in un video MP4
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"