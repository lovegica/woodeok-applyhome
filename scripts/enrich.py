"""Kakao address geocoding in CI; only coordinates leave the server."""
import json
import os
import urllib.parse
import urllib.request


def enrich(items):
    key = os.environ.get('KAKAO_REST_API_KEY', '').strip()
    failures = 0
    for item in items:
        item['location'] = None
        if not key or not item['address']:
            continue
        query = urllib.parse.urlencode({'query': item['address'], 'analyze_type': 'exact'})
        request = urllib.request.Request('https://dapi.kakao.com/v2/local/search/address.json?' + query, headers={'Authorization': 'KakaoAK ' + key})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                docs = json.load(response).get('documents', [])
            if not docs:
                continue
            # Do not place an ambiguous result or a neighborhood centroid as a complex.
            exact = [d for d in docs if d.get('address_type') in ('ROAD_ADDR', 'REGION_ADDR')]
            if len(exact) != 1:
                continue
            doc = exact[0]
            address = doc.get('road_address') or doc.get('address') or {}
            province = address.get('region_1depth_name', '')
            if province not in ('서울', '경기', '서울특별시', '경기도'):
                continue
            if item['region'].startswith('서울') != province.startswith('서울'):
                continue
            item['location'] = {'lat': float(doc['y']), 'lng': float(doc['x']), 'district': address.get('region_2depth_name', '')}
        except Exception:
            failures += 1
    print(f'지도 좌표 {sum(bool(i["location"]) for i in items)}건 / 주소 조회 실패 {failures}건')
