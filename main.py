"""Python 기초 퀴즈 게임 실행 진입점."""

import os
import sys
from pathlib import Path

from quiz_game import QuizGame, StateAccessError


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = PROJECT_ROOT / "state.json"


def resolve_state_path() -> Path:
    """환경 변수 override 또는 프로젝트 루트 상태 경로를 반환한다."""
    override = os.environ.get("QUIZ_STATE_PATH")
    return Path(override) if override else DEFAULT_STATE_PATH


def main() -> int:
    """퀴즈 게임을 시작하고 초기화 실패를 제어된 종료로 바꾼다."""
    try:
        return QuizGame(state_path=resolve_state_path()).run()
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️ 시작 중 입력이 중단되어 안전하게 종료합니다.")
        return 0
    except StateAccessError as error:
        print(f"⚠️ {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
