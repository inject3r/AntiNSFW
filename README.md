# AntiNSFW

A Telegram moderation bot that checks images, stickers, animations and video frames for likely NSFW content and applies the moderation action configured for each group.

The project talks directly to the Telegram Bot API. Group settings and moderation statistics are stored in MySQL, while the detector uses a Hugging Face image-classification model.

## What it does

- Detects NSFW content in photos and supported media.
- Handles static stickers, animations and video frames.
- Configures protection separately for each group.
- Supports delete, warn, mute, remove and ban actions.
- Supports warning limits and escalation.
- Lets administrators exempt users from moderation.
- Lets administrators block specific media.
- Stores detection results in database to avoid repeating work.
- Includes multilingual user and group messages.
- Provides owner-only statistics and broadcast tools.

## Requirements

- Python 3.11+
- MySQL 8.0+
- Enough disk space for the detection model and its dependencies

For video support, PyAV/FFmpeg support is installed through the `av` package. TGS support uses `rlottie-python`.

## Setup

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the MySQL database and user, or use the included Docker Compose setup.

Set at least:

```env
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_user_id

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=antinfsw
MYSQL_USER=antinfsw
MYSQL_PASSWORD=your_password
```

`antinfsw/config.py` is the central configuration layer. Runtime values come from `.env`; code-level defaults live there so they are easy to find and change.

## MySQL

The default schema is in `database/db.sql`.

If the database already exists, import it with:

```bash
mysql -u antinfsw -p antinfsw < database/db.sql
```

The application also creates the configured database when the MySQL server is reachable but the database itself does not exist.

## Run

```bash
python main.py
```

Or:

```bash
make run
```

## Docker

Set the values in `.env`, then:

```bash
docker compose up -d --build
```

MySQL data is kept in the `mysql_data` Docker volume.

## Telegram permissions

The bot needs administrator permissions in groups.

For deletion it needs permission to delete messages. Mute, remove and ban actions also require the corresponding member restriction permissions.

## Configuration

The main settings are controlled through `.env` and read by `antinfsw/config.py`.

Detection settings include:

- `MODEL_ID`
- `DEFAULT_THRESHOLD`
- `INFERENCE_BATCH_SIZE`
- `VIDEO_MAX_FRAMES`
- `GIF_MAX_FRAMES`
- `TGS_MAX_FRAMES`
- `MAX_VIDEO_DURATION_SECONDS`
- `FRAME_MAX_SIDE`
- `IMAGE_TTA`
- `FRAME_TOPK_PERCENT`
- `MAX_MEDIA_BYTES`
- `CACHE_MAX_ENTRIES`

Moderation defaults include:

- `DEFAULT_ACTION`
- `DEFAULT_WARN_LIMIT`
- `DEFAULT_MUTE_MINUTES`
- `DEFAULT_LANGUAGE`
- `MODERATE_ADMINS_DEFAULT`

Database settings are controlled with:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`