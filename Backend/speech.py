import asyncio
import os
import re
import tempfile
import threading
import time

import edge_tts
import pygame
import speech_recognition as sr


class TommySpeech:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        # Faster turn-taking.
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.75
        self.recognizer.phrase_threshold = 0.30
        self.recognizer.non_speaking_duration = 0.40

        self.microphone = sr.Microphone()
        self.voice = "en-IN-PrabhatNeural"

        pygame.mixer.init()
        self._tts_lock = threading.Lock()

    def calibrate(self):
        print("🎤 Calibrating microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.7)
        print("🎤 Microphone ready.")

    def listen(self, timeout=8):
        try:
            with self.microphone as source:
                print("🎤 Listening...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=16
                )

            print("🧠 Recognizing...")
            text = self.recognizer.recognize_google(
                audio,
                language="en-IN"
            )
            print(f"👤 You: {text}")
            return text

        except sr.WaitTimeoutError:
            print("⌛ Listening timeout.")
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand.")
            return None
        except sr.RequestError as error:
            print("Speech recognition error:", error)
            return None
        except Exception as error:
            print("Microphone error:", error)
            return None

    @staticmethod
    def clean_for_speech(text):
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"`[^`]*`", " ", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[*_#>|~]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def split_sentences(text, max_chars=220):
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        chunks = []
        current = ""

        for part in parts:
            if not part:
                continue

            if len(current) + len(part) + 1 <= max_chars:
                current = f"{current} {part}".strip()
            else:
                if current:
                    chunks.append(current)
                current = part

        if current:
            chunks.append(current)

        return chunks

    async def _generate_file(self, text, filename):
        communicate = edge_tts.Communicate(
            text,
            voice=self.voice,
            rate="+9%",
            volume="+2%",
            pitch="+0Hz"
        )
        await communicate.save(filename)

    def _play_file(self, filename):
        pygame.mixer.music.stop()

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(30)

        pygame.mixer.music.stop()

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    def _delete_file(self, filename):
        for _ in range(10):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                return
            except PermissionError:
                time.sleep(0.05)
            except OSError:
                time.sleep(0.05)

    def speak(self, text):
        spoken = self.clean_for_speech(text)

        if not spoken:
            return

        chunks = self.split_sentences(spoken)

        print("🔊 Tommy speaking...")

        with self._tts_lock:
            for index, chunk in enumerate(chunks):
                fd, filename = tempfile.mkstemp(
                    prefix="tommy_",
                    suffix=".mp3"
                )
                os.close(fd)

                try:
                    asyncio.run(
                        self._generate_file(chunk, filename)
                    )

                    self._play_file(filename)

                except Exception as error:
                    print("TTS error:", error)
                    break

                finally:
                    try:
                        pygame.mixer.music.stop()
                    except Exception:
                        pass

                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass

                    self._delete_file(filename)

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
