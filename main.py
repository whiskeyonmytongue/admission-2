"""Python 기초 퀴즈 게임 실행 진입점."""

import os

from quiz_game import QuizGame, StateAccessError


def main() -> int:
    state_path = os.environ.get("QUIZ_STATE_PATH", "state.json")
    try:
        return QuizGame(state_path=state_path).run()
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️ 시작 중 입력이 중단되어 안전하게 종료합니다.")
        return 0
    except StateAccessError as error:
        print(f"⚠️ {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
