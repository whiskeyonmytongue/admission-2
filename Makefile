PYTHON ?= python3

.PHONY: help env demo git run test lint cli-smoke verify verify-git verify-remote

help:
	@echo "make env           # Python·Git·현재 브랜치 확인"
	@echo "make demo          # 임시 상태에서 전체 기능 시연"
	@echo "make git           # 브랜치·병합 그래프 확인"
	@echo "make run           # 퀴즈 게임 실행"
	@echo "make verify        # 테스트, 문법, 안전 종료 검증"
	@echo "make verify-git    # 커밋, 병합, clone/pull 증거 검증"
	@echo "make verify-remote # 공개 main과 로컬 HEAD 일치 검증"

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

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile \
		main.py quiz.py default_quizzes.py quiz_game.py \
		scripts/run_demo.py scripts/verify_git.py scripts/verify_remote.py \
		tests/test_quiz.py tests/test_quiz_game.py

cli-smoke:
	@task_tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$task_tmp_dir"' EXIT; \
	printf '6\n' | QUIZ_STATE_PATH="$$task_tmp_dir/state.json" \
		PYTHONDONTWRITEBYTECODE=1 $(PYTHON) main.py >/dev/null
	@echo "CLI 안전 종료: PASS"

verify: test lint cli-smoke
	@echo "로컬 기능 검증: PASS"

verify-git:
	$(PYTHON) scripts/verify_git.py

verify-remote:
	$(PYTHON) scripts/verify_remote.py
