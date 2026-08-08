"""Python 기초 퀴즈 게임 실행 진입점."""

import os

from quiz_game import QuizGame


def main() -> int:
    state_path = os.environ.get("QUIZ_STATE_PATH", "state.json")
    QuizGame(state_path=state_path).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
