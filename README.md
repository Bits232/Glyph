# Glyph

An AI writing assistant that lives inside your editor. Generate content, edit existing text, ask questions about what you're working on — without switching tabs or copy-pasting between tools.

Built with Django, vanilla JS, and Groq's Llama 3.1 for fast inference. Video transcription powered by Mux.

![Glyph Editor](<!-- add your editor screenshot here -->)

---

## What it does

Glyph has three modes, accessible from the AI panel on the right side of the editor:

- **Generate** — describe what you want and Glyph writes it directly into your document
- **Edit** — tell it how to change your text; works on the whole document or a selected passage
- **Ask** — ask questions about what you're writing, fact-check claims, get summaries

You can also attach a video URL and Glyph will transcribe the audio and drop the full transcript into the editor. Supports direct video links (Vimeo, Dropbox, Google Drive, .mp4 etc.) — not YouTube.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.x |
| AI | Groq API (Llama 3.1 8B Instant) |
| Database | Supabase (usage logging) |
| Video transcription | Mux API |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Editor | TipTap (ProseMirror-based) |
| Hosting | Vercel |

---

## Getting started

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier works)
- A [Supabase](https://supabase.com) project (for logging — optional but expected by the app)
- [Mux](https://mux.com) credentials (only needed for video transcription)

### Installation

**1. Clone the repo**
```bash
git clone https://github.com/Bits232/Glyph.git
cd Glyph
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up environment variables**

Copy the example env file and fill in your credentials:
```bash
cp .env.example .env
```

Open `.env` and add:
```
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
MUX_TOKEN_ID=your_mux_token_id
MUX_TOKEN_SECRET=your_mux_token_secret
SECRET_KEY=your_django_secret_key
```

**4. Run migrations**
```bash
python manage.py migrate
```

**5. Start the server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000/login/` and log in with:
- Email: `test@glyph.com`
- Password: `GlyphTest2026`

---

## Project structure

```
Glyph/
├── App/
│   ├── views.py          # All request handlers — AI, auth, video transcription
│   ├── urls.py           # App-level URL routes
│   ├── models.py         # Database models
│   └── migrations/
├── Project/
│   ├── settings.py       # Django configuration
│   ├── urls.py           # Root URL router
│   └── wsgi.py / asgi.py
├── templates/
│   └── App/
│       ├── login.html    # Login page
│       └── editor_ui.html # Main editor with AI panel
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── build_files.sh        # Vercel build script
└── vercel.json           # Vercel deployment config
```

---

## How the AI works

Requests hit the `/api/ai/` endpoint with three fields:

- `action` — one of `generate`, `edit`, or `ask`
- `text` — the user's prompt or instruction
- `context` — the document content (or selected text range for edit mode)

The backend builds a mode-specific prompt and sends it to Groq's `llama-3.1-8b-instant` model. Responses come back as HTML, which TipTap renders directly into the editor.

Every request and response is logged to Supabase with token usage, action type, and a truncated copy of the input/output — useful for understanding how people actually use the tool.

---

## Video transcription

Paste a direct video URL into the attachment input. Glyph sends it to Mux, which processes the video, generates captions automatically, and returns the transcript as plain text. The transcript is then inserted into the current document.

**Supported sources:** Direct video URLs (.mp4, .mov, .webm), Vimeo, Dropbox, Google Drive public links  
**Not supported:** YouTube (Mux cannot process YouTube URLs)

Note: Transcription takes time depending on video length — Mux polls every 15 seconds up to a 10-minute timeout.

---

## Deployment

Glyph is configured for Vercel. The `build_files.sh` script handles pip install and static file collection. `vercel.json` routes all requests through Django's WSGI handler.

To deploy your own:

1. Fork the repo
2. Connect it to a new Vercel project
3. Add all environment variables in Vercel's dashboard under Settings → Environment Variables
4. Deploy

Make sure your `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and `MUX_TOKEN_ID`/`MUX_TOKEN_SECRET` are all set — the app will fail to start without them.

---

## Known limitations

- Authentication is currently a single hardcoded test account — not suitable for production multi-user use
- Video transcription blocks the request thread while polling Mux (long videos will time out on Vercel's serverless functions)
- Save and Export buttons are present in the UI but not fully wired up in this version
- No mobile layout — designed for desktop

---

## Background

Glyph was originally built for the Mux Hackathon in late 2025. It sat abandoned for six months before being revived and finished for the GitHub Finish-Up-A-Thon Challenge in June 2026.

The core problem it solves hasn't changed: writers shouldn't have to leave their editor to use AI. Everything should be in one place.

---

## License

MIT
