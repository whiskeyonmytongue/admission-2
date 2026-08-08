# 실행 증거 안내

이 디렉터리에는 과제 기능과 Git 작업을 실제로 실행한 기록을 보관합니다.

- `logs/`: 복사 가능한 명령과 터미널 출력
- `images/environment.png`: Python·Git·계정·브랜치 확인 화면
- `images/app-workflow.png`: 추가→목록→풀이→힌트 감점→점수 저장 화면
- `images/git-history.png`: 기능 브랜치와 `--no-ff` 병합 그래프

텍스트 기록만으로 꾸미지 않고, 실행 환경과 Git 이력을 함께 확인할 수 있도록 구성합니다.

같은 화면은 프로젝트 루트에서 `make env`, `make demo`, `make git`으로 다시
만들 수 있습니다. `make demo`는 임시 상태 파일을 사용하고 실행 후 자동으로
정리하므로 제출용 `state.json`을 바꾸지 않습니다.
