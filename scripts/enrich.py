"""Geocode parcel addresses in CI, retaining lookup diagnostics without secrets."""
import datetime as dt
import json
import os
import re
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def candidates(value):
    clean = re.split(r'[\[(]', value)[0]
    clean = re.sub(r'\s*일원.*$', '', clean).strip()
    clean = re.sub(r'(\d)번지', r'\1', clean)
    values = [value, clean]
    # Preserve full parcel addresses embedded in parentheses (development blocks).
    for embedded in re.findall(r'[\[(]([^\[\]()]+)[\])]', value):
        if embedded.strip().startswith(('서울', '경기')):
            values.extend(candidates(embedded))
    values = [re.sub(r'\s*일원.*$', '', v).strip() for v in values]
    if '화성' in clean:
        legacy = clean.replace('화성특례시', '화성시')
        legacy = re.sub(r'화성시\s+(동탄구|만세구|효행구|병점구)\s+', '화성시 ', legacy)
        values.append(legacy)
    values += [re.sub(r'산\s+(?=\d)', '산', v) for v in values]
    return list(dict.fromkeys(v for v in values if v))


def match_document(docs, item, query):
    # Require a full parcel/road address, a unique result and matching province.
    exact = [d for d in docs if d.get('address_type') in ('ROAD_ADDR', 'REGION_ADDR')]
    if len(exact) != 1:
        return None
    doc = exact[0]
    parcel = re.search(r'(\S+(?:동|리))\s+(산\s*)?(\d+)(?:-(\d+))?', query)
    road = re.search(r'(\S+(?:대로|로|길))\s+(\d+)(?:-(\d+))?', query)
    if not parcel and not road:
        return None
    address = (doc.get('address') if parcel else doc.get('road_address')) or {}
    # A matching province alone is insufficient: require city/district as well.
    for district in re.findall(r'(\S+(?:시|군|구))(?=\s)', query):
        if district in ('서울특별시', '경기도', '화성특례시'):
            continue
        if district not in (address.get('region_2depth_name', '') + ' ' + address.get('region_3depth_name', '')):
            return None
    if road:
        name, main, sub = road.groups()
        if address.get('road_name') != name or str(address.get('main_building_no')) != main or str(address.get('sub_building_no') or '0') != str(sub or '0'):
            return None
    province = address.get('region_1depth_name', '')
    if province not in ('서울', '경기', '서울특별시', '경기도'):
        return None
    if item['region'].startswith('서울') != province.startswith('서울'):
        return None
    # For parcel queries, validate neighborhood and lot number in the result.
    parcel = re.search(r'(\S+(?:동|리))\s+(산\s*)?(\d+)(?:-(\d+))?', query)
    if parcel:
        neighborhood, mountain, main, sub = parcel.groups()
        if address.get('region_3depth_name') != neighborhood:
            return None
        if str(address.get('main_address_no', '')).lstrip('0') != main.lstrip('0'):
            return None
        if str(address.get('sub_address_no') or '0').lstrip('0') != str(sub or '0').lstrip('0'):
            return None
        if (address.get('mountain_yn') == 'Y') != bool(mountain):
            return None
    lat, lng = float(doc['y']), float(doc['x'])
    if not (33 <= lat <= 39 and 124 <= lng <= 132):
        return None
    return {'lat': lat, 'lng': lng, 'district': address.get('region_2depth_name', ''), 'accuracy': 'parcel' if parcel else 'road', 'provider': 'Kakao Local address', 'query': query, 'matchedAddress': doc.get('address_name', ''), 'verifiedAt': dt.datetime.now(dt.timezone.utc).isoformat()}


def verified_location(item):
    records = json.loads(Path(__file__).with_name('verified_locations.json').read_text())
    record = records.get(item['id'])
    # Bind evidence to both the specific notice and its name, never a fuzzy name match.
    if record and record['name'] == item.get('name'):
        return {k: v for k, v in record.items() if k != 'name'}
    return None


def enrich(items):
    key = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    for item in items:
        item['location'] = verified_location(item)
        if item['location']:
            item['locationStatus'] = 'verified_source'
            print('지도 공식 위치 확인:', item['id'])
            continue
        item['locationStatus'] = 'key_missing' if not key else 'not_found'
        if not key or not item['address']:
            continue
        for query in candidates(item['address']):
            encoded = urllib.parse.urlencode({'query': query, 'analyze_type': 'exact'})
            request = urllib.request.Request('https://dapi.kakao.com/v2/local/search/address.json?' + encoded, headers={'Authorization': 'KakaoAK ' + key})
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    docs = json.load(response).get('documents', [])
                item['location'] = match_document(docs, item, query)
                if not item['location'] and docs:
                    print('주소 대조 불일치:', item['id'], query, json.dumps([{k: d.get(k) for k in ('address_type', 'address_name', 'address', 'road_address')} for d in docs], ensure_ascii=False))
                if item['location']:
                    item['locationStatus'] = 'matched'
                    break
            except urllib.error.HTTPError as error:
                item['locationStatus'] = 'http_' + str(error.code)
                break
            except Exception:
                item['locationStatus'] = 'lookup_error'
                break
        print('지도 주소 확인:', item['id'], item['locationStatus'])
    print(f'지도 좌표 {sum(bool(i["location"]) for i in items)}건 / 총 {len(items)}건')
