import unittest
from utils import longest_substring_overlap


class TestLongestSubstringOverlap(unittest.TestCase):

    def test_no_overlap(self):
        result = longest_substring_overlap("abc", "def", 2)
        self.assertEqual(result, (False, ""))

    def test_exact_match(self):
        result = longest_substring_overlap("abc", "abc", 2)
        self.assertEqual(result, (True, "abc"))

    def test_partial_overlap(self):
        result = longest_substring_overlap("abcdef", "defghi", 3)
        self.assertEqual(result, (True, "def"))

    def test_partial_overlap_below_threshold(self):
        result = longest_substring_overlap("abcdef", "defghi", 4)
        self.assertEqual(result, (False, "def"))

    def test_overlap_at_start(self):
        result = longest_substring_overlap("defghi", "abcdef", 3)
        self.assertEqual(result, (True, "def"))

    def test_overlap_at_start_below_threshold(self):
        result = longest_substring_overlap("defghi", "abcdef", 4)
        self.assertEqual(result, (False, "def"))

    def test_overlap_with_minimum_length(self):
        result = longest_substring_overlap("abc", "bc", 2)
        self.assertEqual(result, (True, "bc"))

    def test_overlap_with_minimum_length_not_met(self):
        result = longest_substring_overlap("abc", "bc", 3)
        self.assertEqual(result, (False, "bc"))

    def test_question_examples(self):
        question1 = "Predict home prices in 2024"
        question2 = "Predict home prices in 2024 for district 9"
        question3 = "Predict home prices in 2024 for district 11"
        result12 = longest_substring_overlap(
            question1, question2, len(question1) // 4 * 3
        )
        self.assertEqual(result12, (True, "Predict home prices in 2024"))
        result23 = longest_substring_overlap(
            question2, question3, len(question2) // 4 * 3
        )
        self.assertEqual(result23, (True, "Predict home prices in 2024 for district "))
