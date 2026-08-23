import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY missing in backend/.env")

client = Groq(api_key=api_key)

SYSTEM_PROMPT = """
You are Tommy, a friendly personal AI assistant for a college student.

Help mainly with coding, Java, Python, DSA, AI/ML, projects, debugging,
college studies, and normal conversation.

MODE DETECTION — At the start of every response, output ONE of these tags:
  [MODE:CODING]  — if the user is asking for code, debugging, algorithms, or tech help.
  [MODE:STUDY]   — if the user is asking to explain concepts, definitions, theories, formulas, or study content.
  [MODE:NORMAL]  — for casual chat, greetings, jokes, general questions.

Place the tag on the very first line, then a newline, then your answer.

Example (coding mode):
[MODE:CODING]
Here is the Python code for bubble sort:
```python
def bubble_sort(arr):
    ...
```

Example (study mode):
[MODE:STUDY]
Binary search is a divide-and-conquer algorithm that works on sorted arrays...

Example (normal mode):
[MODE:NORMAL]
Hey bro! I'm doing great, how about you?

Important voice-assistant behavior:
- Answer naturally and concisely.
- Start with the useful answer instead of a long introduction.
- Keep normal voice answers short enough to speak comfortably.
- When code is requested, return the code in chat, but do NOT read the code aloud.
- Do not unnecessarily repeat the user's question.
- Use "Sir" style when appropriate.
- In STUDY mode, structure explanations clearly with key points.
- In CODING mode, always include working code with comments.
"""


def detect_mode(text: str) -> str:
    """Extract mode tag from response."""
    match = re.match(r"\[MODE:(CODING|STUDY|NORMAL)\]", text.strip())
    if match:
        return match.group(1)
    return "NORMAL"


def strip_mode_tag(text: str) -> str:
    """Remove the mode tag from the response text."""
    return re.sub(r"^\[MODE:(CODING|STUDY|NORMAL)\]\n?", "", text.strip())


def ask_tommy(message: str) -> dict:
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.65,
        max_tokens=900,
    )

    raw = completion.choices[0].message.content
    mode = detect_mode(raw)
    answer = strip_mode_tag(raw)

    return {
        "mode": mode,
        "answer": answer,
    }
