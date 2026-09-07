import csv
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    queue_path = Path('state/queue.json')
    queue = json.loads(queue_path.read_text(encoding='utf-8'))
    cache_path = Path('state/video-titles.json')
    titles = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    failures = {}
    for index, item in enumerate(queue, 1):
        bvid = item['id']
        if bvid in titles:
            continue
        try:
            request = Request(
                f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
                headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/'},
            )
            with urlopen(request, timeout=20) as response:
                payload = json.load(response)
            if payload.get('code') != 0:
                raise RuntimeError(f"API {payload.get('code')}: {payload.get('message')}")
            data = payload['data']
            if data.get('bvid') != bvid or not data.get('title', '').strip():
                raise RuntimeError('invalid video identity or empty title')
            titles[bvid] = data['title']
        except Exception as error:
            failures[bvid] = str(error)
        if index % 25 == 0:
            cache_path.write_text(json.dumps(titles, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f'{index}/{len(queue)} checked; {len(titles)} titles; {len(failures)} failures', flush=True)
        time.sleep(0.5)
    cache_path.write_text(json.dumps(titles, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for item in queue:
        if item['id'] in titles:
            item['title'] = titles[item['id']]
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for path in Path('transcripts').glob('BV*.txt'):
        if path.stem in titles:
            text = path.read_text(encoding='utf-8')
            text = re.sub(r'^标题：[^\r\n]*', lambda match: '标题：' + titles[path.stem], text, count=1, flags=re.MULTILINE)
            path.write_text(text, encoding='utf-8')
    output = Path('classification')
    json_path = output / 'video-classification.json'
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    for item in payload['videos']:
        item['title'] = titles.get(item['bvid'], '')
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    csv_path = output / 'video-classification.csv'
    with csv_path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    for item in rows:
        item['title'] = titles.get(item['bvid'], '')
    with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output / 'title-refresh-report.json').write_text(json.dumps({
        'source': 'https://api.bilibili.com/x/web-interface/view',
        'queue_total': len(queue), 'resolved': len(titles), 'failures': failures,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Completed: {len(titles)} titles, failures={failures}', flush=True)


if __name__ == '__main__':
    main()
