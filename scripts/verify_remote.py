"""GitHub 공개 저장소의 main과 로컬 HEAD가 같은지 검증한다."""

import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> str:
    return subprocess.check_output(
        list(arguments), cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def fail(message: str, pending: bool = False) -> int:
    status = "PENDING" if pending else "FAIL"
    print(f"verify-remote: {status} - {message}")
    return 1


def repository_name(remote: str) -> str | None:
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote)
    return match.group(1) if match else None


def main() -> int:
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
        return fail(f"HEAD 불일치: local={local_head[:7]}, remote={remote_head[:7]}")

    if not shutil.which("gh"):
        return fail("PUBLIC/default branch 확인에 필요한 gh가 없습니다.")
    try:
        metadata = json.loads(
            run(
                "gh",
                "repo",
                "view",
                repository,
                "--json",
                "visibility,defaultBranchRef",
            )
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
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
