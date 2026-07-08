FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Update system packages to patch vulnerabilities
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Install only the Python dependencies we need
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt pytest

# Create a non-root user for security
RUN useradd -m agent
USER agent

# Keep the container alive in the background waiting for the AI's commands
CMD ["sleep", "infinity"]