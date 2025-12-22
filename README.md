# X Reply Bot 🤖

**Raw, No-Filter, Unapologetically Based** - An AI-powered X (Twitter) reply bot that learns and engages authentically.

## 🔥 Features

- **Two Commands**: Separate learning and active modes
- **Autonomous Learning**: Runs forever, improves without intervention
- **Your Personality**: Raw, direct, no BS - using code terms to dissect ideas (like @KharayKrayKray)
- **Free OpenRouter Models**: Uses gpt-oss-120b, Gemini Flash, Chimera (all FREE)
- **Smart Engagement**: AI predicts viral potential and decides best actions
- **Human-Like Behavior**: Randomized timing, natural gaps, realistic patterns
- **Rate Limit Compliance**: Hard-coded 17/day, 500/month for X free tier

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd "c:\Users\IDRIS\Desktop\REPLY BOT"
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy example configs and add your keys:

```bash
copy config\x_credentials.json.example config\x_credentials.json
copy config\openrouter_config.json.example config\openrouter_config.json
```

Edit with your actual API keys.

### 3. Run Learning Mode (First!)

```bash
python learn_mode.py
```

This runs **FOREVER** - collecting posts, analyzing styles, improving predictions.  
No intervention needed. Just let it learn in the background.

### 4. Run Main Bot

```bash
python main.py
```

Or for testing without actually posting:

```bash
python main.py --dry-run
```

## 📁 Project Structure

```
x-reply-bot/
├── config/
│   ├── bot_config.json           # Your personality settings
│   ├── accounts_to_learn.json    # Target accounts (@KharayKrayKray)
│   ├── openrouter_config.json    # AI model settings
│   └── x_credentials.json        # X API keys (gitignored)
│
├── data/                         # Auto-created, gitignored
│   ├── posts.json               # Collected posts
│   ├── learning_history.json    # Style analysis
│   ├── engagement_metrics.json  # What works
│   └── action_log.json          # Actions taken
│
├── src/
│   ├── core/                    # API clients, rate limiter
│   ├── learning/                # Collectors, analyzers, predictors
│   ├── reasoning/               # Decision maker, content gen, safety
│   ├── actions/                 # Poster, replier, quoter
│   └── utils/                   # Logger, scheduler
│
├── learn_mode.py                # Command 1: Autonomous learning
├── main.py                      # Command 2: Active engagement
└── requirements.txt
```

## 🎭 Your Personality

The bot is configured with your raw, no-filter personality:

- **Style**: ISTP/ESTP - Direct, action-oriented
- **Communication**: ALL CAPS when serious, short sentences, truth > grammar
- **Humor**: Sarcastic, dark, self-aware
- **Special**: Uses code/tech terms to dissect ideas (learned from @KharayKrayKray)

### Content Mix

- 35% Shitposts (funny, relatable, chaotic)
- 15% Hot Takes (controversial, engagement bait)
- 50% Valuable Insights (actual useful info)

## 🤖 OpenRouter Models

Using these FREE models:

| Model                                          | Use Case                   |
| ---------------------------------------------- | -------------------------- |
| `openai/gpt-oss-120b`                          | Primary content generation |
| `google/gemini-2.5-flash-lite-preview-09-2025` | Fast analysis              |
| `qwen/qwen3-next-80b-a3b-instruct`             | Reasoning/decisions        |
| `openai/gpt-5-nano`                            | Quick responses            |
| `tngtech/tng-r1t-chimera:free`                 | Learning analysis          |

## 📊 Rate Limits

X Free Tier enforced:

- **17 posts/day** (2 original, 1 quote, 14 replies)
- **500 posts/month**
- Actions distributed throughout active hours (6am-11pm WAT)

## 🛠️ Commands

### Learning Mode

```bash
python learn_mode.py              # Run forever
python learn_mode.py --test       # Single cycle then exit
python learn_mode.py --stats      # Show stats only
```

### Main Bot

```bash
python main.py                    # Run continuously
python main.py --dry-run          # Test without posting
python main.py --single           # Single action then exit
python main.py --status           # Show status only
```

## 📈 Growth Expectations

| Timeline | Followers  | Engagement |
| -------- | ---------- | ---------- |
| Month 1  | +50-150    | 2-4%       |
| Month 3  | +300-600   | 4-8%       |
| Month 6  | +1000-2000 | 6-12%      |
| Month 12 | +3000-8000 | 8-15%      |

## ⚠️ Important Notes

1. **Run learning first** - Bot needs data before engaging
2. **Keep learning running** - It improves continuously
3. **Monitor early** - Check dry-run before going live
4. **Respect limits** - Bot enforces them, but X may have hidden ones

## 🔧 Troubleshooting

**Bot sounds robotic?**

- Run `learn_mode.py` for longer (24-48 hours minimum)
- Add more accounts to `accounts_to_learn.json`

**Low engagement?**

- Check `data/engagement_metrics.json` for best times
- Adjust `active_hours` in bot_config.json

**Rate limit errors?**

- Check `data/action_log.json` for duplicate entries
- Wait for daily reset (midnight WAT)

**OpenRouter timeout?**

- Switch to faster model in config
- Try `openai/gpt-5-nano` for quick responses

---

**Built for growth. Raw authenticity. No filter.** 🚀
