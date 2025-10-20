# Telegram Channel Management Bot

A production-ready Telegram bot for managing channel/group content with Persian (Farsi) UI. The bot provides moderation workflow, admin management, and direct posting capabilities.

## 📋 Features

- **Three-tier Permission System**: Owner, Admins, and Regular Users
- **Moderation Workflow**: Regular users' posts go through approval in a report group
- **Direct Admin Posting**: Admins can publish directly to the output channel
- **Mandatory Channel Membership**: Enforces channel membership for admin actions
- **Rate Limiting**: Prevents spam with configurable submission limits
- **Audit Logging**: Complete audit trail of all actions
- **Persian UI**: All user-facing text in Persian (Farsi)
- **Admin Management**: Owner can add/remove admins with aliases
- **Safe File Operations**: Atomic writes with backup rotation
- **Media Support**: Text, photos, videos, audio, voice messages, documents

## 🏗️ Architecture

```
┌─────────────┐
│ Regular User│
└──────┬──────┘
       │ /submit or direct message
       ↓
┌──────────────────┐
│ Bot (Rate Check) │
└──────┬───────────┘
       │
       ↓
┌─────────────────┐      ┌──────────────┐
│  Report Group   │◄─────┤ Admin/Owner  │
│  (Moderation)   │      │ (Approve/Del)│
└────────┬────────┘      └──────────────┘
         │ Approve
         ↓
  ┌──────────────┐
  │Output Channel│
  └──────────────┘

Admin Direct Post:
┌──────────┐
│Admin/Own │ /post → Output Channel
└──────────┘         + Audit Log
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Three Telegram entities:
  - A report group (for moderation)
  - An output channel (for approved posts)
  - A required membership channel

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd telegram-channel-bot
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure the bot**:
```bash
# Copy example configs
cp config/config.yaml.example config/config.yaml
cp config/admins.json.example config/admins.json
cp .env.example .env

# Edit config.yaml and .env with your values
nano config/config.yaml
nano .env
```

4. **Set up Telegram entities**:

   a. **Get your user ID**: Send a message to [@userinfobot](https://t.me/userinfobot)
   
   b. **Create/Get Group/Channel IDs**:
   - Add your bot to each group/channel
   - Use [@getidsbot](https://t.me/getidsbot) or forward a message to [@userinfobot](https://t.me/userinfobot)
   - IDs for groups/channels are negative numbers (e.g., -1001234567890)

5. **Promote the bot** (CRITICAL):

   For both the **Report Group** and **Output Channel**, promote the bot to admin with these permissions:
   
   - ✅ Delete messages
   - ✅ Post messages
   - ✅ Edit messages
   - ✅ Pin messages (optional)
   - ✅ Manage video chats (optional)

6. **Run the bot**:
```bash
python -m bot.main
```

### Using Docker

```bash
# Build and run with Docker Compose
cd docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## ⚙️ Configuration

### config/config.yaml

```yaml
bot_token: "YOUR_BOT_TOKEN"
owner_id: 123456789
report_group_id: -1001234567890
output_channel_id: -1001234567891
required_channel_id: -1001234567892
admins_file: "config/admins.json"
locales_file: "bot/locales/fa.json"
log_file: "logs/bot.log"
rate_limit_submissions: 5
rate_limit_window: 3600
webhook:
  enabled: false
  url: "https://your-domain.com"
  path: "/webhook"
  port: 8443
```

### Environment Variables (.env)

Environment variables override config.yaml values:

```bash
BOT_TOKEN=your_bot_token
OWNER_ID=123456789
REPORT_GROUP_ID=-1001234567890
OUTPUT_CHANNEL_ID=-1001234567891
REQUIRED_CHANNEL_ID=-1001234567892
```

### config/admins.json

```json
{
  "admins": [
    {"id": 123456789, "alias": "علی"},
    {"id": 987654321, "alias": "سارا"}
  ]
}
```

## 📱 Usage

### For Regular Users

1. **Submit content**:
   - Send `/submit` command, then follow prompts
   - OR directly send content to the bot

2. **Provide subject**: When prompted, enter the subject name (موضوع)

3. **Send content**: Send your text, photo, video, audio, or document

4. **Wait for approval**: Your content will be reviewed by admins

### For Admins

1. **Direct posting**:
   ```
   /post
   [Enter subject]
   [Send content]
   ```

2. **Review submissions** in the Report Group:
   - Click "✅ تایید" to approve and publish
   - Click "❌ حذف" to reject

3. **View admin list**:
   ```
   /list_admins
   ```

### For Owner

All admin commands plus:

1. **Add admin**:
   ```
   /add_admin 123456789 علی
   ```

2. **Remove admin**:
   ```
   /remove_admin 123456789
   ```

## 🔒 Security & Permissions

### Bot Permissions Required

The bot MUST be an administrator in:

1. **Report Group** with:
   - Send messages
   - Delete messages
   - Edit messages

2. **Output Channel** with:
   - Post messages
   - Edit messages

### Access Control

- **Owner**: Full control, can manage admins
- **Admins**: Can approve/reject posts, post directly
- **Regular Users**: Can submit content for review
- **Mandatory Membership**: Admins must be members of the required channel to perform admin actions

### Security Features

- Atomic file operations with locking
- Backup rotation (keeps last 3 versions)
- Rate limiting to prevent spam
- Comprehensive audit logging
- No database - simple JSON storage
- Environment variable support for secrets

## 🧪 Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot --cov-report=html

# Run specific test file
pytest tests/test_admin_manager.py -v
```

## 📊 Audit Log Export

Export audit logs to CSV:

```bash
python scripts/export_audit_log.py logs/bot.log audit_export.csv
```

## 🐛 Troubleshooting

### Bot doesn't respond
- ✅ Check bot token is correct
- ✅ Ensure bot is running (`python -m bot.main`)
- ✅ Check logs in `logs/bot.log`

### "Not enough rights" errors
- ✅ Promote bot to admin in Report Group and Output Channel
- ✅ Ensure bot has required permissions (see Security section)

### Admins can't perform actions
- ✅ Check they are members of the required channel
- ✅ Verify their user ID is in `config/admins.json`
- ✅ Check logs for permission errors

### Can't get chat IDs
- Use [@userinfobot](https://t.me/userinfobot) or [@getidsbot](https://t.me/getidsbot)
- Forward a message from the group/channel to the bot
- Check bot logs - IDs are logged on startup

### Config file errors
- ✅ Validate YAML syntax at [yamllint.com](http://www.yamllint.com/)
- ✅ Ensure all required fields are present
- ✅ Check that IDs are negative numbers for groups/channels

## 🔄 Webhook Mode (Optional)

For production deployments with high traffic:

1. **Update config.yaml**:
```yaml
webhook:
  enabled: true
  url: "https://yourdomain.com"
  path: "/webhook"
  port: 8443
```

2. **Set up reverse proxy** (nginx example):
```nginx
location /webhook {
    proxy_pass http://localhost:8443;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

3. **Ensure HTTPS**: Telegram requires HTTPS for webhooks

## 📁 Project Structure

```
telegram-channel-bot/
├── bot/
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration loader
│   ├── handlers/               # Message & command handlers
│   ├── services/               # Business logic services
│   ├── utils/                  # Utilities
│   ├── middleware/             # Middleware (future use)
│   └── locales/                # Translations
├── tests/                      # Unit tests
├── config/                     # Configuration files
├── docker/                     # Docker files
├── scripts/                    # Utility scripts
├── logs/                       # Log files (generated)
└── requirements.txt            # Dependencies
```

## 🌐 Localization

All UI text is in Persian (Farsi) and stored in `bot/locales/fa.json`. To add another language:

1. Copy `fa.json` to `en.json` (or your language code)
2. Translate all strings
3. Update `config.yaml` to point to new locale file
4. Modify code to support language selection (future enhancement)

## 🔧 Advanced Configuration

### Rate Limiting

Adjust in `config.yaml`:
```yaml
rate_limit_submissions: 5      # Max submissions
rate_limit_window: 3600        # Per hour (in seconds)
```

### Log Rotation

Logs automatically rotate at 10MB with 5 backup files. Adjust in `bot/services/audit_logger.py`:
```python
maxBytes=10 * 1024 * 1024,  # 10MB
backupCount=5,
```

### Backup Retention

Admin file backups keep last 3 versions. Adjust in `bot/services/admin_manager.py`:
```python
for old_backup in backups[:-3]:  # Change -3 to keep more/fewer
```

## 📝 Example Workflow

1. **User sends photo** to bot
2. Bot asks for subject: "لطفاً نام موضوع را وارد کنید:"
3. User replies: "گل های بهاری"
4. Bot posts to Report Group with inline buttons
5. Admin clicks "✅ تایید"
6. Bot posts to Output Channel with footer:
   ```
   [Photo]
   
   ───────────────────
   ── موضوع: گل های بهاری
   ── کانال: -1001234567891
   ```
7. Audit log records the approval

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Built with [aiogram v3](https://docs.aiogram.dev/)
- Persian UI for Iranian Telegram communities
- Inspired by channel management needs

## 📞 Support

- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Telegram**: [@your_support_username]
- **Email**: your-email@example.com

---

**Note**: Never commit real tokens, user IDs, or production config files to version control. Use `.env` and ensure it's in `.gitignore`.