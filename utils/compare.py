from metaphone import doublemetaphone
from fuzzywuzzy import fuzz
from typing import List, Tuple
import string
import re

def clean_word(word: str) -> str:
    return re.sub(r"[^\w\s]", "", word).lower()

def compare_transcript(transcript_words: List[str], reference_words: List[str], verbose: bool = False) -> List[Tuple[str, bool]]:
    matched_indices = set()
    ref_index = 0
    result = []

    for t_word in transcript_words:
        if ref_index >= len(reference_words):
            if verbose:
                print(f"⚠️ Ref index {ref_index} out of bounds for reference length {len(reference_words)}")
            break

        t_clean = t_word.strip(string.punctuation).lower()
        best_score = 0
        best_match_index = None
        best_phonetic_score = 0
        best_phonetic_index = None

        window = range(ref_index, min(len(reference_words), ref_index + 4))

        for i in window:
            r_word = reference_words[i]
            r_clean = r_word.strip(string.punctuation).lower()

            fuzzy_score = fuzz.partial_ratio(t_clean, r_clean)
            t_meta = doublemetaphone(t_clean)[0]
            r_meta = doublemetaphone(r_clean)[0]
            phonetic_score = fuzz.ratio(t_meta, r_meta)

            if verbose:
                print(f"🔎 '{t_word}' vs ref[{i}] = '{r_word}' | 🧠 Metaphone: {t_meta} vs {r_meta} | 🎯 Fuzzy: {fuzzy_score}, Phonetic: {phonetic_score}")

            combined_score = (fuzzy_score + phonetic_score) / 2

            if combined_score > best_score and i not in matched_indices:
                best_score = combined_score
                best_match_index = i

            if phonetic_score > best_phonetic_score and i not in matched_indices:
                best_phonetic_score = phonetic_score
                best_phonetic_index = i

        # Handle short word fallback first
        if len(t_clean) <= 2 and ref_index < len(reference_words):
            ref_word_clean = reference_words[ref_index].strip(string.punctuation).lower()
            if fuzz.partial_ratio(t_clean, ref_word_clean) >= 95:
                matched_indices.add(ref_index)
                result.append((t_word, True))
                if verbose:
                    print(f"🎯 Word: '{t_word}' (short) → ✅ Fallback match to '{reference_words[ref_index]}' [ref {ref_index}] → ref_index = {ref_index + 1}")
                ref_index += 1
                continue

        # Primary match logic
        is_correct = False
        match_idx = None

        if best_score >= 85 and best_match_index is not None:
            match_idx = best_match_index
            is_correct = True
        elif best_phonetic_score >= 80 and best_phonetic_index is not None and len(t_clean) > 5:
            match_idx = best_phonetic_index
            is_correct = True

        if is_correct and match_idx is not None:
            matched_indices.add(match_idx)
            if match_idx >= ref_index:
                ref_index = match_idx + 1
            if verbose:
                print(f"🎯 Word: '{t_word}' → ✅ Matched to '{reference_words[match_idx]}' [ref {match_idx}] → ref_index = {ref_index}")
        else:
            if verbose:
                print(f"🎯 Word: '{t_word}' → ❌ No match [ref_index = {ref_index}]")

        result.append((t_word, is_correct))

    return result