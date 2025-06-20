# Use a lightweight Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/Temperature_data /app/Door_status_data

# Install Supervisor and system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    git \
    gcc \
    libffi-dev \
    libssl-dev \
    libatlas-base-dev \
    libglib2.0-0 \
    libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app

# Copy Supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose Dash app port
EXPOSE 8050
EXPOSE 8051
EXPOSE 8052

# Start Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
