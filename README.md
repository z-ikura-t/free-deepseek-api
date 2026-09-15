# free-deepseek-api

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-Chat-purple.svg)](https://chat.deepseek.com/)

Local asynchronous API proxy for DeepSeek Chat. Provides a REST API for chat, file uploads, and image recognition using your DeepSeek account.

This is not the official DeepSeek API and not a local model. It is a browser-based proxy (works with DeepSeek Chat web version **2.5**): you authenticate in DeepSeek Chat, save the session, and provide a local API for your tools.

## Overview
- **Chats** — list, create, load, rename, delete chats
- **Messages** — send prompts, receive responses, stream via SSE
- **Files** — upload files and attach to messages
- **Vision** — analyze images via file uploads
- **TTS** — generate text-to-speech audio for a specific message (Ogg Opus), with voice selection
- **Search** — enable internet search for real-time information
- **Thinking** — enable chain-of-thought reasoning

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

## API Endpoints

### Health

Check API health and DeepSeek token validity.

```bash
curl -X GET 'http://127.0.0.1:4971/api/health'
```

### Get Chats

List all chats with optional pagination or date filtering.

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

> **Note:** if any date parameter is provided, `start` and `end` are ignored.

### Delete Chats

Delete one or more chats by their IDs.

```bash
curl -X DELETE 'http://127.0.0.1:4971/api/chats' \
  -H 'Content-Type: application/json' \
  -d '{"chat_ids": ["chat-id-1", "chat-id-2"]}'
```

Replace `chat_ids` with the actual chat IDs.

**Example:**
```bash
curl -X DELETE 'http://127.0.0.1:4971/api/chats' \
  -H 'Content-Type: application/json' \
  -d '{
    "chat_ids": [
      "4a03e37a-bd78-4374-aa18-f1a4ba2cce43",
      "221bca6b-8eaa-456c-8ef5-a54f3237c96f"
    ]
  }'
```

### Create chat

Create a new empty chat.

```bash
curl -X POST 'http://127.0.0.1:4971/api/chat/create'
```

### Get chat

Load a chat with all its messages by ID.

```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/{chat_id}'
```

Replace `{chat_id}` with the actual chat ID.

**Example:**
```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/4a03e37a-bd78-4374-aa18-f1a4ba2cce43'
```

### Update Chat Title

Change the title of a chat by ID.

```bash
curl -X PATCH 'http://127.0.0.1:4971/api/chat/{chat_id}/title' \
  -H 'Content-Type: application/json' \
  -d '{"title": "New chat title"}'
```

**Replace:**
- `{chat_id}` — the actual chat ID
- `title` — new title of the chat

**Example:**
```bash
curl -X PATCH 'http://127.0.0.1:4971/api/chat/4a03e37a-bd78-4374-aa18-f1a4ba2cce43/title' \
  -H 'Content-Type: application/json' \
  -d '{"title": "Questions"}'
```

### Upload Files

Upload one or more files to DeepSeek and get their file IDs.

```bash
curl -X POST 'http://127.0.0.1:4971/api/files/upload' \
  -H 'Content-Type: application/json' \
  -d '{"file_paths": ["/absolute/path/to/file.txt"]}'
```

Replace `/absolute/path/to/file.txt` with the actual absolute path to your file.

**Example:**
```bash
curl -X POST 'http://127.0.0.1:4971/api/files/upload' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_paths": [
      "/path/to/your/document.pdf",
      "/path/to/your/image.png"
    ]
  }'
```

**Important:**
- File size limit: 100 MB per file.

### Chat Completions

Send a user message and receive the assistant's response. Supports streaming for real-time output and file attachments, including images for vision-based analysis.

**Streaming mode:**
```bash
curl -N -X POST 'http://127.0.0.1:4971/api/chat/completions?stream=true' \
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
curl -X POST 'http://127.0.0.1:4971/api/chat/completions' \
  -H 'Content-Type: application/json' \
  -d '{
  "chat_id": "chat_id",
  "parent_message_id": null,
  "prompt": "your message",
  "file_ids": []
}'
```

**Replace:**
- `chat_id` — the actual chat ID
- `parent_message_id` — null for the first message, or the ID of the last message you want to reply to
- `prompt` — your message text
- `file_ids` — list of file IDs from **Upload Files**

**Example (streaming):**
```bash
curl -N -X POST 'http://127.0.0.1:4971/api/chat/completions?stream=true' \
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

## TTS

### Generate Audio

Generate text-to-speech audio for the specified message. Returns **Ogg Opus** audio (`audio/ogg`) — play it directly or save it to a file.

```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/{chat_id}/tts/{message_id}'
```

**Replace:**
- `{chat_id}` — the actual chat ID
- `{message_id}` — message ID to convert to speech

**Example (save audio to a file):**
```bash
curl -X GET 'http://127.0.0.1:4971/api/chat/8da7a55b-81db-4b13-b5b2-cc25d77148b8/tts/6' \
  -o audio1.opus
```

**Important:**
- Only assistant messages can be voiced.
- No streaming for TTS — the full audio is generated before returning.

### Get Voices

Return all available TTS voices.

```bash
curl -X GET 'http://127.0.0.1:4971/api/tts/voices'
```

### Get Current Voice

Return the currently selected TTS voice.

```bash
curl -X GET 'http://127.0.0.1:4971/api/tts/voice'
```

### Set Voice

Change the current TTS voice.

**Example:**
```bash
curl -X PUT 'http://127.0.0.1:4971/api/tts/voice' \
  -H 'Content-Type: application/json' \
  -d '{"voice_id": "echo"}'
```

## Settings

Manage global settings via API.

### Available settings
- **Search** — enables internet search. Allows DeepSeek to retrieve real-time information from the web.
- **Thinking** — enables chain-of-thought reasoning. Improves accuracy on complex tasks.
- **Token** — shows or updates your DeepSeek authentication token.

**Enable/disable:**
- Search
- Thinking

**Example:**
```bash
curl -X PUT 'http://127.0.0.1:4971/api/feature/search/enabled' \
  -H 'Content-Type: application/json' \
  -d '{"enabled": true}'
```

**Set token:**
```bash
curl -X PUT 'http://127.0.0.1:4971/api/token' \
  -H 'Content-Type: application/json' \
  -d '{"value": "your_new_token"}'
```

## Usage example

Simple Python example using curl_cffi:

```python
import asyncio
from curl_cffi.requests import AsyncSession

FREE_DEEPSEEK_API_URL = 'http://127.0.0.1:4971/api'


def get_error_detail(response) -> str:
    try:
        detail = response.json().get('detail', 'Unknown error')
        if isinstance(detail, list):
            return detail[0].get('msg', 'Unknown error') if detail else 'Unknown error'
        if not isinstance(detail, str):
            return 'Unknown error'
        return detail
    except Exception:
        return response.text or 'Unknown error'


async def create_chat() -> dict:
    async with AsyncSession() as session:
        response = await session.post(f'{FREE_DEEPSEEK_API_URL}/chat/create')
        if response.status_code != 201:
            detail = get_error_detail(response)
            raise Exception(f'[{response.status_code}] {detail}')
        return response.json()


async def send_message(chat_id: str, parent_message_id: int | None, prompt: str) -> dict:
    async with AsyncSession() as session:
        response = await session.post(
            f'{FREE_DEEPSEEK_API_URL}/chat/completions',
            json={
                'chat_id': chat_id, 
                'parent_message_id': parent_message_id, 
                'prompt': prompt, 
                'file_ids': []
            },
        )
        if response.status_code != 201:
            detail = get_error_detail(response)
            raise Exception(f'[{response.status_code}] {detail}')
        return response.json()


async def create_chat_and_send() -> None:
    chat = await create_chat()
    chat_id = chat['chat_id']
    print(f'New chat created: {chat_id}')
    
    response = await send_message(chat_id, None, 'Hello! What can you do?')
    
    print('\nUser:', response['user']['content'])
    print('\nAssistant:', response['assistant']['content'])


asyncio.run(create_chat_and_send())
```

**This example:**
- Creates a new chat
- Sends a message to it
- Prints the user's message and the assistant's reply

## Limitations

- This is an unofficial proxy, use responsibly.
- The API is for local development and testing purposes only.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.