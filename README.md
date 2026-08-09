# Python 기초 퀴즈

[![verify](https://github.com/whiskeyonmytongue/admission-2/actions/workflows/verify.yml/badge.svg)](https://github.com/whiskeyonmytongue/admission-2/actions/workflows/verify.yml)

터미널에서 퀴즈를 등록하고 풀 수 있는 Python 콘솔 프로그램입니다. 프로그램을
종료해도 퀴즈, 최고 점수와 플레이 기록이 프로젝트 루트의 `state.json`에
남습니다.

퀴즈 주제는 **Python 기초 문법**입니다. 자료형, 조건문, 반복문, 함수와
딕셔너리를 문제로 만들면 프로그램을 구현하는 과정과 개념 복습을 자연스럽게
연결할 수 있어 이 주제를 선택했습니다.

## 바로 실행하기

Python 3.10 이상과 Git만 있으면 됩니다. 외부 패키지는 사용하지 않습니다.

```bash
git clone https://github.com/whiskeyonmytongue/admission-2.git
cd admission-2
python3 main.py
```

실행 후 `1`부터 `6`까지 원하는 기능을 선택합니다.

```text
1. 퀴즈 풀기
2. 퀴즈 추가
3. 퀴즈 목록
4. 점수 확인
5. 퀴즈 삭제
6. 종료
```

숫자 앞뒤의 공백은 자동으로 제거합니다. 빈 값, 문자, 허용 범위를 벗어난
숫자를 입력하면 이유를 알려 주고 다시 입력받습니다. `Ctrl+C`나 EOF가
발생해도 가능한 상태를 저장한 뒤 traceback 없이 종료합니다.

## 구현 결과

### 필수 기능

| 기능 | 구현 내용 | 확인 위치 |
|---|---|---|
| 기본 퀴즈 | 직접 작성한 Python 기초 문제 5개 | `default_quizzes.py`, `state.json` |
| 퀴즈 풀기 | 출제, 1~4 입력 검증, 정답 판정, 결과 출력 | `QuizGame.play_quiz()` |
| 퀴즈 관리 | 추가, 목록 조회, 삭제 후 즉시 저장 | `add_quiz()`, `list_quizzes()`, `delete_quiz()` |
| 점수 | 최고 점수와 정답 수 저장·조회 | `show_score()` |
| 파일 복구 | 파일 없음은 기본값 생성, 손상 파일은 백업 후 복구 | `load_state()` |
| 안전 저장 | 임시 파일 기록 후 `os.replace()`로 원자 교체 | `save_state()` |
| 입력 안전성 | 중복 JSON 키와 출력에 위험한 문구·시각 형식 거부 | `load_state()`, `Quiz` |

### 보너스 기능

| 기능 | 구현 내용 |
|---|---|
| 랜덤 출제 | `random.shuffle()`로 문제 순서 섞기 |
| 문제 수 선택 | 전체 문제 범위에서 풀 문제 수 지정 |
| 힌트 | 실제 힌트 한 번당 10점 감점, 빈 힌트는 감점 없음 |
| 퀴즈 삭제 | 삭제 즉시 저장, 저장 실패 시 메모리 상태 복구 |
| 플레이 기록 | ISO 8601 시각·문제 수·정답 수·점수 저장 |

## 핵심 실행 화면

![퀴즈 추가·목록·풀이·점수 시연](docs/evidence/images/app-workflow.png)

여섯 번째 문제를 추가한 뒤 한 문제를 풀었습니다. 힌트를 한 번 사용해 10점이
차감됐고, 최종 90점과 플레이 시각이 함께 저장된 것을 확인할 수 있습니다.
같은 시나리오를 다시 실행한 텍스트 출력은
[기능 시연 로그](docs/evidence/logs/app-workflow.txt)에 있습니다.

## 코드 구조와 실행 흐름

```text
main.py
  └─ QuizGame 생성
       ├─ state.json 불러오기 또는 기본값 복구
       ├─ 메뉴 입력과 기능 실행
       ├─ Quiz 객체로 문제와 정답 판정 관리
       └─ 변경된 상태를 state.json에 원자적으로 저장
```

- `Quiz`는 문제 한 개의 데이터 검증, 표시 형식과 정답 판정을 담당합니다.
- `QuizGame`은 입력 검증, 메뉴, 게임 진행과 파일 입출력을 담당합니다.
- `calculate_score()`는 정답 수와 유효한 힌트 수로 점수를 계산합니다.

`if/elif`는 선택한 메뉴에 따라 실행할 기능을 나눕니다. `while`은 올바른
입력을 받을 때까지 반복하고, `for`는 문제와 선택지를 차례대로 처리합니다.
문제 형식이 바뀌면 `Quiz`, 게임 규칙이 바뀌면 `QuizGame`부터 확인하면 됩니다.

## `state.json` 설명

`state.json`은 프로젝트 루트에 저장하는 UTF-8 JSON 파일입니다.

```json
{
  "quizzes": [
    {
      "question": "문제",
      "choices": ["보기 1", "보기 2", "보기 3", "보기 4"],
      "answer": 1,
      "hint": "힌트"
    }
  ],
  "best_score": 90,
  "best_result": {"correct": 1, "total": 1},
  "history": [
    {
      "played_at": "2026-08-09T00:00:00Z",
      "total": 1,
      "correct": 1,
      "score": 90,
      "hints_used": 1
    }
  ]
}
```

JSON은 사람이 읽기 쉽고 Python의 `dict`와 `list`를 그대로 표현할 수 있어
선택했습니다. 파일을 읽고 쓰는 과정에서 발생하는 오류는 `try/except`로
처리합니다.

### 저장과 복구 정책

- 파일이 없으면 기본 퀴즈 5개로 새 `state.json`을 만듭니다.
- 파일이 손상되면 원본을 `.quiz-corrupt-<해시>-<UTC 시각>.bak`으로 보존한 뒤
  기본 상태로 복구합니다.
- 저장할 때는 같은 디렉터리에 임시 파일을 쓴 뒤 `os.replace()`로 교체합니다.
- 중복 JSON 키, 터미널 제어 문자와 UTF-8로 출력할 수 없는 Unicode
  surrogate는 거부합니다.
- 플레이 시각은 `T` 구분자와 시간대가 있는 ISO 8601 형식만 허용합니다.

`main.py`를 다른 디렉터리에서 실행해도 기본 저장 위치는 이 프로젝트의
`state.json`입니다. 별도 상태가 필요하면 `QUIZ_STATE_PATH` 환경 변수로
경로를 바꿀 수 있습니다.

저장에 실패해 안전하게 종료할 수 없는 경우에는 원인을 표준 오류(`stderr`)로
출력하고 종료 코드 `1`을 반환합니다. 임시 파일 생성 구간의 `Ctrl+C` 원자성은
`pthread_sigmask`를 제공하는 macOS와 Linux에서 보장합니다. Windows는 검증
범위에 포함하지 않습니다.

퀴즈가 수천 개로 늘어나면 매번 전체 JSON을 읽고 쓰는 비용과 동시 수정 문제가
커집니다. 이 규모에서는 개별 레코드를 조회하고 갱신할 수 있는 SQLite 같은
데이터베이스가 더 적합합니다.

## 자동 검증

전체 검증은 다음 명령 하나로 실행합니다.

```bash
make verify PYTHON=python3.10
```

이 명령은 Python 3.10 확인, 전체 Python 파일의 문법과 스타일 검사, 단위 테스트,
임시 상태를 사용한 CLI 안전 종료를 차례대로 실행합니다. 테스트 데이터는
`tempfile` 아래에만 만들기 때문에 제출용 `state.json`은 바뀌지 않습니다.

추가 검증 명령은 다음과 같습니다.

| 명령 | 확인 내용 |
|---|---|
| `make env` | Python·Git·현재 브랜치 |
| `make demo` | 추가·목록·풀이·점수 전체 시연 |
| `make git` | 브랜치와 병합 그래프 |
| `make verify-git` | 커밋·병합·clone/pull 증거 |
| `make verify-remote` | PUBLIC/main과 로컬·원격 HEAD 일치 |

스타일 검사는 표준 라이브러리만 사용합니다. UTF-8, LF, 마지막 개행, 줄 끝
공백, 4칸 들여쓰기, 코드 79자, 주석과 docstring 72자, 공개 API docstring,
Python 3.10 문법과 함수 50줄 제한을 확인합니다. GitHub Actions의 공식 Action은
검토한 커밋 SHA로 고정했습니다.

## Git 작업 기록

| 요구사항 | 결과 | 증거 |
|---|---:|---|
| 의미 있는 커밋 10개 이상 | 33개 이상 PASS | [Git 검증 로그](docs/evidence/logs/verification.txt) |
| 추가 브랜치 생성·병합 | no-ff 병합 PASS | `feature/play-quiz`, `61a6736` |
| clone과 pull 실습 | PASS | [왕복 로그](docs/evidence/logs/clone-pull.txt) |
| 공개 저장소와 `main` | PASS | `make verify-remote` |

퀴즈 풀기는 `feature/play-quiz` 브랜치에서 구현한 뒤 `git merge --no-ff`로
`main`에 병합했습니다.

![feature 브랜치 no-ff 병합 그래프](docs/evidence/images/git-history.png)

별도 디렉터리에 저장소를 clone하고 README를 수정해 push한 뒤, 최초 작업
디렉터리에서 `git pull --ff-only`로 받아왔습니다.

![clone → push → pull 결과](docs/evidence/images/clone-pull.png)

<details>
<summary>이 프로젝트에서 사용한 Git 명령</summary>

| 명령 | 역할 |
|---|---|
| `git init` | 로컬 저장소 생성 |
| `git add` | 다음 커밋에 포함할 변경 선택 |
| `git commit` | 기능 단위 변경 이력 저장 |
| `git checkout` | 플레이 기능 브랜치 생성·전환 |
| `git merge` | 플레이 브랜치를 `main`에 병합 |
| `git push` | 로컬 커밋을 GitHub에 전송 |
| `git clone` | GitHub 저장소를 별도 디렉터리에 복제 |
| `git pull` | 원격 변경을 기존 디렉터리에 반영 |

</details>

## 파일 구조

```text
.
├── main.py                    # 실행 진입점
├── quiz.py                    # Quiz 클래스
├── quiz_game.py               # QuizGame 클래스와 전체 기능
├── default_quizzes.py         # 기본 퀴즈 5개
├── state.json                 # 퀴즈·점수·플레이 기록
├── tests/                     # unittest 자동 테스트
├── scripts/                   # 스타일·Git·원격 검증
├── .github/workflows/         # Python 3.10 CI
├── docs/evidence/             # 실행 로그와 화면
├── Makefile                   # 반복 가능한 검증 명령
└── README.md
```

## 추가 확인 자료

개발 화면의 Python 3.13은 일상 개발 환경입니다. 최소 지원 버전과 제출 검증은
Python 3.10에서 별도로 수행했습니다.

![Python과 Git 개발 환경](docs/evidence/images/environment.png)

- [개발 환경 로그](docs/evidence/logs/environment.txt)
- [자동 테스트와 검증 결과](docs/evidence/logs/verification.txt)
- [clone → commit → push → pull 로그](docs/evidence/logs/clone-pull.txt)
