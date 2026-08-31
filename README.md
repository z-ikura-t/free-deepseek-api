# free-deepseek-api

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-Chat-purple.svg)](https://chat.deepseek.com/)

Custom local asynchronous API proxy for DeepSeek Chat. Provides a REST API for chat, file uploads, and image recognition using your DeepSeek account.

This is not the official DeepSeek API and not a local model. It is a browser-based proxy: you authenticate in DeepSeek Chat, saves the session, and provides a local API for your tools.

## Requirements
- Python 3.10+

## Quick Start
```bash
git clone https://github.com/z-ikura-t/free-deepseek-api
cd free-deepseek-api
pip install -r requirements.txt
```

## DeepSeek Chat Authorization

### Auto

Run the built-in script to automatically get your token:

```bash
python auth.py
```

A Chrome window will open. Log in or sign up to DeepSeek Chat, then return to the terminal and press Enter. The token will be saved to `.env` automatically.

> **Note:** Google Chrome is required for auto authorization. If Chrome is not installed, use the manual method below.

### Manual

Create a .env file in the root directory and add your DeepSeek token:

```env
DEEPSEEK_TOKEN=your_token_here
```

How to get the token manually:
1. Open **DeepSeek Chat** in your browser
2. Open **Developer Tools** (F12 or right-click > Inspect)
3. Go to the **Network** tab
4. Send a message in DeepSeek Chat
5. Find the `completion` request in the **Network** tab
6. Open the **Headers** section
7. Find **Authorization** in **Request Headers**
8. Copy the token after `Bearer`  (without the "Bearer " prefix)

**Important:**
- Do not share your token with anyone.
- The token is stored locally in your `.env` file.
- Do not commit or publish your `.env` file.
- The token will change when you log out of your DeepSeek account.

## Run
```bash
uvicorn run:client --reload --port 4971
```

Once the server is running, full interactive API documentation is available at:

[http://127.0.0.1:4971/docs#](http://127.0.0.1:4971/docs#)

## Models

DeepSeek supports three model variants. You can switch models using the `/api/model` endpoint.

| Mode | API Value | Description |
|------|-----------|-------------|
| Fast | `default` | Fast responses, supports internet search, files, and images. |
| Expert | `expert` | Deep reasoning for complex tasks. No internet search, files, or images. |
| Vision | `vision` | Analyze photos, screenshots, PDFs, diagrams. No internet search. |

**Important:**
- Model changes apply only to new chats.

Set model via API:
```bash
curl -X PUT 'http://127.0.0.1:4971/api/model' \
  -H 'Content-Type: application/json' \
  -d '{
  "value": "model type"
}'
```

## API Endpoints


### Get Chats

```bash
curl -X GET 'http://127.0.0.1:4971/api/chats'
```

**Examples:**

```bash
# Pagination
curl -X GET 'http://127.0.0.1:4971/api/chats?start=0&end=100'

# Date range
curl -X GET 'http://127.0.0.1:4971/api/chats?start_date=2026-08-15&end_date=2026-08-30'
```

### Create chat

```bash
curl -X POST 'http://127.0.0.1:4971/api/chat/create'
```

### Get chat

```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/{chat_id}'
```

Replace `{chat_id}` with the actual chat ID.

**Example:**
```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/4a03e37a-bd78-4374-aa18-f1a4ba2cce43'
```

### Upload File

```bash
curl -X POST 'http://127.0.0.1:4971/api/file/upload' \
  -F 'file=@/path/to/your/file.txt'
```

Replace `/path/to/your/file.txt` with the actual path to your file.

**Example:**
```bash
curl -X POST 'http://127.0.0.1:4971/api/file/upload' \
  -F 'file=@image1.jpg'
```

**Important:**
- Upload files for `vision` model only when `vision` is already selected.
- Files uploaded in `vision` model will not be recognized in `default` or `expert` models.

### Generate Message

**Streaming mode:**
```bash
curl -N -X POST 'http://127.0.0.1:4971/api/chat/generate?stream=true' \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_id": "{chat_id}",
    "parent_message_id": null,
    "prompt": "your message",
    "file_ids": []
  }'
```

**Non-streaming mode (returns complete JSON):**
```bash
curl -X POST 'http://127.0.0.1:4971/api/chat/generate' \
  -H 'Content-Type: application/json' \
  -d '{
  "chat_id": "{chat_id}",
  "parent_message_id": null,
  "prompt": "your message",
  "file_ids": []
}'
```

- chat_id — the actual chat ID
- parent_message_id — null for the first message, or the ID of the last message you want to reply to
- prompt — your message text
- file_ids — list of file IDs from **Upload File**

**Example (streaming):**
```bash
curl -N -X POST 'http://127.0.0.1:4971/api/chat/generate?stream=true' \
  -H 'Content-Type: application/json' \
  -d '{
  "chat_id": "221bca6b-8eaa-456c-8ef5-a54f3237c96f",
  "parent_message_id": 6,
  "prompt": "What does it say?",
  "file_ids": [
    "file-3fb90c05-52c5-481e-891b-8a130975794c"
  ]
}'
```

## Settings

Manage features via API.

### Available settings
- **Search** — enables internet search. Allows DeepSeek to retrieve real‑time information from the web.
- **Thinking** — enables chain‑of‑thought reasoning. Improves accuracy on complex tasks.
- **Base Prompt** — sets a system prompt that is automatically prepended to every user message.
- **Token** — view or update your DeepSeek authentication token.

**Enable/disable:**
- Search
- Thinking
- Base Prompt

**Example:**
```bash
curl -X PUT 'http://127.0.0.1:4971/api/feature/search/enabled' \
  -H 'Content-Type: application/json' \
  -d '{"enabled": true}'
```

**Set value:**
- Base Prompt
- Token

**Example:**
```bash
curl -X PUT 'http://127.0.0.1:4971/api/feature/base_prompt' \
  -H 'Content-Type: application/json' \
  -d '{"value": "Without Markdown: \n"}'
```

## Usage example

Simple Python example using curl_cffi:

```python
import asyncio
from curl_cffi.requests import AsyncSession

FREE_DEEPSEEK_API_URL = 'http://127.0.0.1:4971/api'

async def get_chats(start: int = 0, end: int = 100) -> list[dict]:
    async with AsyncSession() as session:
        chats = await session.get(f'{FREE_DEEPSEEK_API_URL}/chats?start={start}&end={end}')
        return chats.json()

async def get_chat(chat_id: str) -> list[dict]:
    async with AsyncSession() as session:
        chat = await session.get(f'{FREE_DEEPSEEK_API_URL}/chat/{chat_id}')
        return chat.json()

async def get_last_chat_messages() -> None:
    chats = await get_chats(start=0, end=1)
    if not chats.get('detail') is None: raise Exception(chats['detail'])
    chat = await get_chat(chats['chats'][0]['chat_id'])
    if not chat.get('detail') is None: raise Exception(chat['detail'])
    print('Last chat messages: ')
    for message in chat['messages']:
        print('\n', '-' * 75, '\n')
        print(f'Role: {message["role"]}')
        print(f'Content: \n{message["content"]}')

asyncio.run(get_last_chat_messages())
```

This example:
- Fetches the list of chats
- Gets the last chat
- Prints all messages from that chat with role and content

## Limitations

- This is an unofficial proxy, use responsibly.
- The API is for local development and testing purposes only.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.