"""Quiz 모델의 검증과 직렬화 동작을 검사한다."""

import unittest

from quiz import Quiz


class QuizTest(unittest.TestCase):
    def test_round_trip_and_answer_check(self) -> None:
        quiz = Quiz(" 질문? ", [" A ", "B", "C", "D"], 2, " 힌트 ")

        restored = Quiz.from_dict(quiz.to_dict())

        self.assertEqual(restored.question, "질문?")
        self.assertEqual(restored.choices[0], "A")
        self.assertEqual(restored.hint, "힌트")
        self.assertTrue(restored.is_correct(2))
        self.assertFalse(restored.is_correct(1))

    def test_rejects_invalid_question_choices_and_answer(self) -> None:
        valid_choices = ["A", "B", "C", "D"]
        with self.assertRaises(ValueError):
            Quiz("", valid_choices, 1)
        with self.assertRaises(ValueError):
            Quiz("질문", ["A", "B"], 1)
        with self.assertRaises(ValueError):
            Quiz("질문", valid_choices, 0)
        with self.assertRaises(ValueError):
            Quiz("질문", valid_choices, True)
        with self.assertRaises(ValueError):
            Quiz.from_dict(
                {"question": 123, "choices": valid_choices, "answer": 1}
            )
        with self.assertRaises(ValueError):
            Quiz.from_dict(
                {"question": "질문", "choices": [1, 2, 3, 4], "answer": 1}
            )

    def test_rejects_terminal_control_characters(self) -> None:
        valid_choices = ["A", "B", "C", "D"]
        unsafe_values = (
            ("질문\x1b]52;c;VEVTVA==\x07", valid_choices, "힌트"),
            ("질문", ["A", "B\n위조", "C", "D"], "힌트"),
            ("질문", valid_choices, "힌트\t위조"),
            ("질문\ud800", valid_choices, "힌트"),
        )
        for question, choices, hint in unsafe_values:
            with self.subTest(value=(question, choices, hint)):
                with self.assertRaisesRegex(ValueError, "제어 문자"):
                    Quiz(question, choices, 1, hint)

    def test_display_lines_contains_numbered_choices(self) -> None:
        quiz = Quiz("질문", ["A", "B", "C", "D"], 1)
        self.assertEqual(
            quiz.display_lines(3),
            ["[문제 3] 질문", "1. A", "2. B", "3. C", "4. D"],
        )


if __name__ == "__main__":
    unittest.main()
