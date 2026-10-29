"""Evidence-bound editorial share cards. API numbers never stand in for complex totals."""
import datetime as dt
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from decimal import Decimal, InvalidOperation

ROOT = Path(__file__).resolve().parents[1]
POLICY = {'complexMinUnits': 500, 'price84OverManwon': 100000, 'noticeMinUnits': 0,
          'regions': ['서울', '경기'], 'priceAreaMin': 84, 'priceAreaMaxExclusive': 85}


def price84(models):
    values = []
    for row in models:
        try:
            area = Decimal(re.match(r'^\d+(?:\.\d+)?', str(row.get('HOUSE_TY', '')))[0])
            price = Decimal(str(row.get('LTTOT_TOP_AMOUNT', '')).replace(',', '').strip())
            if 84 <= area < 85 and price > 0:
                values.append(int(price))
        except (InvalidOperation, TypeError):
            continue
    return {'minTypeTopManwon': min(values), 'maxTypeTopManwon': max(values),
            'basis': '청약홈 주택형별 최고 공급금액 · 실제 최저가 아님'} if values else None


def qualifies(item, complex_units=None):
    # A notice with >=500 units proves a lower bound, never its exact complex total.
    total_lower_bound = complex_units or item.get('units') or 0
    return (item['region'].startswith(('서울', '경기')) and int(total_lower_bound) >= 500
            and bool(item.get('price84')) and item['price84']['maxTypeTopManwon'] > 100000)


def load_reviews():
    return json.loads((ROOT / 'editorial/reviewed_cards.json').read_text(encoding='utf-8'))


def review_matches(item, review, today):
    return (item['name'] == review['name'] and item['units'] == review['noticeUnits']
            and item['start'] == review['start'] and item['end'] == review['end']
            and item['end'] >= str(today)
            and 0 <= (today - dt.date.fromisoformat(review['reviewedAt'])).days <= 7
            and review['price84MinManwon'] > 100000
            and review['complexUnits'] >= 500)


def font_path():
    paths = [os.environ.get('CARD_FONT', ''), str(Path.home()/'.local/share/fonts/NotoSansCJKkr-Bold.otf'),
             str(Path.home()/'.local/share/fonts/NotoSansCJKkr-Regular.otf'),
             '/System/Library/Fonts/AppleSDGothicNeo.ttc']
    return next((p for p in paths if p and Path(p).is_file()), None)


def render(item, review, today, folder):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    W, H = 1080, 1440
    navy, ink, muted, yellow = '#112631', '#142830', '#627078', '#FFDC45'
    canvas = Image.new('RGB', (W, H), '#F5F4EE')
    d = ImageDraw.Draw(canvas)
    fontfile = font_path()
    if not fontfile:
        raise RuntimeError('공유 카드 한국어 글꼴 누락')
    def text(x, y, value, size=32, color=ink, max_width=960):
        font = ImageFont.truetype(fontfile, size)
        if d.textlength(value, font=font) > max_width:
            raise RuntimeError('공유 카드 문구 폭 초과: 편집 검수 필요')
        d.text((x,y), value, font=font, fill=color, anchor='lt')
    def box(x,y,w,h,fill,r=0):
        d.rounded_rectangle((x,y,x+w,y+h),radius=r,fill=fill)
    # Fixed editorial grid: headline > actual rendering > facts > conditions > dates.
    box(0,0,W,80,navy)
    text(46,25,'우더기네   |   핵심 청약 브리핑',27,'white')
    text(800,27,str(today).replace('-','.'),23,'#D9E3E5',240)
    text(48,111,review['eyebrow'],28,muted)
    text(44,157,review['headline'][0],65)
    text(44,235,review['headline'][1],65)
    hero_path = ROOT / 'public' / review.get('hero', 'assets/apartment-ai-concept.png')
    hero = Image.open(hero_path).convert('RGB')
    hero = ImageOps.fit(hero,(984,385),method=Image.Resampling.LANCZOS,centering=(.5,.48))
    canvas.paste(hero,(48,326))
    box(48,665,984,46,navy)
    text(65,678,(review['imageCaption'] if review.get('hero') else 'AI 컨셉 이미지 · 실제 단지 외관이 아닙니다'),20,'white')
    box(48,731,984,106,'white',14)
    text(72,749,'단지 전체',23,muted,270)
    text(72,784,f"{review['complexUnits']:,}세대",36,ink,270)
    text(392,749,'이번 모집',23,muted,270)
    text(392,784,f"{item['units']:,}세대",36,ink,270)
    text(709,749,'입주 예정',23,muted,280)
    text(709,784,review['moveIn'],36,ink,280)
    box(48,855,984,105,yellow,14)
    text(72,874,'전용 84㎡ 공급가격',25,ink,390)
    text(72,913,review['priceNote'],19,ink,410)
    text(485,880,f"{review['price84MinManwon']/10000:.2f}~{review['price84MaxManwon']/10000:.2f}억",46,ink,525)
    text(52,983,'입지',24,muted,110)
    text(157,979,review['locationLine'],30,ink,860)
    text(52,1030,'조건',24,muted,110)
    text(157,1026,review['conditions'][0],30,ink,860)
    text(157,1070,review['conditions'][1],25,ink,860)
    box(48,1123,984,106,navy,14)
    text(72,1141,'청약 접수',23,'#C5D3D7',230)
    text(72,1178,review['receiptLabel'],37,yellow,370)
    text(470,1141,'발표 / 계약',23,'#C5D3D7',520)
    text(470,1180,review['resultLabel'],29,'white',540)
    text(52,1251,review['caution'],23,'#785D36')
    text(52,1296,'공식 공고 '+review['noticeDate']+'  ·  '+review['sourceLabel'],20,muted)
    text(52,1327,'가격·자격·일정은 변경될 수 있습니다. 신청 전 최신 공고 확인',20,muted)
    box(0,1370,1080,70,navy)
    text(47,1394,'@woodeok.apt',28,'white',410)
    text(460,1399,'lovegica.github.io/woodeok-applyhome',20,'#DAE4E7',580)
    filename = item['id'] + '-news.png'
    canvas.save(folder/filename, optimize=True)
    return 'cards/'+filename


def source_unchanged(review):
    try:
        with urllib.request.urlopen(review['sourceUrl'], timeout=30) as response:
            return hashlib.sha256(response.read()).hexdigest() == review['sourceSha256']
    except Exception:
        return False


def build_sharecards(items, today):
    folder = ROOT/'public/cards'
    folder.mkdir(exist_ok=True)
    for old in folder.glob('*-news.png'):
        old.unlink()
    reviews = load_reviews()
    ready, pending = [], []
    for item in items:
        review = reviews.get(item['id'])
        if review:
            item['complexUnits'] = review['complexUnits']
            item['complexUnitsSource'] = review['sourceUrl']
        if review and review_matches(item, review, today) and source_unchanged(review):
            item['newsCard'] = render(item, review, today, folder)
            item['newsCardSource'] = review['sourceUrl']
            item['newsCardReviewedAt'] = review['reviewedAt']
            item['price84Reviewed'] = {k: review[k] for k in ('price84MinManwon','price84MaxManwon','priceNote')}
            ready.append({'id':item['id'],'name':item['name'],'image':item['newsCard'], 'source':review['sourceUrl']})
        elif review or qualifies(item, item.get('complexUnits')) or (item.get('price84') and item['price84']['maxTypeTopManwon'] > 100000):
            pending.append({'id':item['id'],'name':item['name'],'reason':'공식 총 세대수·자격·가격표 검토 필요'})
    manifest = {'date':str(today),'policy':POLICY,'cards':ready,'pendingReview':pending}
    (ROOT/'public/sharecards.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    if ready:
        from zipfile import ZipFile, ZIP_DEFLATED
        with ZipFile(folder/'woodeok-news-cards.zip','w',ZIP_DEFLATED) as z:
            for card in ready:
                z.write(ROOT/'public'/card['image'],Path(card['image']).name)
    else:
        (folder/'woodeok-news-cards.zip').unlink(missing_ok=True)
    print('핵심 카드',len(ready),'건 / 검토 대기',len(pending),'건')
    return manifest
