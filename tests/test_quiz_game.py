import json
import tempfile
import unittest
from pathlib import Path

from quiz import Quiz
from quiz_game import QuizGame


class StableRandom:
    def shuffle(self, values) -> None:
        return None


class QuizGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_path = Path(self.temporary_directory.name) / "state.json"
        self.messages = []

    def make_game(self, answers=()) -> QuizGame:
        answer_iterator = iter(answers)
        return QuizGame(
            state_path=self.state_path,
            input_fn=lambda _: next(answer_iterator),
            output_fn=self.messages.append,
            rng=StableRandom(),
        )

    def test_missing_state_creates_five_default_quizzes(self) -> None:
        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertTrue(self.state_path.exists())
        self.assertIsNone(game.best_score)

    def test_save_and_reload_preserves_quizzes_and_score(self) -> None:
        game = self.make_game()
        game.quizzes.append(Quiz("새 문제", ["1", "2", "3", "4"], 4, "힌트"))
        game.best_score = 80
        game.best_result = {"correct": 4, "total": 5}
        game.history = [
            {
                "played_at": "2026-08-09T00:00:00Z",
                "total": 5,
                "correct": 4,
                "score": 80,
                "hints_used": 0,
            }
        ]
        self.assertTrue(game.save_state())

        restored = self.make_game()

        self.assertEqual(len(restored.quizzes), 6)
        self.assertEqual(restored.best_score, 80)
        self.assertEqual(len(restored.history), 1)

    def test_corrupt_state_is_backed_up_and_recovered(self) -> None:
        self.state_path.write_text("{not-json", encoding="utf-8")

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        backups = list(self.state_path.parent.glob("state.json.corrupt-*.bak"))
        self.assertEqual(len(backups), 1)
        json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_read_int_retries_blank_text_and_out_of_range(self) -> None:
        game = self.make_game(["", "abc", "9", " 2 "])

        result = game.read_int("선택: ", 1, 4)

        self.assertEqual(result, 2)
        self.assertEqual(sum("⚠️" in message for message in self.messages), 3)

    def test_add_list_and_delete_quiz_are_persisted(self) -> None:
        game = self.make_game(
            ["추가 문제", "보기1", "보기2", "보기3", "보기4", "3", "추가 힌트", "6"]
        )

        game.add_quiz()
        game.list_quizzes()
        game.delete_quiz()

        restored = self.make_game()
        self.assertEqual(len(restored.quizzes), 5)
        self.assertTrue(any("추가 문제" in message for message in self.messages))

    def test_play_applies_hint_penalty_and_records_history(self) -> None:
        game = self.make_game(["1", "y", "1"])
        game.quizzes = [Quiz("정답은 1", ["A", "B", "C", "D"], 1, "A입니다")]

        game.play_quiz()

        self.assertEqual(game.best_score, 90)
        self.assertEqual(game.best_result, {"correct": 1, "total": 1})
        self.assertEqual(game.history[0]["score"], 90)
        self.assertEqual(game.history[0]["hints_used"], 1)
        self.assertTrue(game.history[0]["played_at"].endswith("Z"))

    def test_play_and_score_handle_empty_or_unplayed_state(self) -> None:
        game = self.make_game()
        game.quizzes = []

        game.play_quiz()
        game.show_score()

        self.assertTrue(any("등록된 퀴즈가 없습니다" in item for item in self.messages))
        self.assertTrue(any("플레이 기록이 없습니다" in item for item in self.messages))

    def test_eof_saves_and_exits_without_traceback(self) -> None:
        def raise_eof(_: str) -> str:
            raise EOFError

        game = QuizGame(
            state_path=self.state_path,
            input_fn=raise_eof,
            output_fn=self.messages.append,
        )

        game.run()

        self.assertTrue(self.state_path.exists())
        self.assertTrue(any("입력이 중단" in item for item in self.messages))


if __name__ == "__main__":
    unittest.main()
