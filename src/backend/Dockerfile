# --- Stage 1: Base Python Image ---
FROM python:3.13-alpine AS base

# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /backend_app

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements
COPY requirements.txt  .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for healthcheck
RUN apk add --no-cache curl

# --- Stage 2: Development ---
FROM base AS development

# Copy the Django project to the container
COPY . .

# Expose the Django port
EXPOSE 8000

# Migrate database, Collect static files, Create superadmin, Run Django’s server
CMD ["sh", "/backend_app/entrypoint.dev.sh"]

# --- Stage 3: Production (Gunicorn + Nginx)  ---
FROM base AS production

# Copy the Django project to the container
COPY . .

# Expose the Django port
EXPOSE 8000

# Migrate database, Collect static files for admin panel and rest framework, Create superadmin, Run Django’s server using gunicorn and configure logging
CMD ["sh", "/backend_app/entrypoint.sh"]
