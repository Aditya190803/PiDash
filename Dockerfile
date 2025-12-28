# Stage 1: Use the official Python 3.13 slim image as a parent image
FROM python:3.14-slim

# Set the working directory in the container to /app
WORKDIR /app

RUN mkdir -p lsfile

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Persist uploaded files even if the container is removed/recreated.
# This mounts the lsfile directory as a volume.
VOLUME /app/lsfile

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define the command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
