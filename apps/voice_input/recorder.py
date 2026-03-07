"""Voice recording and speech-to-text."""


def record_and_transcribe(duration: int = 10) -> str:
    """Record audio and transcribe using speech_recognition.

    Requires: pip install SpeechRecognition pyaudio
    Falls back to text input if audio dependencies not available.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=duration)
        return recognizer.recognize_google(audio)
    except ImportError:
        return input("(Audio not available) Type your response: ")
    except Exception:
        return input("(Audio error) Type your response: ")
