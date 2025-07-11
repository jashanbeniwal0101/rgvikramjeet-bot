# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional)
EXPOSE 8080

# Run your bot
CMD ["python", "main.py"]
