"""GitHub 공개 저장소의 main과 로컬 HEAD가 같은지 검증한다."""

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> str:
    """프로젝트 루트에서 외부 명령을 실행하고 출력을 반환한다."""
    return subprocess.check_output(
        list(arguments), cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def fail(message: str, pending: bool = False) -> int:
    """실패 또는 미완료 메시지를 출력하고 실패 코드를 반환한다."""
    status = "PENDING" if pending else "FAIL"
    print(f"verify-remote: {status} - {message}")
    return 1


def repository_name(remote: str) -> str | None:
    """GitHub 원격 URL에서 owner/repository 이름을 추출한다."""
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote)
    return match.group(1) if match else None


def _repository_metadata(repository: str) -> dict:
    """GitHub CLI가 반환한 저장소 메타데이터를 읽는다."""
    return json.loads(
        run(
            "gh",
            "repo",
            "view",
            repository,
            "--json",
            "visibility,defaultBranchRef",
        )
    )


def main() -> int:
    """공개 main 브랜치와 로컬 HEAD 일치 여부를 검증한다."""
    try:
        remote = run("git", "remote", "get-url", "origin")
    except (OSError, subprocess.CalledProcessError):
        return fail("origin이 아직 설정되지 않았습니다.", pending=True)

    repository = repository_name(remote)
    if repository != "whiskeyonmytongue/admission-2":
        return fail(f"origin 대상이 올바르지 않습니다: {remote}")

    try:
        local_head = run("git", "rev-parse", "HEAD")
        remote_line = run("git", "ls-remote", "origin", "refs/heads/main")
    except (OSError, subprocess.CalledProcessError) as error:
        return fail(f"원격 main을 확인하지 못했습니다: {error}", pending=True)
    if not remote_line:
        return fail("원격 main 브랜치가 없습니다.", pending=True)
    remote_head = remote_line.split()[0]
    if local_head != remote_head:
        return fail(
            f"HEAD 불일치: local={local_head[:7]}, "
            f"remote={remote_head[:7]}"
        )

    if not shutil.which("gh"):
        return fail("PUBLIC/default branch 확인에 필요한 gh가 없습니다.")
    try:
        metadata = _repository_metadata(repository)
    except (
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        return fail(f"GitHub 메타데이터를 확인하지 못했습니다: {error}")

    default_branch = (metadata.get("defaultBranchRef") or {}).get("name")
    if metadata.get("visibility") != "PUBLIC" or default_branch != "main":
        return fail(
            f"PUBLIC/main이 아닙니다: {metadata.get('visibility')}/{default_branch}"
        )

    print(f"PUBLIC/main 및 HEAD {local_head[:7]} 일치: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
