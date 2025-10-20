# Telegram Channel Management Bot

This is a production-ready, modular Telegram bot for managing submissions to a channel via a moderation group. It's built with Python 3.11 and the `aiogram` framework.

## Features

- **Role-Based Access Control**: Differentiates between an Owner, Admins, and regular Users.
- **Moderation Workflow**: Regular user submissions go to a report group for approval before being published.
- **Direct Publishing**: Admins and the owner can bypass moderation and post directly to the output channel.
- **Admin Management**: The owner can add or remove admins via simple commands.
- **Mandatory Membership**: Admins must be members of a specified channel to perform actions.
- **Configurable**: All chat IDs and settings are managed in a `config.yaml` file.
- **Secure**: Bot token is loaded from environment variables, not hardcoded.
- **Robust**: Implements concurrency-safe file writes with backups, error handling, and retry logic for posting.
- **Internationalization**: All user-facing strings are in Persian (Farsi) and managed in `fa.json`.
- **Dockerized**: Comes with `Dockerfile` and `docker-compose.yml` for easy deployment.

## Project Structure

```
telegram_management_bot/
├── app/                  # Main application source code
├── tests/                # Unit tests
├── .env.example          # Environment variable template
├── admins.json.example   # Example admin data file
├── config.yaml.example   # Example configuration file
├── fa.json               # Persian language strings
├── Dockerfile            # Container definition
├── docker-compose.yml    # Docker orchestration
├── pyproject.toml        # Dependencies (Poetry)
└── README.md
```

## Setup and Installation

### 1. Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- Docker and Docker Compose (for containerized deployment)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Getting Chat IDs

You need the numeric IDs for the owner, report group, output channel, and required membership channel.
1.  **Owner ID**: Send a message to `@userinfobot` on Telegram to get your numeric user ID.
2.  **Group/Channel IDs**:
    *   Add your bot to the target group and channel.
    *   Make the bot an **admin** in both.
    *   Forward a message from the channel/group to `@userinfobot`. It will show you the chat's numeric ID (it will be a negative number).

### 3. Bot Permissions

Your bot needs the following admin rights in the **Report Group** and **Output Channel**:
- **In Report Group**:
  - `Send Messages`: To post reports and logs.
  - `Delete Messages`: To clean up handled reports.
- **In Output Channel**:
  - `Post Messages`: To publish approved content.

### 4. Configuration

1.  **Environment Variables**:
    -   Copy `.env.example` to a new file named `.env`.
    -   Open `.env` and paste your bot token from BotFather.
    ```
    BOT_TOKEN="YOUR_REAL_BOT_TOKEN_HERE"
    ```

2.  **Configuration File**:
    -   Copy `config.yaml.example` to `config.yaml`.
    -   Edit `config.yaml` with the numeric IDs you collected.

3.  **Admins File**:
    -   Copy `admins.json.example` to `admins.json`.
    -   You can pre-populate this file with admin IDs and aliases, or add them later using the bot's commands.

### 5. Running the Bot

#### Locally (for development)

1.  **Install Dependencies**:
    ```bash
    poetry install
    ```
2.  **Run the Bot** (from the project root directory):
    ```bash
    poetry run python -m app.bot
    ```

#### Using Docker (recommended for production)

1.  Make sure your `.env`, `config.yaml`, and `admins.json` files are correctly configured.
2.  Build and run the container in detached mode:
    ```bash
    docker-compose up --build -d
    ```
3.  To view logs:
    ```bash
    docker-compose logs -f
    ```
4.  To stop the bot:
    ```bash
    docker-compose down
    ```

## Bot Commands

### For Regular Users
- `/start`: Shows a welcome message.
- `/submit`: Starts the submission process (asks for subject, then content).
- **Direct Message**: Users can also send content (text, photo, etc.) directly to the bot to start the submission process.

### For Admins & Owner
- `/post` (as a reply to a message): Directly posts the replied-to message to the output channel.

### For the Owner Only
- `/add_admin <user_id> <alias>`: Adds a new admin.
  - *Example*: `/add_admin 123456789 ali`
- `/remove_admin <user_id>`: Removes an admin.
  - *Example*: `/remove_admin 123456789`

## Security Considerations

- **Bot Token**: The `BOT_TOKEN` is treated as a secret and is loaded from an environment variable. It should never be committed to version control. The `.gitignore` file should include `.env`.
- **Permissions**: The bot only requires the minimum permissions necessary to function. Do not grant it global admin rights if not needed.
- **Callback Data**: The `callback_data` for inline buttons contains the submitter's ID. While this is not highly sensitive, it's designed to be processed server-side and is not easily forgeable by a user to affect other users' posts without access to the report group.
- **File System Access**: The bot writes to `admins.json` and a log file. Ensure the user running the bot process has the correct write permissions for these files. When using Docker, this is handled by volume mounts.