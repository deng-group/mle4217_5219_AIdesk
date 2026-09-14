# Web Chat Prototype

Minimal Flask web window for the MLE4217/5219 AI Learning Agent.

Run:

```bash
source ~/miniconda3/bin/activate && conda activate matsci && \
GEMINI_API_KEY=... python web_app/app.py
```

Open:

```text
http://127.0.0.1:5055
```

Notes:

- The course widget uses `/api/answer/stream`, so answer text and elapsed time update during generation.
- If `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` is set, the UI defaults to the Anthropic-compatible provider.
- If no Anthropic token is set but `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set, the UI defaults to Gemini.
- Without a Gemini key, the UI defaults to `dry_run`.
- Short memory is stored in browser `sessionStorage`, so it is scoped to the current window/tab.
- The book widget hides debug provider/model/source score details from students.

API configuration helper:

```bash
cp scripts/api_env.example.sh scripts/api_env.sh
source scripts/api_env.sh
```

Test the helper in the real sibling course website (not the standalone prototype):

```bash
python scripts/start_course_widget_test.py
```
