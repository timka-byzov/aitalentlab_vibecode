# ITMO Admission Bot

This Telegram bot helps prospective students choose between two AI master's programs at ITMO University and plan their studies based on their background.

## Features
- Parses curriculum data from ITMO University websites
- Recommends elective courses based on student background
- Generates personalized study plans
- Answers questions about the programs
- Supports both Russian and English languages

## Project Structure
```
├── core/                  # Core application logic
│   ├── domain/            # Domain models
│   └── services/          # Business logic services
├── infrastructure/        # Infrastructure components
│   ├── scraping/          # Web scraping functionality
│   └── telegram/          # Telegram bot implementation
├── examples/              # Sample curriculum data
├── src/                   # Additional source files
├── knowledge_areas.yaml   # Configuration of knowledge areas
├── requirements.txt       # Python dependencies
└── test_parser.py         # Parser test script
```

## Setup
1. Create a virtual environment:
```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create .env file with your Telegram bot token
echo "TELEGRAM_BOT_TOKEN='your_bot_token_here'" > .env
```

4. Run the bot:
```bash
python infrastructure/telegram/bot.py
```

## Configuration
The `knowledge_areas.yaml` file defines knowledge areas used for recommendations. Example structure:
```yaml
knowledge_areas:
  math:
    - математика
    - алгебра
    - анализ
  programming:
    - программирование
    - алгоритм
    - python
```

## Testing
Run the test script to verify curriculum parsing:
```bash
python test_parser.py
```

## Usage
1. Start the bot with `/start`
2. Choose a program (AI or AI Product)
3. Rate your background in 5 areas (0-5)
4. Receive a personalized study plan
5. Ask questions about the program

Example interaction:
```
User: /start
Bot: Welcome! Choose a program: [AI, AI Product]
User: AI
Bot: Rate your math background (0-5): 
User: 4
...
```

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a pull request

## Roadmap
- [ ] Add more program options
- [ ] Implement course scheduling
- [ ] Add multilingual support
- [ ] Create web interface