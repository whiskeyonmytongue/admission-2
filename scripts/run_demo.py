"""제출용 상태를 바꾸지 않고 핵심 기능을 한 번에 시연한다."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from quiz_game import QuizGame


class NewestFirst:
    """방금 추가한 문제를 첫 문제로 고르는 재현 가능한 셔플."""

    @staticmethod
    def shuffle(values: List[object]) -> None:
        """마지막 문제를 첫 위치로 옮긴다."""
        values.insert(0, values.pop())


def main() -> None:
    """임시 상태에서 추가·조회·풀이·점수 조회를 실행한다."""
    answers = iter(
        [
            "len 함수의 역할은?",
            "문자열 출력",
            "길이 반환",
            "파일 열기",
            "반복 종료",
            "2",
            "객체의 길이를 구합니다.",
            "1",
            "y",
            "2",
        ]
    )

    def scripted_input(prompt: str) -> str:
        answer = next(answers)
        print(f"{prompt}{answer}")
        return answer

    with tempfile.TemporaryDirectory(prefix="admission-2-demo-") as directory:
        game = QuizGame(
            state_path=Path(directory) / "state.json",
            input_fn=scripted_input,
            rng=NewestFirst(),
        )
        game.add_quiz()
        game.list_quizzes()
        game.play_quiz()
        game.show_score()

    print("\nDEMO RESULT: PASS (임시 상태 자동 정리)")


if __name__ == "__main__":
    main()
