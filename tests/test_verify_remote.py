"""GitHub 원격 검증기의 URL·응답 경계를 검증한다."""

import io
import unittest
from unittest.mock import patch

from scripts import verify_remote


class VerifyRemoteTest(unittest.TestCase):
    def test_repository_name_accepts_exact_github_urls(self) -> None:
        expected = "whiskeyonmytongue/admission-2"
        remotes = (
            "git@github.com:whiskeyonmytongue/admission-2.git",
            "https://github.com/whiskeyonmytongue/admission-2.git",
            "ssh://git@github.com/whiskeyonmytongue/admission-2.git",
        )

        for remote in remotes:
            with self.subTest(remote=remote):
                repository = verify_remote.repository_name(remote)
                self.assertEqual(repository, expected)

    def test_repository_name_rejects_disguised_or_extra_paths(self) -> None:
        remotes = (
            "https://evil.example/github.com/whiskeyonmytongue/admission-2",
            "https://github.com/whiskeyonmytongue/admission-2/extra",
            "https://github.com/whiskeyonmytongue/admission-2?ref=main",
            "ssh://other@github.com/whiskeyonmytongue/admission-2",
        )

        for remote in remotes:
            with self.subTest(remote=remote):
                self.assertIsNone(verify_remote.repository_name(remote))

    def test_invalid_metadata_shape_is_a_controlled_failure(self) -> None:
        captured = io.StringIO()
        command_outputs = (
            "git@github.com:whiskeyonmytongue/admission-2.git",
            "a" * 40,
            "a" * 40 + "\trefs/heads/main",
        )
        with patch.object(
            verify_remote,
            "run",
            side_effect=command_outputs,
        ), patch.object(
            verify_remote,
            "_repository_metadata",
            return_value=[],
        ), patch.object(
            verify_remote.shutil,
            "which",
            return_value="/usr/bin/gh",
        ), patch("sys.stdout", captured):
            result = verify_remote.main()

        self.assertEqual(result, 1)
        self.assertIn("객체 형식", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
