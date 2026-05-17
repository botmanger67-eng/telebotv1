# telegram-ai-assistant-bot

A Telegram bot that uses DeepSeek AI for smart conversations, auto-detects URLs, weather, translations, calculations, and GitHub links, with optional commands for search, news, images, and more.

## Features

- **AI-powered chat** – leverages DeepSeek API for intelligent conversations
- **Auto-detection** – detects and processes URLs, weather queries, translations, calculations, and GitHub links
- **Search engine integration** – uses DuckDuckGo Search for web, news, and image queries
- **GitHub tools** – extracts and processes GitHub links (repos, issues, etc.)
- **Link checking** – validates and summarizes URLs found in messages
- **Persistent storage** – SQLite database for user data and conversation history
- **Asynchronous operations** – built on `asyncio` for non-blocking performance

## Tech Stack

- **python-telegram-bot** – Telegram Bot API framework
- **DeepSeek API** – AI conversation engine
- **DuckDuckGo Search** – search, news, and image retrieval
- **SQLite** – lightweight embedded database
- **asyncio** – asynchronous I/O and concurrency

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-ai-assistant-bot.git
   cd telegram-ai-assistant-bot
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   At minimum, provide your `TELEGRAM_BOT_TOKEN` and `DEEPSEEK_API_KEY`.

5. **Initialize the database** (if required)
   ```bash
   python src/database.py   # Creates SQLite tables on first run
   ```

6. **Run the bot**
   ```bash
   python src/main.py
   ```

## Usage

Start the bot and send a message in Telegram. The bot automatically processes:

- **Plain text** – replies using DeepSeek AI
- **URLs** – extracts and summarizes content
- **Weather requests** – e.g., “weather London”
- **Translations** – e.g., “translate hello to French”
- **Calculations** – e.g., “calculate 2+2”
- **GitHub links** – fetches repository or issue details

Optional commands (example from `search_engine.py` and `github_tools.py`):
- `/search <query>` – web search (DuckDuckGo)
- `/news <topic>` – latest news
- `/image <query>` – image search
- `/github <url>` – explicit GitHub info

**Example interaction**

```
User: Hi, what's the weather in Tokyo?
Bot: The current weather in Tokyo is 22°C, partly cloudy.

User: https://github.com/username/repo
Bot: Repository "repo" by username, 42 stars, last updated 2025-01-15.

User: /news AI
Bot: Top stories: [1] OpenAI launches GPT-5... [2] ...
```

## Project Structure

```
├── src/main.py
├── src/config.py
├── src/ai_chat.py
├── src/search_engine.py
├── src/link_checker.py
├── src/github_tools.py
├── src/database.py
├── requirements.txt
├── .env.example
├── .gitignore
```

## API Endpoints

This bot does not expose its own API endpoints. It consumes the following external APIs:

- **DeepSeek API** – for chat completions (configured via `DEEPSEEK_API_KEY`)
- **DuckDuckGo Search** – web, news, and image searches (no API key required)
- **Telegram Bot API** – for message handling and command routing (via `TELEGRAM_BOT_TOKEN`)

Internal logic is handled entirely asyncio‑based, with event‑driven message flows.

## Environment Variables

The following variables must be defined in `.env` (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot token from [@BotFather](https://t.me/botfather) |
| `DEEPSEEK_API_KEY` | API key for DeepSeek AI service |
| `DATABASE_PATH` | (optional) Path to SQLite database file; defaults to `bot.db` |

Additional variables may be required depending on configuration (e.g., for custom search preferences), but the two tokens above are mandatory.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Make sure your code adheres to the existing style and includes appropriate documentation.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.