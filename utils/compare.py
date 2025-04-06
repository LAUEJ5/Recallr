from fuzzywuzzy import fuzz
from typing import List, Tuple

def compare_transcript(transcript_words: List[str], reference_words: List[str]) -> List[Tuple[str, bool]]:
    """
    Compares each word in the transcript to the reference using fuzzy logic.
    Returns a list of (word, correct) tuples.
    """
    result = []
    ref_index = 0

    for word in transcript_words:
        if ref_index >= len(reference_words):
            result.append((word, False))
            continue

        score = fuzz.ratio(word.lower(), reference_words[ref_index].lower())
        if score > 80:
            result.append((reference_words[ref_index], True))
            ref_index += 1
        else:
            match_found = False
            for lookahead in range(1, 3):
                if ref_index + lookahead < len(reference_words):
                    future_score = fuzz.ratio(word.lower(), reference_words[ref_index + lookahead].lower())
                    if future_score > 80:
                        result.append((reference_words[ref_index + lookahead], True))
                        ref_index += lookahead + 1
                        match_found = True
                        break
            if not match_found:
                result.append((word, False))

    return result



# For standalone testing
if __name__ == "__main__":
    reference_text = "I am the Lorax and I speak for the trees"
    spoken_text = "I'm the Lorax I speak for trees"
    comparison = compare_transcript(
        spoken_text.split(), reference_text.split()
    )
    for word_feedback in comparison:
        word = word_feedback["word"]
        correct = word_feedback["correct"]
        print(f"{word}: {'✅' if correct else '❌'}")
