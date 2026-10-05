# Airflow plus the three packages tracker.py needs, installed next to Airflow (pinned to its
# version so pip never changes it). The repo itself is mounted at /opt/project.
FROM apache/airflow:3.3.2-python3.10

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir "apache-airflow==3.3.2" -r /tmp/requirements.txt
