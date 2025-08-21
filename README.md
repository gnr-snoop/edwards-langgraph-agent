# Snoop Edwards

Snoop Edwards is a modular, multi-agent assistant that blends Python backend services, Discord integration, and a Streamlit web interface. The project is organized for easy local development and production deployment using Docker Compose.

## Features

- Modular Python backend (`app/`)
- Discord bot integration (`discord/`)
- Streamlit web interface (`streamlit/`)
- Environment-based configuration
- Containerized development and deployment

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

### Quick Start with Docker Compose

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd snoop-edwards
   ```

2. **Configure environment variables:**
   - Copy `.env.sample` to `.env` and adjust settings as needed:
     ```sh
     cp .env.sample .env
     ```

3. **Start all services:**
   ```sh
   docker-compose up --build
   ```

4. **Access the application:**
   - Streamlit UI: [http://localhost:8501](http://localhost:8501)
   - Discord bot: configure your Discord credentials in the `.env` file.

### Stopping Services

```sh
docker-compose down
```

## Directory Structure

- `app/` - Core backend logic, configurations, and utilities
- `discord/` - Discord bot implementation and helpers
- `streamlit/` - Streamlit web application and static assets
- `.devcontainer/` - VS Code development container configuration
- `.vscode/` - Editor settings and launch configurations

## Configuration Files

- `.env` / `.env.sample` – Environment variables for all services
- `docker-compose.yaml` – Multi-service orchestration (recommended for most users)
- `Dockerfile` – Base image for backend services
- `.devcontainer/devcontainer.json` – Development container config for VS Code
- `.vscode/launch.json` – Debugging configuration for VS Code
- `pyproject.toml` & `poetry.lock` – Python dependencies and project metadata

## Development

To run services individually or for advanced configuration, refer to each service’s subdirectory and the relevant configuration files.


## Running Locally

To run this project locally, follow these steps:

1. **Install Poetry**: If you haven't already, install Poetry by following the instructions on the [Poetry Installation](https://python-poetry.org/docs/#installation) page.

2. **Clone the Repository**: Clone the project repository to your local machine:
    ```sh
    git clone https://github.com/snoop-especialidades/snoop-edwards.git
    cd snoop-edwards
    ```

3. **Install Dependencies**: Use Poetry to install the project dependencies:
    ```sh
    poetry install
    ```

4. **Run the Apps**: Run backend and discord bot
    ```sh
    cd app
    poetry run python main.py

    cd discord
    poetry run python bot_discord.py
    ```
