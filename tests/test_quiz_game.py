"""QuizGame의 상태·입력·종료 경계를 검증한다."""

import io
import json
import os
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main as application
import quiz_game
from quiz import Quiz
from quiz_game import QuizGame, StateAccessError, calculate_score


class StableRandom:
    def shuffle(self, values) -> None:
        return None


class QuizGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_path = Path(self.temporary_directory.name) / "state.json"
        self.messages = []
        self.errors = []

    def make_game(self, answers=()) -> QuizGame:
        answer_iterator = iter(answers)
        return QuizGame(
            state_path=self.state_path,
            input_fn=lambda _: next(answer_iterator),
            output_fn=self.messages.append,
            error_fn=self.errors.append,
            rng=StableRandom(),
        )

    def corrupt_backup_count(self) -> int:
        return len(
            list(self.state_path.parent.glob(".quiz-corrupt-*.bak"))
        )

    def test_runtime_state_artifacts_are_git_ignored(self) -> None:
        root = Path(__file__).resolve().parents[1]
        artifact_paths = (
            ".quiz-state-probe.tmp",
            "nested/.quiz-corrupt-probe.bak",
        )
        for artifact_path in artifact_paths:
            with self.subTest(path=artifact_path):
                completed = subprocess.run(
                    ["git", "check-ignore", "--quiet", artifact_path],
                    cwd=root,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0)

    def test_calculate_score_applies_penalty_and_floor(self) -> None:
        self.assertEqual(calculate_score(4, 5, 1), (80, 70))
        self.assertEqual(calculate_score(0, 2, 2), (0, 0))
        with self.assertRaises(ValueError):
            calculate_score(1, 0, 0)

    def test_missing_state_creates_five_default_quizzes(self) -> None:
        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertTrue(self.state_path.exists())
        self.assertIsNone(game.best_score)

    def test_missing_state_save_failure_stops_initialization(self) -> None:
        with patch.object(QuizGame, "save_state", return_value=False):
            with self.assertRaisesRegex(StateAccessError, "저장하지 못했습니다"):
                self.make_game()

    def test_falsy_error_callable_is_preserved(self) -> None:
        received = []

        class FalsyErrorSink:
            def __bool__(self) -> bool:
                return False

            def __call__(self, message: str) -> None:
                received.append(message)

        sink = FalsyErrorSink()
        game = QuizGame(
            state_path=self.state_path,
            output_fn=self.messages.append,
            error_fn=sink,
        )

        self.assertIs(game.error, sink)

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

    def test_save_io_error_detail_is_written_to_stderr(self) -> None:
        game = self.make_game()
        self.errors.clear()

        denied = PermissionError("denied")
        with patch("quiz_game.os.replace", side_effect=denied):
            self.assertFalse(game.save_state())

        self.assertTrue(any("denied" in item for item in self.errors))
        self.assertFalse(any("denied" in item for item in self.messages))

    def test_non_serializable_state_is_reported_as_save_failure(self) -> None:
        game = self.make_game()
        game.history = [{"invalid": object()}]
        self.errors.clear()

        self.assertFalse(game.save_state())

        self.assertTrue(any("저장하지 못했습니다" in item for item in self.errors))
        temporary_files = list(
            self.state_path.parent.glob(".quiz-state-*.tmp")
        )
        self.assertEqual(temporary_files, [])

    def test_failed_temporary_cleanup_reports_retained_path(self) -> None:
        game = self.make_game()
        self.errors.clear()
        with patch(
            "quiz_game.os.replace",
            side_effect=PermissionError("replace denied"),
        ), patch(
            "pathlib.Path.unlink",
            side_effect=PermissionError("cleanup denied"),
        ):
            self.assertFalse(game.save_state())

        self.assertTrue(any("임시 상태 파일" in item for item in self.errors))
        for path in self.state_path.parent.glob(".quiz-state-*.tmp"):
            path.unlink()

    def test_corrupt_state_is_backed_up_and_recovered(self) -> None:
        self.state_path.write_text("{not-json", encoding="utf-8")

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(self.corrupt_backup_count(), 1)
        json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_duplicate_json_keys_are_backed_up_as_corrupt(self) -> None:
        self.state_path.write_text(
            '{"quizzes":[{"question":"숨겨진 문제",'
            '"choices":["A","B","C","D"],"answer":1}],'
            '"quizzes":[],"best_score":null,"best_result":null,'
            '"history":[]}',
            encoding="utf-8",
        )

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(self.corrupt_backup_count(), 1)
        self.assertTrue(any("중복 JSON 키" in item for item in self.messages))

    def test_surrogate_quiz_text_is_backed_up_as_corrupt(self) -> None:
        self.state_path.write_text(
            '{"quizzes":[{"question":"\\ud800",'
            '"choices":["A","B","C","D"],"answer":1}],'
            '"best_score":null,"best_result":null,"history":[]}',
            encoding="utf-8",
        )

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(self.corrupt_backup_count(), 1)
        self.assertFalse(any("\ud800" in item for item in self.messages))

    def test_history_timestamp_cannot_inject_terminal_lines(self) -> None:
        game = self.make_game()
        game.best_score = 100
        game.best_result = {"correct": 1, "total": 1}
        game.history = [
            {
                "played_at": "2026-08-09\n00:00:00+00:00",
                "total": 1,
                "correct": 1,
                "score": 100,
                "hints_used": 0,
            }
        ]
        self.assertTrue(game.save_state())
        self.messages.clear()

        restored = self.make_game()

        self.assertEqual(len(restored.quizzes), 5)
        self.assertEqual(restored.history, [])
        self.assertEqual(self.corrupt_backup_count(), 1)

    def test_wrong_field_types_are_treated_as_corrupt_state(self) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "quizzes": [
                        {
                            "question": 123,
                            "choices": ["A", "B", "C", "D"],
                            "answer": 1,
                        }
                    ],
                    "best_score": None,
                    "best_result": None,
                    "history": [],
                }
            ),
            encoding="utf-8",
        )

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(self.corrupt_backup_count(), 1)

    def test_deeply_nested_json_is_backed_up_and_recovered(self) -> None:
        nested_json = "[" * 2000 + "0" + "]" * 2000
        self.state_path.write_text(nested_json, encoding="utf-8")

        game = self.make_game()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(self.corrupt_backup_count(), 1)

    def test_backup_failure_preserves_corrupt_source(self) -> None:
        corrupt_source = "{not-json"
        self.state_path.write_text(corrupt_source, encoding="utf-8")

        with patch(
            "quiz_game.open",
            side_effect=PermissionError("backup denied"),
        ):
            with self.assertRaises(StateAccessError):
                self.make_game()

        recovered = self.state_path.read_text(encoding="utf-8")
        self.assertEqual(recovered, corrupt_source)
        self.assertTrue(any("backup denied" in item for item in self.errors))

    def test_backup_name_collision_retries_without_overwrite(self) -> None:
        game = self.make_game()
        real_open = open
        attempts = 0

        def open_after_collision(*arguments, **keywords):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise FileExistsError("collision")
            return real_open(*arguments, **keywords)

        with patch("quiz_game.open", side_effect=open_after_collision):
            backup = game._backup_corrupt_state()

        self.assertIsNotNone(backup)
        self.assertEqual(attempts, 2)
        self.assertEqual(backup.read_bytes(), self.state_path.read_bytes())

    def test_backup_collisions_never_unlink_unowned_paths(self) -> None:
        game = self.make_game()
        with patch(
            "quiz_game.open",
            side_effect=FileExistsError("collision"),
        ), patch("pathlib.Path.unlink") as unlink:
            backup = game._backup_corrupt_state()

        self.assertIsNone(backup)
        unlink.assert_not_called()

    def test_interrupted_backup_removes_only_created_backup(self) -> None:
        game = self.make_game()
        with patch(
            "quiz_game.shutil.copyfileobj",
            side_effect=KeyboardInterrupt,
        ):
            with self.assertRaises(KeyboardInterrupt):
                game._backup_corrupt_state()

        backups = list(self.state_path.parent.glob(".quiz-corrupt-*.bak"))
        self.assertEqual(backups, [])

    def test_read_io_failure_does_not_replace_valid_source(self) -> None:
        source = '{"quizzes": []}'
        self.state_path.write_text(source, encoding="utf-8")

        with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
            with self.assertRaises(StateAccessError):
                self.make_game()

        self.assertEqual(self.state_path.read_text(encoding="utf-8"), source)

    def test_inconsistent_best_score_is_recovered_as_corrupt(self) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "quizzes": [],
                    "best_score": 90,
                    "best_result": None,
                    "history": [],
                }
            ),
            encoding="utf-8",
        )

        game = self.make_game()

        self.assertIsNone(game.best_score)
        self.assertEqual(self.corrupt_backup_count(), 1)

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

    def test_add_rejects_control_text_without_changing_state(self) -> None:
        game = self.make_game(
            [
                "질문\x1b]52;c;VEVTVA==\x07",
                "A",
                "B",
                "C",
                "D",
                "1",
                "힌트",
            ]
        )
        original_state = self.state_path.read_text(encoding="utf-8")

        game.add_quiz()

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(
            self.state_path.read_text(encoding="utf-8"),
            original_state,
        )
        self.assertTrue(any("제어 문자" in item for item in self.messages))
        self.assertFalse(any("\x1b" in item for item in self.messages))

    def test_add_rolls_back_when_save_fails(self) -> None:
        game = self.make_game(
            ["추가 문제", "보기1", "보기2", "보기3", "보기4", "3", "힌트"]
        )
        original_count = len(game.quizzes)
        game.save_state = lambda: False

        game.add_quiz()

        self.assertEqual(len(game.quizzes), original_count)
        self.assertTrue(any("추가를 취소" in message for message in self.messages))

    def test_delete_rolls_back_when_save_fails(self) -> None:
        game = self.make_game(["1"])
        original = list(game.quizzes)
        game.save_state = lambda: False

        game.delete_quiz()

        self.assertEqual(game.quizzes, original)
        self.assertTrue(any("삭제를 취소" in item for item in self.messages))

    def test_play_applies_hint_penalty_and_records_history(self) -> None:
        game = self.make_game(["1", "y", "1"])
        game.quizzes = [Quiz("정답은 1", ["A", "B", "C", "D"], 1, "A입니다")]

        game.play_quiz()

        self.assertEqual(game.best_score, 90)
        self.assertEqual(game.best_result, {"correct": 1, "total": 1})
        self.assertEqual(game.history[0]["score"], 90)
        self.assertEqual(game.history[0]["hints_used"], 1)
        self.assertTrue(game.history[0]["played_at"].endswith("Z"))

    def test_empty_hint_does_not_reduce_score_or_usage_count(self) -> None:
        game = self.make_game(["1", "y", "1"])
        game.quizzes = [Quiz("정답은 1", ["A", "B", "C", "D"], 1)]

        game.play_quiz()

        self.assertEqual(game.best_score, 100)
        self.assertEqual(game.history[0]["hints_used"], 0)
        self.assertTrue(any("감점 없음" in item for item in self.messages))

    def test_score_output_reports_only_applied_penalty_at_floor(self) -> None:
        game = self.make_game()
        self.messages.clear()

        game._show_result(2, 0, 0, 0, 2)

        penalty_message = self.messages[-1]
        self.assertIn("힌트 감점 0점", penalty_message)
        self.assertIn("요청 20점", penalty_message)
        self.assertIn("0점 하한", penalty_message)

    def test_play_rolls_back_score_when_save_fails(self) -> None:
        game = self.make_game(["1", "n", "1"])
        game.quizzes = [Quiz("정답은 1", ["A", "B", "C", "D"], 1)]
        game.save_state = lambda: False

        game.play_quiz()

        self.assertIsNone(game.best_score)
        self.assertIsNone(game.best_result)
        self.assertEqual(game.history, [])
        self.assertTrue(
            any("기록을 반영하지 않았습니다" in item for item in self.messages)
        )

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
            error_fn=self.errors.append,
        )

        with patch.object(game, "save_state", wraps=game.save_state) as save:
            result = game.run()

        self.assertEqual(result, 0)
        save.assert_called_once_with()
        self.assertTrue(self.state_path.exists())
        self.assertTrue(any("입력이 중단" in item for item in self.messages))

    def test_keyboard_interrupt_saves_and_exits(self) -> None:
        def raise_interrupt(_: str) -> str:
            raise KeyboardInterrupt

        game = QuizGame(
            state_path=self.state_path,
            input_fn=raise_interrupt,
            output_fn=self.messages.append,
            error_fn=self.errors.append,
        )

        with patch.object(game, "save_state", wraps=game.save_state) as save:
            self.assertEqual(game.run(), 0)

        save.assert_called_once_with()
        self.assertTrue(self.state_path.exists())
        self.assertEqual(self.errors, [])

    def test_interrupt_during_replace_removes_temporary_file(self) -> None:
        game = self.make_game(["6"])
        temporary_pattern = ".quiz-state-*.tmp"

        with patch(
            "quiz_game.os.replace",
            side_effect=[KeyboardInterrupt, None],
        ) as replace:
            result = game.run()

        self.assertEqual(result, 0)
        self.assertEqual(replace.call_count, 2)
        temporary_files = list(
            self.state_path.parent.glob(temporary_pattern)
        )
        self.assertEqual(temporary_files, [])

    def test_interrupt_during_temporary_open_removes_file(self) -> None:
        game = self.make_game(["6"])
        original_open = quiz_game._open_owner_only
        interrupted = False

        def interrupt_after_open(path):
            nonlocal interrupted
            temporary_file = original_open(path)
            if not interrupted:
                interrupted = True
                os.kill(os.getpid(), signal.SIGINT)
            return temporary_file

        with patch(
            "quiz_game._open_owner_only",
            side_effect=interrupt_after_open,
        ):
            result = game.run()

        self.assertEqual(result, 0)
        self.assertTrue(interrupted)
        self.assertEqual(list(self.state_path.parent.glob(".*.tmp")), [])

    def test_preopen_interrupt_does_not_delete_collision(self) -> None:
        game = self.make_game()
        collision = self.state_path.with_name(".quiz-state-fixed.tmp")
        collision.write_text("foreign", encoding="utf-8")

        with patch(
            "quiz_game.secrets.token_hex",
            return_value="fixed",
        ), patch(
            "quiz_game._open_owner_only",
            side_effect=KeyboardInterrupt,
        ):
            with self.assertRaises(KeyboardInterrupt):
                game.save_state()

        self.assertEqual(collision.read_text(encoding="utf-8"), "foreign")

    def test_temporary_collision_retries_without_deleting_owner(self) -> None:
        game = self.make_game()
        collision = self.state_path.with_name(".quiz-state-fixed.tmp")
        collision.write_text("foreign", encoding="utf-8")

        with patch(
            "quiz_game.secrets.token_hex",
            side_effect=["fixed", "fresh"],
        ):
            self.assertTrue(game.save_state())

        self.assertEqual(collision.read_text(encoding="utf-8"), "foreign")

    def test_saved_state_is_owner_only_even_with_open_umask(self) -> None:
        game = self.make_game()
        previous_umask = os.umask(0)
        try:
            self.assertTrue(game.save_state())
        finally:
            os.umask(previous_umask)

        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o600)

    def test_long_state_basename_still_saves(self) -> None:
        long_path = self.state_path.with_name("s" * 220)

        QuizGame(
            state_path=long_path,
            input_fn=lambda _: "6",
            output_fn=self.messages.append,
            error_fn=self.errors.append,
        )

        self.assertTrue(long_path.exists())

    def test_long_corrupt_state_basename_can_be_recovered(self) -> None:
        long_path = self.state_path.with_name("s" * 221)
        long_path.write_text("{not-json", encoding="utf-8")

        game = QuizGame(
            state_path=long_path,
            output_fn=self.messages.append,
            error_fn=self.errors.append,
        )

        self.assertEqual(len(game.quizzes), 5)
        self.assertEqual(
            len(list(long_path.parent.glob(".quiz-corrupt-*.bak"))),
            1,
        )
        json.loads(long_path.read_text(encoding="utf-8"))

    def test_surrogateescape_basename_can_build_backup_path(self) -> None:
        raw_name = b"state-\xff.json"
        game = self.make_game()
        game.state_path = self.state_path.with_name(os.fsdecode(raw_name))

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.open",
            return_value=io.BytesIO(b"corrupt"),
        ):
            backup = game._backup_corrupt_state()

        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_bytes(), b"corrupt")

    def test_interrupted_exit_save_failure_returns_one_on_stderr(self) -> None:
        def raise_eof(_: str) -> str:
            raise EOFError

        game = self.make_game()
        game.input = raise_eof
        game.save_state = lambda: False

        self.assertEqual(game.run(), 1)
        self.assertTrue(any("저장하지 못했습니다" in item for item in self.errors))

    def test_safe_exit_reports_save_failure(self) -> None:
        game = self.make_game()
        game.save_state = lambda: False

        self.assertFalse(game.safe_exit())
        self.assertTrue(any("저장하지 못했습니다" in item for item in self.errors))

    def test_default_state_path_is_stable_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as external_directory:
            original_directory = Path.cwd()
            try:
                os.chdir(external_directory)
                with patch.dict(os.environ, {}, clear=True), patch(
                    "main.QuizGame"
                ) as game_class:
                    game_class.return_value.run.return_value = 0
                    result = application.main()
            finally:
                os.chdir(original_directory)

        self.assertEqual(result, 0)
        game_class.assert_called_once_with(
            state_path=application.DEFAULT_STATE_PATH
        )

    def test_fatal_state_error_is_written_to_stderr(self) -> None:
        standard_output = io.StringIO()
        standard_error = io.StringIO()
        with patch(
            "main.QuizGame",
            side_effect=StateAccessError("읽기 실패"),
        ), patch("sys.stdout", standard_output), patch(
            "sys.stderr",
            standard_error,
        ):
            result = application.main()

        self.assertEqual(result, 1)
        self.assertEqual(standard_output.getvalue(), "")
        self.assertIn("읽기 실패", standard_error.getvalue())

    def test_startup_interrupt_fails_without_state(self) -> None:
        captured_error = io.StringIO()
        with patch.object(
            application,
            "resolve_state_path",
            return_value=self.state_path,
        ), patch.object(
            QuizGame,
            "save_state",
            side_effect=KeyboardInterrupt,
        ), patch("sys.stderr", captured_error):
            result = application.main()

        self.assertEqual(result, 1)
        self.assertFalse(self.state_path.exists())
        self.assertIn("저장을 확인하지 못했습니다", captured_error.getvalue())


if __name__ == "__main__":
    unittest.main()
