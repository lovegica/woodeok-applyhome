# 2026-10-25 수정 및 검증

기준 커밋: 7f92673d8852d12f02b4aee8e4956f4ce42bb7df

## 확인한 운영 상태
- 배포 data.json: 갱신 2026-10-25 09:00:36 KST, 공고 7건, 좌표 2건.
- Actions 실행 40144976188: schedule, 2026-10-25 00:00:20 UTC (09:00:20 KST), success.
- 해당 실행의 head_sha는 위 기준 커밋과 동일. cron은 이미 `0 22 * * *` (07:00 KST). 09시 실행은 cron의 UTC 변환 오류로 설명되지 않음. GitHub 예약 실행 지연 가능성이 있으나 내부 원인은 확정하지 못함.
- Actions jobs 메타데이터 접근 성공. 원본 로그 다운로드는 HTTP 403으로 실패.

## 변경
- 공공데이터포털 공식 통합 Swagger에 따라 APT, APT 잔여세대(04 무순위 / 06 불법행위 재공급), 임의공급 3개 API 수집. 어느 하나라도 실패하면 불완전한 결과의 배포 중단.
- 특별공급, 1/2순위 지역별 일정 및 잔여세대/임의공급 접수 필드 사용. 일정 없는 신규 공고와 종료 공고 제외. 향후 접수 공고의 기존 7일 제한 제거.
- 괄호 안 실제 지번 보존, 화성 행정구역 정규화. 시/군/구, 동/리, 산 여부, 본번/부번 또는 도로명 건물번호 검증. 사업 블록/동 중심 좌표 거부.
- 위치 근거(검색문, 일치 주소, 공급자, 조회 시각) 보존. 미확인 공고는 카드에 주소와 함께 유지.
- KST 현재 날짜와 공급별 일정으로 오늘 접수만 노란 마커, 예정은 회색. 마커 클릭 시 카드 선택 및 이동 유지.
- 기존 07시 cron 유지. GitHub Actions만으로 07시 정각 완료 보장 불가.
- REST/API 비밀값은 CI 환경변수에만 유지. 브라우저용 Kakao JavaScript 키만 config.json에 기록.

## 검증
- Python 단위 테스트 13건 통과: 지역, 접수 공백일, 미래 일정, 종료 제외, 공급 유형 수집, 실패 시 중단, 주소 누락/오매칭 방지.
- JavaScript 문법 검사 통과. 날짜 경계/접수 공백과 마커→카드 동작 assertion 4건 통과.
- git diff --check 통과.
- 실제 Kakao/API 재수집, 브라우저 시각 검증, 원격 push, 배포 후 검증은 미완료. 따라서 좌표 증가 건수는 주장하지 않음.

## 배포 차단
GitHub 쓰기 인증이 없어 push dry-run이 `could not read Username`으로 실패. 브라우저 도구도 로컬 런타임 오류로 초기화 실패. API 비밀값을 채팅에 제공할 필요 없음. GitHub 인증 복구 후 main에 변경을 push하면 기존 Actions가 재수집/검증/Pages 배포를 수행함.

## 공식 근거
- https://www.data.go.kr/data/15098547/openapi.do
- https://infuser.odcloud.kr/api/stages/37000/api-docs?1643022751478
- https://developers.kakao.com/docs/ko/local/dev-guide
