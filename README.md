# 🤖 Dictionary Bot

A Discord bot for **classical Arabic dictionary lookups**, backed by indexed classical lexicons and scanned page images.

---

## ✨ Features

- 📖 **Classical Lexicon Search** — BM25-style indexed search across Lisan al-Arab (~10,600 entries) and Qamus al-Muhit (~4,067 entries)
- 🌱 **Root Extraction** — Custom pure-Python Arabic root extractor for root-based lookup
- 🖼️ **Scanned Page Images** — Displays original scanned dictionary pages, proxied for reliability
- 🔐 **Role-Based Access** — Unrestricted access for one role, channel-restricted access for another

---

## 🚀 Commands

| Command | Description |
|---|---|
| `/lisan <word>` | Look up an entry in Lisan al-Arab |
| `/qamus <word>` | Look up an entry in Qamus al-Muhit |
| `/lughat <word>` | General dictionary/root lookup |
| `/lane <word>` | Lane's Lexicon lookup |
| `/lughat-scan <word>` | Gives exact page of a word from 22+ dictionaries |

---

## 🛠️ Tech Stack

| Service | Purpose |
|---|---|
| [discord.py](https://discordpy.readthedocs.io/) | Discord bot framework |
| BM25-style indexing | In-process dictionary search |
| Custom root extractor | Pure-Python Arabic root extraction |
| wsrv.nl | Image proxy for scanned dictionary pages |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Environment variable management |

---

## 📋 Prerequisites

- Python 3.11+
- Discord Bot Token

---


## 📁 Project Structure

```
├── data/                    # SQLite dictionary databases
│   ├── ejtaal_index.db
│   ├── lane_lexicon.db
│   ├── lisan_index.db
│   └── qamus_al_muhit_index.db
│
├── bot.py                   # Discord bot entry point
├── config.py                # Configuration and environment variables
├── database.py              # Database connection utilities
├── ejtaal_db.py             # Ejtaal dictionary interface
├── root_extractor.py        # Arabic root extraction logic
├── text_utils.py            # Arabic text processing helpers
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## 🔑 Getting API Keys

### Discord Bot Token
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create new application → Bot → Reset Token
3. Enable **Message Content Intent**

---

## 🤝 Invite Bot to Your Server

Generate an invite link:
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. OAuth2 → URL Generator
3. Select `bot` and `applications.commands` scopes
4. Select permissions: `Read Messages`, `Send Messages`, `Use Slash Commands`
5. Copy and share the generated URL

---

## ⚠️ Important Notes

- Restricted-role access only works in channels you've explicitly configured

---


---

## Contributing

Contributions, feature requests, and bug reports are welcome.

Feel free to fork the repository and submit a pull request.

---

⭐ If this project helped you, consider giving it a star on GitHub!
