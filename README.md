# 우더기네 청약보드

서울·경기 APT 일반분양 칸반 보드. GitHub Actions가 한국시간 매일 07:00에 API를 수집하고 Pages에 배포합니다. PC를 켜둘 필요는 없습니다. 예약 실행은 GitHub 상황에 따라 지연될 수 있으며, 공개 저장소는 장기간 활동이 없을 때 예약이 비활성화될 수 있습니다.

## 처음 배포하기

1. GitHub 로그인 → 오른쪽 프로필에서 계정명을 확인합니다. 이메일과 계정명은 다릅니다.
2. 새 **공개** 저장소 `woodeok-applyhome`을 생성합니다. 기본 브랜치는 `main`으로 사용합니다.
3. 이 폴더를 GitHub Desktop의 **File → Add local repository**로 추가합니다. Git 저장소가 아니라는 메시지가 나오면 **create a repository here**를 선택합니다. 또는 터미널에서 `git init -b main`을 실행합니다.
4. 파일을 커밋하고 GitHub Desktop에서 Publish repository를 선택합니다. 2번에서 이미 저장소를 만들었다면 해당 저장소를 먼저 clone한 뒤 프로젝트 파일을 복사합니다. **숨김 폴더 `.github`를 반드시 포함**합니다.
5. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서 이름을 `APPLYHOME_SERVICE_KEY`, 값을 공공데이터포털의 **Decoding 인증키**로 저장합니다. 노출되었던 이전 키는 재발급하세요. 키는 코드·커밋·채팅에 넣지 않습니다.
6. **Settings → Pages → Source → GitHub Actions**를 선택합니다.
7. **Actions → 청약보드 갱신 및 배포 → Run workflow**를 실행합니다. 첫 push가 비밀값 설정 전에 실패했어도 설정 후 다시 실행하면 됩니다.
8. 실행이 성공하면 배포 URL을 확인합니다. 일반적으로 `https://계정명.github.io/woodeok-applyhome/`입니다.

## 데이터 기준

- 공식 API: https://www.data.go.kr/data/15098547/openapi.do
- 조회: `https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail`
- 모든 페이지를 조회한 후 서울·경기를 필터링합니다.
- 접수 중: 접수 시작일 ≤ 오늘 ≤ 종료일.
- 7일 내 접수: 내일부터 오늘+7일까지 시작하는 공고.
- 신규 공고: 오늘을 포함한 최근 7일 발표 공고. 접수 중/예정이면 해당 열에 우선 표시됩니다.
- 날짜 기준: Asia/Seoul. 일정 누락 공고도 신규 발표일 기준에 맞으면 신규 열에 표시합니다.
- 분양가는 표시하지 않습니다. 공식 서비스에 `getAPTLttotPblancMdl` 별도 주택형 상세 조회가 존재하는 것을 확인했지만 실제 응답 필드·단위를 인증 조회로 검증하기 전에는 연결하지 않습니다.
- 무순위·임의공급·오피스텔·임대는 현재 범위에서 제외합니다.
- 각 단지별 1080×1350 PNG와 SVG 카드를 생성합니다. 한글 글꼴은 CI에 설치합니다.
- API 실패 시 새 배포를 중단하여 기존 정상 배포를 유지합니다. 화면에 수집시각을 표시하고 36시간 이상 지나면 지연 안내가 나옵니다.
- 공개 파일에는 허용된 공고 필드만 저장하며 인증키와 원본 응답은 저장하지 않습니다.

## 로컬 실행

Python 3.9 이상, Cairo 라이브러리와 한글 글꼴이 필요합니다. GitHub Actions는 실행 환경을 자동 구성합니다.

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
# APPLYHOME_SERVICE_KEY는 프로세스 환경변수로만 전달
python3 scripts/build.py
python3 -m http.server 8000 --directory public
```

키를 명령문에 직접 쓰면 셸 히스토리에 남을 수 있습니다. 저장소의 Actions Secret 방식을 권장합니다.

현재 검증: 필터 경계일, 중복 제거, 지역 제외, 외부 링크 검증 단위 테스트 통과. 실제 API 인증 수집·이미지 렌더링·GitHub 배포는 키 및 GitHub 연결 후 확인해야 합니다.
