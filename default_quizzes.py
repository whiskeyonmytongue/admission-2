"""처음 실행할 때 사용하는 Python 기초 퀴즈."""

from typing import List

from quiz import Quiz


def create_default_quizzes() -> List[Quiz]:
    """직접 작성한 기본 퀴즈 다섯 개를 새 객체로 반환한다."""
    return [
        Quiz(
            "Python에서 여러 값을 순서대로 저장하는 자료형은?",
            ["int", "list", "bool", "float"],
            2,
            "대괄호([])로 표현하는 자료형입니다.",
        ),
        Quiz(
            "조건이 참일 때만 코드를 실행하는 키워드는?",
            ["if", "for", "def", "import"],
            1,
            "조건문을 시작하는 두 글자 키워드입니다.",
        ),
        Quiz(
            "정해진 범위를 반복할 때 주로 사용하는 문장은?",
            ["try", "class", "return", "for"],
            4,
            "컬렉션의 각 항목을 순회할 때 사용합니다.",
        ),
        Quiz(
            "함수를 정의할 때 사용하는 키워드는?",
            ["func", "def", "make", "lambda only"],
            2,
            "define의 앞 세 글자를 떠올려 보세요.",
        ),
        Quiz(
            "키와 값을 한 쌍으로 저장하는 자료형은?",
            ["tuple", "set", "dict", "str"],
            3,
            "dictionary의 줄임말입니다.",
        ),
    ]

