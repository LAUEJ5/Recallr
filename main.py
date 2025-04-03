import speech_recognition as sr
import difflib

# User-defined text
target_text = input("Enter the text you want to memorize:\n").strip()
target_words = target_text.split()
revealed = [False] * len(target_words)

def print_current_state():
    output = []
    for i, word in enumerate(target_words):
        if revealed[i]:
            output.append(word)
        else:
            output.append("●" * len(word))  # Simulate blur
    print(" ".join(output))

recognizer = sr.Recognizer()
mic = sr.Microphone()

print("\nStart reciting. Press Ctrl+C to stop.")
print_current_state()

try:
    while not all(revealed):
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            print("\nListening...")
            audio = recognizer.listen(source)
        
        try:
            transcript = recognizer.recognize_google(audio)
            spoken_words = transcript.strip().split()
            print(f"You said: {transcript}")

            for spoken_word in spoken_words:
                for i, (word, done) in enumerate(zip(target_words, revealed)):
                    if not done and difflib.SequenceMatcher(None, spoken_word.lower(), word.lower()).ratio() > 0.8:
                        revealed[i] = True
                        break

            print_current_state()
        
        except sr.UnknownValueError:
            print("Didn't catch that. Try again.")
        except sr.RequestError:
            print("Speech service error.")

except KeyboardInterrupt:
    print("\nSession ended.")
