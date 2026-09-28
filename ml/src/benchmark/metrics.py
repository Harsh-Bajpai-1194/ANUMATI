"""
OCR Evaluation Metrics: Character Error Rate (CER) and Word Error Rate (WER).
Uses Levenshtein edit distance to measure transcription accuracy.
"""

from typing import List, Sequence, Tuple


def levenshtein_distance(seq1: Sequence, seq2: Sequence) -> int:
    """
    Computes Levenshtein edit distance (insertions, deletions, substitutions)
    between two sequences (strings or word lists).
    """
    len1, len2 = len(seq1), len(seq2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Current and previous row of distances
    previous_row = list(range(len2 + 1))
    current_row = [0] * (len2 + 1)

    for i in range(len1):
        current_row[0] = i + 1
        for j in range(len2):
            cost = 0 if seq1[i] == seq2[j] else 1
            current_row[j + 1] = min(
                current_row[j] + 1,       # Insertion
                previous_row[j + 1] + 1,   # Deletion
                previous_row[j] + cost     # Substitution
            )
        previous_row[:] = current_row[:]

    return current_row[len2]


def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Calculate Character Error Rate (CER) = Levenshtein(chars) / len(reference chars).
    Returns a float between 0.0 (perfect) and 1.0+ (poor).
    """
    ref_chars = list(reference.strip())
    hyp_chars = list(hypothesis.strip())

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    distance = levenshtein_distance(ref_chars, hyp_chars)
    return distance / len(ref_chars)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) = Levenshtein(words) / len(reference words).
    Returns a float between 0.0 (perfect) and 1.0+ (poor).
    """
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    distance = levenshtein_distance(ref_words, hyp_words)
    return distance / len(ref_words)


def calculate_accuracy(reference: str, hypothesis: str) -> float:
    """
    Returns percentage character accuracy: max(0.0, 1.0 - CER) * 100.
    """
    cer = calculate_cer(reference, hypothesis)
    return max(0.0, (1.0 - cer)) * 100.0