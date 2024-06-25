# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .

# Copy the cleanup script into the container
COPY cleanup.sh /usr/local/bin/cleanup.sh

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
# Install cron
RUN apt-get update && apt-get install -y cron

# Give execution rights on the cleanup script
RUN chmod +x /usr/local/bin/cleanup.sh

# Create the cron job
RUN echo "*/10 * * * * /usr/local/bin/cleanup.sh" > /etc/cron.d/cleanup-cron

# Give execution rights on the cron job file
RUN chmod 0644 /etc/cron.d/cleanup-cron

COPY . .

# Apply the cron job
RUN crontab /etc/cron.d/cleanup-cron

# Expose the port (no specific port hardcoded)
EXPOSE ${PORT}

# Start cron and the application
CMD cron && uvicorn app.main:app --host 0.0.0.0 --port $PORT
