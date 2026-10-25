"""Fetch ApplyHome server-side. Never publish credentials or raw responses."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

BASE = 'https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/'
KST = dt.timezone(dt.timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]

def date(value):
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

SOURCES = {
    'getAPTLttotPblancDetail': 'APT 일반분양',
    'getRemndrLttotPblancDetail': '무순위·잔여세대·재공급',
    'getOPTLttotPblancDetail': '임의공급',
}

def schedules(row):
    periods = []
    pairs = [('SPSPLY_RCEPT_BGNDE', 'SPSPLY_RCEPT_ENDDE', '특별공급'),
             ('GNRL_RCEPT_BGNDE', 'GNRL_RCEPT_ENDDE', '일반공급')]
    for rank in (1, 2):
        for area in ('CRSPAREA', 'ETC_GG', 'ETC_AREA'):
            pairs.append((f'GNRL_RNK{rank}_{area}_RCPTDE', f'GNRL_RNK{rank}_{area}_ENDDE', f'{rank}순위'))
    for start, end, label in pairs:
        begin, finish = date(row.get(start)), date(row.get(end))
        if begin and finish and begin <= finish:
            entry = dict(type=label, start=str(begin), end=str(finish))
            if entry not in periods:
                periods.append(entry)
    if not periods:
        for prefix in ('SUBSCRPT_RCEPT', 'RCEPT'):
            begin, finish = date(row.get(prefix+'_BGNDE')), date(row.get(prefix+'_ENDDE'))
            if begin and finish and begin <= finish:
                periods.append(dict(type=row.get('_sourceType', '청약 접수'), start=str(begin), end=str(finish)))
                break
    return periods

def select(rows, today):
    result = {}
    for row in rows:
        region = str(row.get('SUBSCRPT_AREA_CODE_NM') or '')
        address = str(row.get('HSSPLY_ADRES') or '').strip()
        if address.startswith(('서울', '경기')):
            region = '서울' if address.startswith('서울') else '경기'
        elif region not in ('서울', '서울특별시', '경기', '경기도'):
            continue
        periods = schedules(row)
        relevant = [p for p in periods if p['end'] >= str(today)]
        if not relevant:
            continue
        active = any(p['start'] <= str(today) <= p['end'] for p in periods)
        begin, finish = min(p['start'] for p in periods), max(p['end'] for p in periods)
        announced = date(row.get('RCRIT_PBLANC_DE'))
        new = bool(announced and today - dt.timedelta(days=6) <= announced <= today)
        identity = str(row.get('HOUSE_MANAGE_NO') or '') + '-' + str(row.get('PBLANC_NO') or '')
        if identity == '-':
            raise ValueError('공고 식별번호 누락')
        link = str(row.get('PBLANC_URL') or '')
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme != 'https' or not (parsed.hostname == 'applyhome.co.kr' or (parsed.hostname or '').endswith('.applyhome.co.kr')):
            link = 'https://www.applyhome.co.kr/'
        result[identity] = dict(id=identity, name=str(row.get('HOUSE_NM') or '단지명 미제공'), region=region, address=address, start=begin, end=finish, schedules=periods, applicationType=row.get('HOUSE_SECD_NM') or row.get('_sourceType', 'APT 일반분양'), announced=str(announced or ''), units=row.get('TOT_SUPLY_HSHLDCO'), winner=str(row.get('PRZWNER_PRESNATN_DE') or ''), status='접수 중' if active else '접수 예정', isNew=new, url=link)
    return sorted(result.values(), key=lambda x: (x['start'], x['name']))

def fetch_source(key, endpoint):
    rows = []
    for page in range(1, 1001):
        query = urllib.parse.urlencode({'page': page, 'perPage': 1000, 'serviceKey': key})
        payload = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(BASE + endpoint + '?' + query, timeout=60) as response:
                    payload = json.load(response)
                break
            except Exception:
                if attempt == 2:
                    raise RuntimeError('청약 API 요청 실패: 인증키·활용승인·서비스 상태를 확인하세요.') from None
                time.sleep(2 ** attempt)
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
            raise RuntimeError('청약 API 응답 형식 오류')
        batch = payload['data']
        rows.extend(batch)
        total = payload.get('totalCount')
        if total is not None and len(rows) >= int(total):
            return rows
        if len(batch) < 1000:
            return rows
    raise RuntimeError('페이지 제한 초과: 불완전한 데이터 배포 중단')

def fetch(key):
    rows = []
    for endpoint, label in SOURCES.items():
        batch = fetch_source(key, endpoint)
        for row in batch:
            row['_sourceType'] = label
        rows.extend(batch)
        print(label, len(batch), '건 수집')
    return rows


def cards(items):
    folder = ROOT / 'public/cards'
    folder.mkdir(exist_ok=True)
    for item in items:
        # SVG is a downloadable image; text is escaped and long lines wrap.
        import textwrap
        lines = textwrap.wrap(item['name'], 19)[:4]
        texts = ''.join(f'<text x="76" y="{290+i*78}" font-size="58" font-weight="700">{html.escape(line)}</text>' for i, line in enumerate(lines))
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350"><rect width="1080" height="1350" fill="#f8f7f2"/><g font-family="Noto Sans CJK KR" fill="#25251f"><text x="76" y="115" font-size="32">우더기네 · 서울/경기 청약보드</text><rect x="76" y="160" width="350" height="62" rx="31" fill="#ffda35"/><text x="100" y="202" font-size="30">{html.escape(item['status'])}</text>{texts}<text x="76" y="720" font-size="30">청약 접수</text><text x="76" y="780" font-size="40">{item['start'] or '미제공'} ~ {item['end'] or '미제공'}</text><text x="76" y="900" font-size="30">공급규모 {html.escape(str(item['units'] if item['units'] is not None else '미제공'))} 세대</text><text x="76" y="1010" font-size="30">당첨자 발표 {html.escape(item['winner'] or '미제공')}</text><text x="76" y="1190" font-size="24">출처: 한국부동산원 청약홈 · 신청 전 모집공고 확인</text><text x="76" y="1240" font-size="24">분양가·자격·일정은 공식 모집공고를 확인하세요.</text></g></svg>'''
        (folder / (item['id'] + '.svg')).write_text(svg, encoding='utf-8')
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(folder / (item['id'] + '.png')))

def main():
    key = os.environ.get('APPLYHOME_SERVICE_KEY', '').strip()
    if not key:
        raise RuntimeError('APPLYHOME_SERVICE_KEY 비밀값이 필요합니다.')
    now = dt.datetime.now(KST)
    items = select(fetch(key), now.date())
    from enrich import enrich
    enrich(items)
    cards(items)
    (ROOT / "public/config.json").write_text(json.dumps({"kakaoJsKey": os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip()}), encoding="utf-8")
    data = dict(updatedAt=now.isoformat(), date=now.date().isoformat(), items=items, scope='서울/경기 APT 일반·특별·1/2순위·무순위·재공급·임의공급')
    (ROOT / 'public/data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    print(f'공고 {len(items)}건 생성 완료')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else '빌드 실패: 데이터 형식을 확인하세요.', file=sys.stderr)
        sys.exit(1)
