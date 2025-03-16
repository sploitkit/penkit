FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    masscan \
    curl \
    wget \
    git \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy project files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Create a non-root user to run the application
RUN groupadd -r penkit && useradd -r -g penkit penkit
RUN mkdir -p /home/penkit/.penkit && chown -R penkit:penkit /home/penkit

# Switch to non-root user for better security
USER penkit

# Set up environment
ENV PATH="/app:${PATH}"
ENV HOME=/home/penkit

# Set entry point
ENTRYPOINT ["python", "-m", "penkit.cli.main"]
CMD ["--help"]
