TOMMY PHASE 4 - OPTIMIZED VOICE

Replace these files in your project:

backend/
  speech.py
  groq_ai.py
  main.py

frontend/
  app.js
  style.css

Also update requirements.txt.

Then run:

pip install -r requirements.txt
python start_tommy.py

What was optimized:
- Wake word remains removed.
- Mic starts only after button click.
- Faster speech recognition timing.
- Shorter Groq voice responses.
- Code/markdown is not spoken.
- TTS is generated sentence-by-sentence so the first sentence can start sooner.
- Mouth animation is much faster (90ms animation cycle).
- Speaking animation starts immediately when TTS begins.
