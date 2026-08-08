"""개별 퀴즈 문제를 표현하는 모델."""

from __future__ import annotations

from typing import Any, Dict, List


class Quiz:
    """문제, 네 개의 선택지, 정답 번호와 힌트를 묶어 관리한다."""

    CHOICE_COUNT = 4

    def __init__(
        self,
        question: str,
        choices: List[str],
        answer: int,
        hint: str = "",
    ) -> None:
        """입력값을 검증하고 공백을 정리해 퀴즈를 생성한다."""
        if not isinstance(question, str) or not isinstance(hint, str):
            raise ValueError("문제와 힌트는 문자열이어야 합니다.")
        if not isinstance(choices, list) or any(
            not isinstance(choice, str) for choice in choices
        ):
            raise ValueError("선택지는 문자열 배열이어야 합니다.")
        question = question.strip()
        choices = [choice.strip() for choice in choices]
        hint = hint.strip()

        if not question:
            raise ValueError("문제는 비어 있을 수 없습니다.")
        if len(choices) != self.CHOICE_COUNT or any(
            not choice for choice in choices
        ):
            raise ValueError("선택지는 비어 있지 않은 네 개여야 합니다.")
        if (
            isinstance(answer, bool)
            or not isinstance(answer, int)
            or not 1 <= answer <= 4
        ):
            raise ValueError("정답 번호는 1부터 4 사이의 정수여야 합니다.")

        self.question = question
        self.choices = choices
        self.answer = answer
        self.hint = hint

    def display_lines(self, number: int | None = None) -> List[str]:
        """터미널에 출력할 문제와 선택지 문자열을 반환한다."""
        title = f"[문제 {number}] {self.question}" if number else self.question
        lines = [
            f"{index}. {choice}"
            for index, choice in enumerate(self.choices, start=1)
        ]
        return [title] + lines

    def is_correct(self, answer: int) -> bool:
        """입력한 번호가 정답인지 확인한다."""
        return answer == self.answer

    def to_dict(self) -> Dict[str, Any]:
        """JSON으로 저장할 수 있는 딕셔너리로 변환한다."""
        return {
            "question": self.question,
            "choices": list(self.choices),
            "answer": self.answer,
            "hint": self.hint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quiz":
        """저장된 딕셔너리를 검증하면서 Quiz 객체로 복원한다."""
        if not isinstance(data, dict):
            raise ValueError("퀴즈 데이터는 객체여야 합니다.")
        return cls(
            question=data.get("question", ""),
            choices=data.get("choices", []),
            answer=data.get("answer"),
            hint=data.get("hint", ""),
        )
