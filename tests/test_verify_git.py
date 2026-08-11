"""Git 실습 증거 검증의 회귀 테스트."""

import subprocess
import unittest
from unittest.mock import patch

from scripts.verify_git import validate_clone_log


VALID_LOG = """$ git clone repository
$ git push origin main
$ git pull --ff-only origin main
[main 1234abc] docs: refresh git workflow evidence
RESULT: PASS
"""


class VerifyGitTest(unittest.TestCase):
    """clone·push·pull 로그의 현재성과 메시지 규칙을 검사한다."""

    @patch("scripts.verify_git.git", return_value="")
    def test_current_lowercase_commit_is_accepted(self, _git):
        """현재 이력의 영문 소문자 커밋은 통과한다."""
        self.assertIsNone(validate_clone_log(VALID_LOG))

    @patch("scripts.verify_git.git", return_value="")
    def test_uppercase_commit_type_is_rejected(self, _git):
        """대문자 type으로 시작한 예전 메시지를 거부한다."""
        invalid = VALID_LOG.replace("docs:", "Docs:")
        self.assertIn("메시지 규칙", validate_clone_log(invalid))

    @patch(
        "scripts.verify_git.git",
        side_effect=subprocess.CalledProcessError(1, "git"),
    )
    def test_unreachable_logged_commit_is_rejected(self, _git):
        """현재 main에 없는 예전 커밋 증거를 거부한다."""
        self.assertIn("현재 main 이력에 없습니다", validate_clone_log(VALID_LOG))


if __name__ == "__main__":
    unittest.main()
