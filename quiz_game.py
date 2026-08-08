"""퀴즈 게임의 상태, 입력, 기능 흐름을 관리한다."""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from default_quizzes import create_default_quizzes
from quiz import Quiz


class StateAccessError(RuntimeError):
    """원본 상태를 안전하게 읽거나 보존할 수 없을 때 발생한다."""


def _stderr_output(message: str) -> None:
    """치명적 진단을 표준 오류로 출력한다."""
    print(message, file=sys.stderr)


def calculate_score(
    correct: int,
    total: int,
    hints_used: int,
) -> tuple[int, int]:
    """정답과 유효한 힌트 수로 기본 점수와 최종 점수를 계산한다."""
    values = (correct, total, hints_used)
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in values
    ):
        raise ValueError("점수 계산 값은 정수여야 합니다.")
    if total < 1 or correct < 0 or correct > total:
        raise ValueError("전체 문제 수와 정답 수가 유효하지 않습니다.")
    if hints_used < 0 or hints_used > total:
        raise ValueError("힌트 사용 수가 유효하지 않습니다.")
    base_score = round(correct / total * 100)
    return base_score, max(0, base_score - hints_used * 10)


class QuizGame:
    """퀴즈 목록과 점수를 불러오고 저장하는 게임 관리자."""

    def __init__(
        self,
        state_path: str | Path = "state.json",
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
        error_fn: Optional[Callable[[str], None]] = None,
        rng: random.Random | Any = random,
    ) -> None:
        """저장 경로와 교체 가능한 입출력·난수 함수를 설정한다."""
        self.state_path = Path(state_path)
        self.input = input_fn
        self.output = output_fn
        self.error = error_fn or _stderr_output
        self.rng = rng
        self.quizzes: List[Quiz] = []
        self.best_score: Optional[int] = None
        self.best_result: Optional[Dict[str, int]] = None
        self.history: List[Dict[str, Any]] = []
        self.load_state()

    def reset_to_defaults(self) -> None:
        """메모리 상태를 기본 퀴즈와 빈 점수로 초기화한다."""
        self.quizzes = create_default_quizzes()
        self.best_score = None
        self.best_result = None
        self.history = []

    def load_state(self) -> None:
        """JSON 상태를 읽고, 없거나 손상되었으면 안전하게 복구한다."""
        if not self.state_path.exists():
            self.output("📂 저장 파일이 없어 기본 퀴즈로 시작합니다.")
            self.reset_to_defaults()
            self.save_state()
            return

        try:
            with self.state_path.open("r", encoding="utf-8") as state_file:
                data = json.load(state_file)
            self._apply_state(data)
        except OSError as error:
            raise StateAccessError(
                f"저장 파일을 읽지 못해 원본을 그대로 보존합니다: {error}"
            ) from error
        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            backup = self._backup_corrupt_state()
            if backup is None:
                raise StateAccessError(
                    "손상된 저장 파일의 백업을 만들지 못해 원본을 그대로 보존합니다."
                ) from error
            self.output(
                "⚠️ 저장 파일을 읽을 수 없어 기본값으로 복구합니다. "
                f"백업: {backup.name}"
            )
            self.output(f"   원인: {error}")
            self.reset_to_defaults()
            if not self.save_state():
                raise StateAccessError(
                    "손상 상태를 백업했지만 기본 상태 파일을 저장하지 못했습니다."
                )
            return

        score_text = (
            "기록 없음"
            if self.best_score is None
            else f"{self.best_score}점"
        )
        self.output(
            f"📂 저장된 데이터를 불러왔습니다. "
            f"(퀴즈 {len(self.quizzes)}개, 최고 점수 {score_text})"
        )

    def _apply_state(self, data: Any) -> None:
        if not isinstance(data, dict):
            raise ValueError("최상위 데이터는 객체여야 합니다.")

        raw_quizzes = data.get("quizzes")
        if not isinstance(raw_quizzes, list):
            raise ValueError("quizzes는 배열이어야 합니다.")
        quizzes = [Quiz.from_dict(item) for item in raw_quizzes]

        best_score = data.get("best_score")
        if best_score is not None and (
            isinstance(best_score, bool)
            or not isinstance(best_score, int)
            or not 0 <= best_score <= 100
        ):
            raise ValueError("best_score는 null 또는 0~100 정수여야 합니다.")

        best_result = data.get("best_result")
        if best_result is not None:
            self._validate_result(best_result)

        history = data.get("history", [])
        if not isinstance(history, list):
            raise ValueError("history는 배열이어야 합니다.")
        for record in history:
            self._validate_history_record(record)

        self._validate_score_history(best_score, best_result, history)

        self.quizzes = quizzes
        self.best_score = best_score
        self.best_result = best_result
        self.history = history

    @staticmethod
    def _validate_score_history(
        best_score: Any,
        best_result: Any,
        history: List[Dict[str, Any]],
    ) -> None:
        """최고 점수와 전체 플레이 기록의 교차 필드를 검증한다."""
        if (best_score is None) != (best_result is None):
            raise ValueError(
                "best_score와 best_result는 함께 존재하거나 함께 비어야 합니다."
            )
        if history and best_score is None:
            raise ValueError("플레이 기록이 있으면 최고 점수도 있어야 합니다.")
        if best_score is not None and best_result is not None:
            if not history:
                raise ValueError("최고 점수가 플레이 기록과 일치하지 않습니다.")
            history_best = max(record["score"] for record in history)
            if best_score != history_best:
                raise ValueError("최고 점수가 플레이 기록과 일치하지 않습니다.")
            if not any(
                record["score"] == best_score
                and record["correct"] == best_result["correct"]
                and record["total"] == best_result["total"]
                for record in history
            ):
                raise ValueError("최고 점수의 정답 기록이 history에 없습니다.")

    @staticmethod
    def _validate_result(result: Any) -> None:
        if not isinstance(result, dict):
            raise ValueError("best_result는 객체여야 합니다.")
        correct = result.get("correct")
        total = result.get("total")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (correct, total)
        ):
            raise ValueError("best_result의 값은 정수여야 합니다.")
        if total < 1 or correct < 0 or correct > total:
            raise ValueError("best_result의 정답 수가 유효하지 않습니다.")

    @classmethod
    def _validate_history_record(cls, record: Any) -> None:
        if not isinstance(record, dict) or not isinstance(
            record.get("played_at"),
            str,
        ):
            raise ValueError("history 항목 형식이 올바르지 않습니다.")
        timestamp = record["played_at"]
        normalized_timestamp = (
            timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
        )
        try:
            parsed_timestamp = datetime.fromisoformat(normalized_timestamp)
        except ValueError as error:
            raise ValueError(
                "history의 played_at은 ISO 8601 시각이어야 합니다."
            ) from error
        if parsed_timestamp.tzinfo is None:
            raise ValueError("history의 played_at에는 시간대가 있어야 합니다.")
        cls._validate_result(record)
        score = record.get("score")
        hints_used = record.get("hints_used", 0)
        if (
            isinstance(score, bool)
            or not isinstance(score, int)
            or not 0 <= score <= 100
            or isinstance(hints_used, bool)
            or not isinstance(hints_used, int)
            or hints_used < 0
            or hints_used > record["total"]
        ):
            raise ValueError("history의 점수 또는 힌트 수가 유효하지 않습니다.")
        _, expected_score = calculate_score(
            record["correct"],
            record["total"],
            hints_used,
        )
        if score != expected_score:
            raise ValueError("history의 점수가 정답 수와 힌트 감점에 맞지 않습니다.")

    def state_dict(self) -> Dict[str, Any]:
        """현재 상태를 JSON 직렬화 가능한 딕셔너리로 반환한다."""
        return {
            "quizzes": [quiz.to_dict() for quiz in self.quizzes],
            "best_score": self.best_score,
            "best_result": self.best_result,
            "history": self.history,
        }

    def save_state(self) -> bool:
        """같은 디렉터리의 임시 파일을 원자적으로 교체한다."""
        temporary_name: Optional[str] = None
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.state_path.parent,
                prefix=f".{self.state_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_name = temporary_file.name
                json.dump(
                    self.state_dict(),
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, self.state_path)
            return True
        except OSError as error:
            self.error(f"⚠️ 상태를 저장하지 못했습니다: {error}")
            if temporary_name:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass
            return False

    def _backup_corrupt_state(self) -> Optional[Path]:
        if not self.state_path.exists():
            return None
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = self.state_path.with_name(
            f"{self.state_path.name}.corrupt-{timestamp}.bak"
        )
        try:
            shutil.copy2(self.state_path, backup)
            return backup
        except OSError:
            return None

    def read_int(self, prompt: str, minimum: int, maximum: int) -> int:
        """공백·문자·범위 오류를 안내하고 올바른 정수를 다시 받는다."""
        while True:
            raw_value = self.input(prompt).strip()
            if not raw_value:
                self.output(f"⚠️ 값을 입력하세요. ({minimum}~{maximum})")
                continue
            try:
                value = int(raw_value)
            except ValueError:
                self.output(f"⚠️ 숫자로 입력하세요. ({minimum}~{maximum})")
                continue
            if minimum <= value <= maximum:
                return value
            self.output(f"⚠️ {minimum}부터 {maximum} 사이의 숫자를 입력하세요.")

    def play_quiz(self) -> None:
        """문제 수를 선택해 무작위로 풀고 힌트 감점을 반영한다."""
        if not self.quizzes:
            self.output("⚠️ 등록된 퀴즈가 없습니다. 먼저 퀴즈를 추가해 주세요.")
            return

        selected = self._select_quizzes()
        correct, hints_used = self._play_selected(selected)
        total = len(selected)
        base_score, score = calculate_score(correct, total, hints_used)
        self._show_result(total, correct, base_score, score, hints_used)
        record = self._history_record(total, correct, score, hints_used)
        self._persist_result(record)

    def _select_quizzes(self) -> List[Quiz]:
        """사용자가 고른 수만큼 무작위 문제를 선택한다."""
        count = self.read_int(
            f"풀 문제 수 (1~{len(self.quizzes)}): ",
            1,
            len(self.quizzes),
        )
        selected = list(self.quizzes)
        self.rng.shuffle(selected)
        return selected[:count]

    def _play_selected(self, selected: List[Quiz]) -> tuple[int, int]:
        """선택된 문제를 풀고 정답·유효 힌트 수를 반환한다."""
        correct = 0
        hints_used = 0
        self.output(f"\n📝 퀴즈를 시작합니다. (총 {len(selected)}문제)")
        for number, quiz in enumerate(selected, start=1):
            is_correct, used_hint = self._play_question(number, quiz)
            correct += int(is_correct)
            hints_used += int(used_hint)
        return correct, hints_used

    def _play_question(self, number: int, quiz: Quiz) -> tuple[bool, bool]:
        """문제 하나를 출력하고 정답·유효 힌트 여부를 반환한다."""
        self.output("\n" + "-" * 42)
        for line in quiz.display_lines(number):
            self.output(line)
        used_hint = self._offer_hint(quiz)
        answer = self.read_int("정답 입력 (1~4): ", 1, 4)
        is_correct = quiz.is_correct(answer)
        if is_correct:
            self.output("✅ 정답입니다!")
        else:
            self.output(f"❌ 오답입니다. 정답은 {quiz.answer}번입니다.")
        return is_correct, used_hint

    def _offer_hint(self, quiz: Quiz) -> bool:
        """실제 힌트를 보여 준 경우에만 감점 여부를 반환한다."""
        if not self.read_yes_no("힌트를 볼까요? (y/N): "):
            return False
        if not quiz.hint:
            self.output("💡 등록된 힌트가 없습니다. (감점 없음)")
            return False
        self.output(f"💡 힌트: {quiz.hint} (-10점)")
        return True

    def _show_result(
        self,
        total: int,
        correct: int,
        base_score: int,
        score: int,
        hints_used: int,
    ) -> None:
        """점수와 힌트 감점 내역을 출력한다."""
        self.output("\n" + "=" * 42)
        self.output(f"🏆 결과: {total}문제 중 {correct}문제 정답 ({score}점)")
        if hints_used:
            penalty = hints_used * 10
            self.output(f"   기본 {base_score}점 - 힌트 감점 {penalty}점")

    @staticmethod
    def _history_record(
        total: int,
        correct: int,
        score: int,
        hints_used: int,
    ) -> Dict[str, Any]:
        """현재 플레이 결과를 ISO 8601 기록으로 만든다."""
        played_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        return {
            "played_at": played_at,
            "total": total,
            "correct": correct,
            "score": score,
            "hints_used": hints_used,
        }

    def _persist_result(self, record: Dict[str, Any]) -> None:
        """점수와 기록을 함께 저장하고 실패하면 메모리를 되돌린다."""
        score = record["score"]
        total = record["total"]
        correct = record["correct"]

        previous_best_score = self.best_score
        previous_best_result = (
            None if self.best_result is None else dict(self.best_result)
        )
        previous_history_length = len(self.history)
        is_new_best = self.best_score is None or score > self.best_score
        if is_new_best:
            self.best_score = score
            self.best_result = {"correct": correct, "total": total}
        self.history.append(record)
        if self.save_state():
            if is_new_best:
                self.output("🎉 새로운 최고 점수입니다!")
        else:
            self.best_score = previous_best_score
            self.best_result = previous_best_result
            del self.history[previous_history_length:]
            self.output("⚠️ 저장에 실패해 이번 점수와 기록을 반영하지 않았습니다.")

    def read_yes_no(self, prompt: str) -> bool:
        """빈 입력은 아니요로 처리하고 y/n만 다시 받는다."""
        while True:
            answer = self.input(prompt).strip().lower()
            if answer in ("", "n", "no"):
                return False
            if answer in ("y", "yes"):
                return True
            self.output("⚠️ y 또는 n으로 입력하세요.")

    def read_nonempty(self, prompt: str) -> str:
        """공백이 아닌 문자열을 입력받을 때까지 반복한다."""
        while True:
            value = self.input(prompt).strip()
            if value:
                return value
            self.output("⚠️ 빈 값은 입력할 수 없습니다.")

    def add_quiz(self) -> None:
        """문제와 선택지를 입력받아 즉시 상태 파일에 추가한다."""
        self.output("\n📌 새로운 퀴즈를 추가합니다.")
        question = self.read_nonempty("문제: ")
        choices = [
            self.read_nonempty(f"선택지 {number}: ") for number in range(1, 5)
        ]
        answer = self.read_int("정답 번호 (1~4): ", 1, 4)
        hint = self.input("힌트 (생략 가능): ").strip()
        self.quizzes.append(Quiz(question, choices, answer, hint))
        if self.save_state():
            self.output("✅ 퀴즈가 추가되고 저장되었습니다.")
        else:
            self.quizzes.pop()
            self.output("⚠️ 저장에 실패해 퀴즈 추가를 취소했습니다.")

    def list_quizzes(self) -> None:
        """정답을 노출하지 않고 등록된 문제 제목을 보여 준다."""
        if not self.quizzes:
            self.output("⚠️ 등록된 퀴즈가 없습니다.")
            return
        self.output(f"\n📋 등록된 퀴즈 목록 (총 {len(self.quizzes)}개)")
        for number, quiz in enumerate(self.quizzes, start=1):
            self.output(f"{number}. {quiz.question}")

    def delete_quiz(self) -> None:
        """선택한 문제를 삭제하고 성공 여부를 즉시 저장한다."""
        if not self.quizzes:
            self.output("⚠️ 삭제할 퀴즈가 없습니다.")
            return
        self.list_quizzes()
        number = self.read_int("삭제할 문제 번호: ", 1, len(self.quizzes))
        deleted = self.quizzes.pop(number - 1)
        if self.save_state():
            self.output(f"🗑️ '{deleted.question}' 퀴즈를 삭제했습니다.")
        else:
            self.quizzes.insert(number - 1, deleted)
            self.output("⚠️ 저장에 실패해 삭제를 취소했습니다.")

    def show_score(self) -> None:
        """최고 점수와 ISO 시각이 포함된 전체 플레이 기록을 출력한다."""
        if self.best_score is None or self.best_result is None:
            self.output("🏆 아직 플레이 기록이 없습니다.")
            return

        self.output(
            f"\n🏆 최고 점수: {self.best_score}점 "
            f"({self.best_result['total']}문제 중 "
            f"{self.best_result['correct']}문제 정답)"
        )
        self.output(f"📚 플레이 기록 (총 {len(self.history)}회)")
        for number, record in enumerate(self.history, start=1):
            self.output(
                f"{number}. {record['played_at']} | "
                f"{record['correct']}/{record['total']} 정답 | "
                f"{record['score']}점 | 힌트 {record.get('hints_used', 0)}회"
            )

    def show_menu(self) -> None:
        """현재 선택 가능한 여섯 가지 메뉴를 출력한다."""
        self.output("\n" + "=" * 42)
        self.output("          Python 기초 퀴즈")
        self.output("=" * 42)
        self.output("1. 퀴즈 풀기")
        self.output("2. 퀴즈 추가")
        self.output("3. 퀴즈 목록")
        self.output("4. 점수 확인")
        self.output("5. 퀴즈 삭제")
        self.output("6. 종료")
        self.output("=" * 42)

    def run(self) -> int:
        """메뉴를 반복하고 EOF/Ctrl+C에서도 저장한 뒤 정상 종료한다."""
        try:
            while True:
                self.show_menu()
                menu = self.read_int("선택: ", 1, 6)
                if menu == 1:
                    self.play_quiz()
                elif menu == 2:
                    self.add_quiz()
                elif menu == 3:
                    self.list_quizzes()
                elif menu == 4:
                    self.show_score()
                elif menu == 5:
                    self.delete_quiz()
                else:
                    return 0 if self.safe_exit() else 1
        except (EOFError, KeyboardInterrupt):
            self.output("\n⚠️ 입력이 중단되었습니다. 현재 상태를 저장합니다.")
            return 0 if self.safe_exit() else 1

    def safe_exit(self) -> bool:
        """현재 상태를 저장하고 성공 여부를 알린다."""
        saved = self.save_state()
        if saved:
            self.output("💾 상태를 저장했습니다.")
        else:
            self.error("⚠️ 상태를 저장하지 못했습니다.")
        self.output("퀴즈 게임을 종료합니다.")
        return saved
