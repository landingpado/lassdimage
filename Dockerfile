# Use an official Python runtime as a parent image  
FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y libheif-dev gcc

# Update pip
RUN pip install --upgrade pip

# Add the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the app when the container launches
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 main:app
