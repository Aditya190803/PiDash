# Use the official Python 3.12 slim image as a parent image
FROM python:3.12-slim

# Set the working directory in the container to /app
WORKDIR /app

# Create the directory for file uploads
# This step is important to ensure the directory exists inside the container
RUN mkdir -p lsfile

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install curl for health check and Python packages
RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application's code into the container at /app
COPY . .

# Create a non-root user and ensure upload folder ownership
RUN groupadd -r appuser \
  && useradd -r -g appuser -d /app -s /sbin/nologin -c "App user" appuser \
  && chown -R appuser:appuser /app /app/lsfile

# Persist uploaded files even if the container is removed/recreated.
# This mounts the lsfile directory as a volume.
VOLUME /app/lsfile

# Run as non-root user
USER appuser

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Copy .env file if it exists
COPY .env.example .env

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Define the command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--timeout", "120", "app:app"]

