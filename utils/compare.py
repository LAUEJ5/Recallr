from metaphone import doublemetaphone
from fuzzywuzzy import fuzz
from typing import List, Tuple
import string


def compare_transcript(transcript_words: List[str], reference_words: List[str]) -> List[Tuple[str, bool]]:
    matched_indices = set()
    ref_index = 0
    result = []

    for t_word in transcript_words:
        best_score = 0
        best_match_index = None
        phonetic_score = 0

        t_clean = t_word.strip(string.punctuation)

        for i in range(ref_index, min(len(reference_words), ref_index + 4)):
            r_word = reference_words[i]
            r_clean = r_word.strip(string.punctuation)

            fuzzy_score = fuzz.partial_ratio(t_clean.lower(), r_clean.lower())
            t_meta = doublemetaphone(t_clean)[0]
            r_meta = doublemetaphone(r_clean)[0]
            phonetic_score = fuzz.ratio(t_meta, r_meta)

            print(f"🔎 Comparing '{t_word}' to ref[{i}] = '{r_word}'")
            print(f"🧠 Metaphone: {t_meta} vs {r_meta}")
            print(f"🎯 Fuzzy: {fuzzy_score}, Phonetic: {phonetic_score}")

            combined_score = (fuzzy_score + phonetic_score) / 2
            if combined_score > best_score and i not in matched_indices:
                best_score = combined_score
                best_match_index = i

        is_correct = False
        if (best_score >= 85 or (phonetic_score >= 80 and len(t_clean) > 5)) and best_match_index is not None:
            print(f"✅ Matched '{t_word}' to ref[{best_match_index}] = '{reference_words[best_match_index]}'")
            matched_indices.add(best_match_index)
            is_correct = True

            if best_match_index == ref_index:
                ref_index += 1
            elif best_match_index > ref_index:
                ref_index = best_match_index + 1
        else:
            print(f"❌ No match for '{t_word}'")

        result.append((t_word, is_correct))  # ✅ Use transcript word here

    return result
