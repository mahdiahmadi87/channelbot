# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

# Install poetry
RUN pip install poetry

# Copy only requirements to cache them in a layer
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev --no-root

# Copy the rest of the application
COPY ./app ./app

# Expose port (if using webhooks in the future)
# EXPOSE 8080

# Command to run the application
CMD ["poetry", "run", "python", "app/bot.py"]