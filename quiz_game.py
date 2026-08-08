"""퀴즈 게임의 상태, 입력, 기능 흐름을 관리한다."""

from __future__ import annotations

import json
import os
import random
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from default_quizzes import create_default_quizzes
from quiz import Quiz


class QuizGame:
    """퀴즈 목록과 점수를 불러오고 저장하는 게임 관리자."""

    def __init__(
        self,
        state_path: str | Path = "state.json",
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
        rng: random.Random | Any = random,
    ) -> None:
        self.state_path = Path(state_path)
        self.input = input_fn
        self.output = output_fn
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
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            backup = self._backup_corrupt_state()
            backup_message = f" 백업: {backup.name}" if backup else ""
            self.output(f"⚠️ 저장 파일을 읽을 수 없어 기본값으로 복구합니다.{backup_message}")
            self.output(f"   원인: {error}")
            self.reset_to_defaults()
            self.save_state()
            return

        score_text = "기록 없음" if self.best_score is None else f"{self.best_score}점"
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

        self.quizzes = quizzes
        self.best_score = best_score
        self.best_result = best_result
        self.history = history

    @staticmethod
    def _validate_result(result: Any) -> None:
        if not isinstance(result, dict):
            raise ValueError("best_result는 객체여야 합니다.")
        correct = result.get("correct")
        total = result.get("total")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (correct, total)):
            raise ValueError("best_result의 값은 정수여야 합니다.")
        if total < 0 or correct < 0 or correct > total:
            raise ValueError("best_result의 정답 수가 유효하지 않습니다.")

    @classmethod
    def _validate_history_record(cls, record: Any) -> None:
        if not isinstance(record, dict) or not isinstance(record.get("played_at"), str):
            raise ValueError("history 항목 형식이 올바르지 않습니다.")
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
        ):
            raise ValueError("history의 점수 또는 힌트 수가 유효하지 않습니다.")

    def state_dict(self) -> Dict[str, Any]:
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
            self.output(f"⚠️ 상태를 저장하지 못했습니다: {error}")
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

        count = self.read_int(
            f"풀 문제 수 (1~{len(self.quizzes)}): ", 1, len(self.quizzes)
        )
        selected = list(self.quizzes)
        self.rng.shuffle(selected)
        selected = selected[:count]
        correct = 0
        hints_used = 0
        self.output(f"\n📝 퀴즈를 시작합니다. (총 {len(selected)}문제)")
        for number, quiz in enumerate(selected, start=1):
            self.output("\n" + "-" * 42)
            for line in quiz.display_lines(number):
                self.output(line)
            if self.read_yes_no("힌트를 볼까요? (y/N): "):
                hints_used += 1
                hint = quiz.hint or "등록된 힌트가 없습니다."
                self.output(f"💡 힌트: {hint} (-10점)")
            answer = self.read_int("정답 입력 (1~4): ", 1, 4)
            if quiz.is_correct(answer):
                correct += 1
                self.output("✅ 정답입니다!")
            else:
                self.output(f"❌ 오답입니다. 정답은 {quiz.answer}번입니다.")

        total = len(selected)
        base_score = round(correct / total * 100)
        score = max(0, base_score - hints_used * 10)
        self.output("\n" + "=" * 42)
        self.output(f"🏆 결과: {total}문제 중 {correct}문제 정답 ({score}점)")
        if hints_used:
            self.output(
                f"   기본 {base_score}점 - 힌트 감점 {hints_used * 10}점"
            )

        if self.best_score is None or score > self.best_score:
            self.best_score = score
            self.best_result = {"correct": correct, "total": total}
            self.output("🎉 새로운 최고 점수입니다!")
        self.save_state()

    def read_yes_no(self, prompt: str) -> bool:
        """빈 입력은 아니요로 처리하고 y/n만 다시 받는다."""
        while True:
            answer = self.input(prompt).strip().lower()
            if answer in ("", "n", "no"):
                return False
            if answer in ("y", "yes"):
                return True
            self.output("⚠️ y 또는 n으로 입력하세요.")

    def show_menu(self) -> None:
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

    def run(self) -> None:
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
                    self.safe_exit()
                    return
        except (EOFError, KeyboardInterrupt):
            self.output("\n⚠️ 입력이 중단되었습니다. 현재 상태를 저장합니다.")
            self.safe_exit()

    def safe_exit(self) -> None:
        if self.save_state():
            self.output("💾 상태를 저장했습니다.")
        self.output("퀴즈 게임을 종료합니다.")
