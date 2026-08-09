PYTHON ?= python3
MKTEMP ?= mktemp
UV ?= uv
VENV ?= .venv
VENV_PYTHON ?= $(VENV)/bin/python

.PHONY: help setup verify-venv env demo git run runtime syntax style test lint
.PHONY: cli-smoke verify
.PHONY: verify-git verify-remote

help:
	@echo "make setup         # uv로 Python 3.10 가상환경 구성"
	@echo "make verify-venv   # 가상환경에서 전체 검증"
	@echo "make env           # Python·Git·현재 브랜치 확인"
	@echo "make demo          # 임시 상태에서 전체 기능 시연"
	@echo "make git           # 브랜치·병합 그래프 확인"
	@echo "make run           # 퀴즈 게임 실행"
	@echo "make runtime       # 정확한 검증 버전(Python 3.10) 확인"
	@echo "make syntax        # 현재 Python 문법·컴파일 검증"
	@echo "make style         # 과제용 PEP 8·257 핵심 규칙·Python 3.10 AST 검증"
	@echo "make test          # 전체 단위 테스트 실행"
	@echo "make verify        # 문법, 스타일, 테스트, CLI 검증"
	@echo "make verify-git    # 커밋, 병합, clone/pull 증거 검증"
	@echo "make verify-remote # 공개 main과 로컬 HEAD 일치 검증"

setup:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "uv가 필요합니다: https://docs.astral.sh/uv/getting-started/installation/" >&2; \
		exit 1; \
	}
	@if [ -d "$(VENV)" ] && [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "$(VENV)에 완전한 가상환경이 없습니다. 디렉터리를 확인한 뒤 다시 실행하세요." >&2; \
		exit 1; \
	fi
	@$(UV) python install 3.10
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		$(UV) venv --managed-python --python 3.10 "$(VENV)"; \
	fi
	@$(VENV_PYTHON) scripts/check_runtime.py
	@echo "가상환경 준비: PASS ($(VENV_PYTHON))"

verify-venv: setup
	@$(MAKE) verify PYTHON="$(VENV_PYTHON)"

env:
	@echo "=== admission-2 개발 환경 ==="
	@pwd
	@$(PYTHON) --version
	@git --version
	@printf "Git user: "; git config --local --get user.name
	@printf "Git email: "; git config --local --get user.email
	@printf "Branch: "; git branch --show-current

demo:
	@PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/run_demo.py

git:
	@git log --oneline --graph --decorate --all -18

run:
	$(PYTHON) main.py

runtime:
	@$(PYTHON) scripts/check_runtime.py

syntax:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m scripts.check_syntax

style:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/check_style.py

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

lint: syntax style

cli-smoke:
	@task_tmp_dir=$$($(MKTEMP) -d) || { \
		echo "임시 디렉터리를 만들지 못했습니다." >&2; exit 1; \
	}; \
	trap 'rm -rf "$$task_tmp_dir"' EXIT; \
	printf '6\n' | QUIZ_STATE_PATH="$$task_tmp_dir/state.json" \
		PYTHONDONTWRITEBYTECODE=1 $(PYTHON) main.py >/dev/null
	@echo "CLI 안전 종료: PASS"

verify: runtime syntax style test cli-smoke
	@echo "로컬 기능 검증: PASS"

verify-git:
	$(PYTHON) scripts/verify_git.py

verify-remote:
	$(PYTHON) scripts/verify_remote.py
