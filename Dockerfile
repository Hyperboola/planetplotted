# Immagine della pipeline: Airflow + librerie + codice del progetto.
# In locale docker-compose monta la cartella sopra /opt/planetplotted;
# in produzione e nella CI si usa il codice copiato qui dentro.
FROM apache/airflow:2.10.5-python3.12

# ffmpeg serve a montare i fotogrammi in un video MP4 (reel)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
# Le versioni sono bloccate dai vincoli ufficiali di Airflow: stesse librerie
# in locale, nella CI e in produzione.
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"

WORKDIR /opt/planetplotted
COPY --chown=airflow:root . /opt/planetplotted
ENV PYTHONPATH=/opt/planetplotted
