"""표준 라이브러리 스타일 검사기의 주요 경계를 검증한다."""

import io
import unittest
from unittest.mock import patch

from scripts import check_style


class StyleCheckerTest(unittest.TestCase):
    def test_overlong_line_returns_failure_with_location(self) -> None:
        path = check_style.ROOT / "probe.py"
        source = '"""Temporary style probe."""\n\nprobe = "{0}"\n'.format(
            "x" * 90
        )
        captured_error = io.StringIO()
        with patch(
            "scripts.check_style.source_paths",
            return_value=[path],
        ), patch(
            "scripts.check_style.decode_source",
            return_value=source,
        ), patch("sys.stderr", captured_error):
            result = check_style.main()

        self.assertEqual(result, 1)
        self.assertIn("probe.py:3", captured_error.getvalue())

    def test_empty_discovery_returns_failure(self) -> None:
        captured_error = io.StringIO()
        with patch(
            "scripts.check_style.source_paths",
            return_value=[],
        ), patch("sys.stderr", captured_error):
            result = check_style.main()

        self.assertEqual(result, 1)
        self.assertIn("검사할", captured_error.getvalue())

    def test_indent_alignment_and_wide_suite(self) -> None:
        path = check_style.ROOT / "probe.py"
        aligned = "value = call(\n     first,\n     second,\n)\n"
        errors = []
        check_style.check_python_lines(path, aligned, errors)
        self.assertEqual(errors, [])

        wide_suite = "if True:\n        value = 1\n"
        check_style.check_python_lines(path, wide_suite, errors)
        self.assertTrue(any("4칸" in item for item in errors))

    def test_invalid_utf8_reports_line_number(self) -> None:
        path = check_style.ROOT / "probe.py"
        errors = []
        with patch("pathlib.Path.read_bytes", return_value=b"valid\n\xff"):
            self.assertIsNone(check_style.decode_source(path, errors))

        self.assertTrue(any("probe.py:2" in item for item in errors))

    def test_control_flow_string_is_not_a_docstring(self) -> None:
        path = check_style.ROOT / "probe.py"
        source = '"""Module."""\nif True:\n    "{0}"\n'.format(
            "x" * 70
        )
        errors = []

        check_style.check_python_lines(path, source, errors)

        self.assertEqual(errors, [])

    def test_inline_comment_uses_code_line_limit(self) -> None:
        path = check_style.ROOT / "probe.py"
        source = 'value = "{0}"  # note\n'.format("x" * 58)
        errors = []

        check_style.check_python_lines(path, source, errors)

        self.assertEqual(errors, [])

    def test_crlf_reports_its_actual_line(self) -> None:
        path = check_style.ROOT / "probe.py"
        errors = []
        with patch(
            "pathlib.Path.read_bytes",
            return_value=b"first\nsecond\r\n",
        ):
            check_style.decode_source(path, errors)

        self.assertTrue(any("probe.py:2" in item for item in errors))
        self.assertFalse(any("probe.py:1" in item for item in errors))

    def test_function_length_includes_decorator(self) -> None:
        path = check_style.ROOT / "probe.py"
        source = (
            '"""Module."""\n\n@decorator\ndef public():\n'
            '    """Public function."""\n'
            + "    pass\n" * 48
        )
        errors = []

        check_style.check_ast(path, source, errors)

        self.assertTrue(any("50줄" in item for item in errors))

    def test_compiler_context_error_fails_style_check(self) -> None:
        path = check_style.ROOT / "probe.py"
        errors = []

        check_style.check_ast(path, '"""Module."""\nreturn\n', errors)

        self.assertTrue(any("문법 오류" in item for item in errors))

    def test_valid_nested_async_context_is_not_rejected(self) -> None:
        path = check_style.ROOT / "probe.py"
        sources = (
            "    return [[y for y in await get()] for x in xs]\n",
            "    return [[y async for y in agen2()] "
            "async for x in agen1()]\n",
            "    return (y async for y in agen())\n",
        )
        for body in sources:
            source = (
                '\"\"\"Module.\"\"\"\nasync def public():\n'
                '    \"\"\"Return a valid async expression.\"\"\"\n'
                + body
            )
            with self.subTest(body=body):
                errors = []
                check_style.check_ast(path, source, errors)
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
