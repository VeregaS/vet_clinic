FROM python:3.11-bookworm@sha256:726d304906fa5eb468e5531e366548d1903286352f5adb54ef508ac01fbd80c6
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# The base image includes Pango and DejaVu for Cyrillic PDF output.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
