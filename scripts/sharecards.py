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
    # Large, high-contrast mobile reading grid. Sources remain in site metadata.
    box(0,0,W,78,navy)
    text(46,24,'우더기네  청약노트',30,'white')
    text(800,27,str(today).replace('-','.'),23,'#D9E3E5',240)
    text(48,106,review['eyebrow'],27,muted)
    text(44,154,review['headline'][0].replace(' 대단지',''),66)
    text(44,232,review['headline'][1],66)
    hero_path = ROOT / 'public' / review.get('hero', 'assets/apartment-ai-concept.png')
    hero = Image.open(hero_path).convert('RGB')
    hero = ImageOps.fit(hero,(984,322),method=Image.Resampling.LANCZOS,centering=(.5,.48))
    canvas.paste(hero,(48,316))
    box(48,607,984,31,navy)
    text(64,615,('공식 CG · 실제와 다를 수 있습니다' if review.get('hero') else 'AI 컨셉 이미지 · 실제 단지 아님'),19,'white')
    box(48,658,984,111,'white',16)
    for x,label,value in [(72,'단지 전체',f"{review['complexUnits']:,}세대"),(392,'이번 모집',f"{item['units']:,}세대"),(709,'입주 예정',review['moveIn'])]:
        text(x,676,label,25,muted,280)
        text(x,717,value,39,ink,280)
    box(48,789,984,142,yellow,16)
    text(72,806,'전용 84㎡ 분양가',29,ink,440)
    text(72,852,f"{review['price84MinManwon']/10000:.2f}~{review['price84MaxManwon']/10000:.2f}억원",59,ink,920)
    text(648,809,review['priceNote'].replace('이번 공급 ', '').replace(' 기준', ''),23,ink,350)
    text(52,955,'입지',25,muted,100)
    text(157,950,review['locationLine'],33,ink,870)
    text(52,1010,'조건',25,muted,100)
    text(157,1004,review['conditions'][0],36,ink,870)
    text(157,1054,review['conditions'][1],28,ink,870)
    box(48,1111,984,113,navy,16)
    text(72,1129,'청약 접수',25,'#C5D3D7',230)
    text(72,1171,review['receiptLabel'],42,yellow,370)
    text(466,1129,'발표 / 계약',25,'#C5D3D7',520)
    text(466,1175,review['resultLabel'],31,'white',540)
    text(52,1244,review['caution'],24,muted)
    box(0,1290,1080,150,navy)
    handle = '@woodeok.apt'
    handle_font = ImageFont.truetype(fontfile, 46)
    handle_x = (W - d.textlength(handle, font=handle_font)) / 2
    text(handle_x,1343,handle,46,'white',1000)
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
