# --- Stage 1: Base Python Image ---
FROM python:3.13-slim-bullseye

# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /sms_service

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements
COPY requirements.txt  .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Command to run your main file
CMD ["python", "main.py"]
