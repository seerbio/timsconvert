# Use Python 3.11 as the base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy all files to the working directory
COPY . /app

# Install dependencies, including OpenGL, dbus, and other libraries for PySide6 and awscli
RUN apt-get update && \
    apt-get install -y \
    libgl1-mesa-glx \
    libegl1 \
    libxkbcommon0 \
    libdbus-1-3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install AWS CLI
RUN pip install --no-cache-dir awscli

# Set the entrypoint for the container
ENTRYPOINT ["python3", "/app/tims_seer.py"]
