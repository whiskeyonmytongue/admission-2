"""과제에서 요구한 로컬 Git 이력과 clone/pull 증거를 검증한다."""

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLONE_LOG = ROOT / "docs" / "evidence" / "logs" / "clone-pull.txt"
LOGGED_COMMIT = re.compile(r"^\[main ([0-9a-f]{7,40})\] (.+)$", re.MULTILINE)
COMMIT_MESSAGE = re.compile(
    r"^(feat|fix|test|docs|refactor|build|chore|merge): [ -~]+$"
)


def git(*arguments: str) -> str:
    """프로젝트 루트에서 Git 명령을 실행하고 출력을 반환한다."""
    return subprocess.check_output(
        ["git", *arguments], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def fail(message: str, pending: bool = False) -> int:
    """실패 또는 미완료 메시지를 출력하고 실패 코드를 반환한다."""
    status = "PENDING" if pending else "FAIL"
    print(f"verify-git: {status} - {message}")
    return 1


def validate_clone_log(log: str) -> str | None:
    """clone 로그의 명령·커밋·메시지 증거를 검사한다."""
    required = ("git clone", "git push", "git pull", "RESULT: PASS")
    missing = [command for command in required if command not in log]
    if missing:
        return f"실습 로그에 다음 표식이 없습니다: {', '.join(missing)}"

    commits = LOGGED_COMMIT.findall(log)
    if not commits:
        return "실습 로그에 push한 커밋 기록이 없습니다."

    for commit, message in commits:
        if not COMMIT_MESSAGE.fullmatch(message):
            return f"로그의 커밋 메시지 규칙이 다릅니다: {message}"
        try:
            git("merge-base", "--is-ancestor", commit, "HEAD")
        except (OSError, subprocess.CalledProcessError):
            return f"로그의 커밋이 현재 main 이력에 없습니다: {commit}"
    return None


def main() -> int:
    """커밋·병합·clone/push/pull 증거를 순서대로 검증한다."""
    try:
        count = int(git("rev-list", "--count", "HEAD"))
        if count < 10:
            return fail(f"커밋이 {count}개입니다. 10개 이상이어야 합니다.")

        merges = git("log", "--merges", "--pretty=%s")
        if "feature/play-quiz" not in merges:
            return fail("feature/play-quiz 병합 커밋을 찾지 못했습니다.")

        parents = git("rev-list", "--parents", "--merges", "HEAD")
        if not any(len(line.split()) >= 3 for line in parents.splitlines()):
            return fail("두 부모를 가진 no-ff 병합 커밋이 없습니다.")
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        return fail(f"Git 이력을 읽지 못했습니다: {error}")

    if not CLONE_LOG.exists():
        return fail("clone/push/pull 실습 로그가 아직 없습니다.", pending=True)

    log = CLONE_LOG.read_text(encoding="utf-8")
    log_error = validate_clone_log(log)
    if log_error:
        return fail(log_error)

    print(f"커밋 {count}개, no-ff 병합, clone/push/pull 증거: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
