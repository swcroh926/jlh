"""Public award-title collector. Python 3.10+, standard library only."""
import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import error, parse, request, robotparser
from http.cookiejar import CookieJar

BASE = Path(__file__).resolve().parent
SITES = {
    'national': ('전국', 'https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttList.do'),
    'seoul': ('서울', 'https://ssei.sen.go.kr/fus/MI000000000000000074/board/BO00000126/ctgynone/list0010v.do'),
}
AGENT = 'ScienceAwardCollector/0.1'
FIELDS = ['source', 'id', 'title', 'year', 'field', 'award', 'record_type', 'url', 'evidence', 'collected_at', 'raw_record_type', 'classification_basis']

class Listing(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cells = None
        self.cell = None
        self.row_id = None
        self.body_id = None
        self.page = None
        self.all_text = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'input' and a.get('name') in ('page', 'pageIndex'):
            self.page = a.get('value')
        if tag == 'tbody':
            m = re.search(r"fn_moveBbsNttDetail\('([0-9]+)'", a.get('onclick', ''))
            self.body_id = m[1] if m else None
            # National raw responses place TDs directly in TBODY. Browsers insert
            # TR on save. Accept both representations of the same listing row.
            if self.body_id:
                self.cells, self.row_id = [], self.body_id
        if tag == 'tr':
            self.cells, self.row_id = [], self.body_id
        if tag in ('td', 'th') and self.cells is not None:
            self.cell = []
        if tag == 'a' and self.cells is not None:
            m = re.search(r"fncDetailView\('([0-9]+)'", a.get('href', '') + a.get('onclick', ''))
            if m:
                self.row_id = m[1]
        if tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if not self.skip:
            self.all_text.append(data)
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.cells is not None:
            if self.row_id:
                self.rows.append((self.row_id, self.cells))
            self.cells, self.cell = None, None
        if tag == 'tbody':
            if self.body_id and self.cells is not None:
                self.rows.append((self.body_id, self.cells))
                self.cells, self.cell = None, None
            self.body_id = None


def classify_record(row):
    row.setdefault('raw_record_type', row.get('record_type', ''))
    if row['source'] == '전국' and row.get('record_type') == '미분류':
        row['record_type'] = '학생'
        row['classification_basis'] = '사용자 확인: 전국 미분류는 학생 작품'
    row.setdefault('classification_basis', '목록/제목 표기')
    return row


def extract(text, site, expected_page=None):
    p = Listing()
    p.feed(text)
    if expected_page is not None and p.page != str(expected_page):
        raise ValueError(f'요청 페이지 {expected_page}와 응답 페이지 {p.page!r}가 다릅니다.')
    if not p.rows:
        raise ValueError('작품 행을 찾지 못했습니다. 오류 화면·로그인 화면 또는 사이트 구조 변경을 확인하세요.')
    output = []
    for identity, v in p.rows:
        if site == 'national':
            if len(v) != 7:
                raise ValueError('전국 목록의 열 구조가 달라졌습니다.')
            year, field, title, award = v[1:5]
            kind = '지도논문' if title.startswith('(지도논문)') else '미분류'
            url = 'https://www.science.go.kr/mps/1079/bbs/423/moveBbsNttDetail.do?nttSn=' + identity
        else:
            if len(v) != 9:
                raise ValueError('서울 목록의 열 구조가 달라졌습니다.')
            award, field, title, year, kind = v[1], v[2], v[3], v[6], v[7]
            url = SITES[site][1].replace('list0010v.do', 'view0010v.do') + '?board_id=BO00000126&board_seq=' + identity
        if not title or not re.fullmatch(r'\d{4}', year):
            raise ValueError('제목 또는 연도 값이 올바르지 않습니다.')
        output.append(dict(source=SITES[site][0], id=identity, title=title, year=year,
                           field=field, award=award, record_type=kind, url=url,
                           evidence='목록 제목만', collected_at=datetime.now(timezone.utc).isoformat()))
    if len({r['id'] for r in output}) != len(output):
        raise ValueError('한 페이지에 중복 게시물 ID가 있습니다.')
    return [classify_record(row) for row in output]


def make_request(site, page):
    url = SITES[site][1]
    if site == 'national':
        return request.Request(url + '?' + parse.urlencode({'page': page}), headers={'User-Agent': AGENT})
    data = parse.urlencode({'board_id': 'BO00000126', 'pageIndex': page,
                            'searchCondition': '', 'searchKeyword': ''}).encode()
    return request.Request(url, data=data, headers={'User-Agent': AGENT, 'Referer': url})


class Client:
    def __init__(self, delay=3):
        self.opener = request.build_opener(request.HTTPCookieProcessor(CookieJar()))
        self.delay, self.last = max(3, delay), 0

    def read(self, req):
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        # Standard SSL/proxy settings; no certificate validation bypass.
        with self.opener.open(req, timeout=25) as response:
            if parse.urlparse(response.url).hostname != parse.urlparse(req.full_url).hostname:
                raise ValueError('다른 호스트로 이동하여 중단했습니다. 사이트 주소를 확인하세요.')
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('페이지 크기 제한(8MB)을 초과했습니다.')
            encoding = response.headers.get_content_charset() or 'utf-8'
            return raw.decode(encoding)

    def check_robots(self, site):
        url = SITES[site][1]
        robots_url = parse.urljoin(url, '/robots.txt')
        rp = robotparser.RobotFileParser()
        try:
            text = self.read(request.Request(robots_url, headers={'User-Agent': AGENT}))
        except error.HTTPError as e:
            if e.code == 404:
                return
            raise
        if '<html' in text.lower() or '<!doctype' in text.lower():
            raise ValueError('robots.txt 대신 HTML이 반환되어 자동 수집 허용 여부를 확인하지 못했습니다.')
        rp.parse(text.splitlines())
        if not rp.can_fetch(AGENT, url):
            raise ValueError('robots.txt에서 해당 경로의 자동 수집을 허용하지 않습니다.')
        self.delay = max(self.delay, rp.crawl_delay(AGENT) or 0)
        rate = rp.request_rate(AGENT)
        if rate and rate.requests:
            self.delay = max(self.delay, rate.seconds / rate.requests)


def atomic_text(path, content):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.replace(path)


def load_state(folder):
    path = folder / 'state.json'
    if not path.exists():
        return {'version': 1, 'records': {}, 'pages': {}}
    state = json.loads(path.read_text(encoding='utf-8'))
    if state.get('version') != 1 or not isinstance(state.get('records'), dict) or not isinstance(state.get('pages'), dict):
        raise ValueError('저장된 state.json 형식이 올바르지 않습니다. 파일을 보존하고 다른 출력 폴더를 사용하세요.')
    return state


def fingerprint(rows):
    return hashlib.sha256(','.join(sorted(r['id'] for r in rows)).encode()).hexdigest()


def remember(state, site, page, rows):
    digest = fingerprint(rows)
    key = f'{site}:{page}'
    for k, value in state['pages'].items():
        if k.startswith(site + ':') and k != key and value == digest:
            raise ValueError('다른 페이지에서 동일한 목록이 반환되어 중단했습니다.')
    for row in rows:
        state['records'][f"{site}:{row['id']}"] = row
    state['pages'][key] = digest


def category(row):
    if row.get('record_type') == '지도논문' or re.match(r'^\s*[（(]\s*지도논문\s*[)）]', row['title']):
        return 'guidance_papers'
    if row.get('record_type') == '학생':
        return 'student_projects'
    return 'unclassified'


def write_csv(path, rows):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "'" + str(row.get(k, '')) if str(row.get(k, '')).lstrip().startswith(('=', '+', '-', '@')) else row.get(k, '') for k in FIELDS})
    try:
        tmp.replace(path)
    except PermissionError:
        # An open Excel file must not stop the collection or overwrite older results.
        alternate = path.with_name(path.stem + '_latest.csv')
        try:
            tmp.replace(alternate)
            logging.warning('CSV가 열려 있어 %s에 최신 결과를 저장했습니다.', alternate)
        except PermissionError:
            logging.warning('CSV 두 파일이 잠겨 있습니다. JSON은 저장됐습니다. 엑셀을 닫고 재실행하세요: %s', tmp)


def export(folder, state):
    for row in state['records'].values():
        classify_record(row)
    atomic_text(folder / 'state.json', json.dumps(state, ensure_ascii=False, indent=2))
    rows = list(state['records'].values())
    groups = {'awards': rows,
              'projects': [r for r in rows if category(r) != 'guidance_papers']}
    for name in ('guidance_papers', 'student_projects', 'unclassified'):
        groups[name] = [r for r in rows if category(r) == name]
    for name, subset in groups.items():
        atomic_text(folder / (name + '.json'), json.dumps(subset, ensure_ascii=False, indent=2))
        write_csv(folder / (name + '.csv'), subset)
    atomic_text(folder / 'summary.json', json.dumps({
        'counts': {name: len(subset) for name, subset in groups.items()},
        'sources': state.get('sources', {}),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'note': 'projects에는 학생 여부 미확인 자료가 포함됩니다. 동일 연구의 지역/전국 중복은 별도 검토가 필요합니다.'
    }, ensure_ascii=False, indent=2))


def page_info(text, site):
    parser = Listing()
    parser.feed(text)
    plain = ' '.join(' '.join(parser.all_text).split())
    if site == 'national':
        match = re.search(r'전체\s*([\d,]+)\s*건,\s*현재 페이지\s*(\d+)\s*/\s*(\d+)', plain)
    else:
        match = re.search(r'총\s*([\d,]+)\s*건\s*(\d+)\s*/\s*(\d+)', plain)
    if not match:
        raise ValueError('전체 건수와 마지막 페이지를 확인하지 못했습니다. 전체 수집을 임의로 완료 처리하지 않습니다.')
    total, current, last = int(match[1].replace(',', '')), int(match[2]), int(match[3])
    if not (1 <= current <= last <= 100000) or total < last:
        raise ValueError('게시판의 전체 건수/페이지 값이 올바르지 않습니다.')
    return {'total_records': total, 'total_pages': last}


def parse_response(folder, text, site, page):
    try:
        return extract(text, site, page)
    except ValueError:
        diagnostic_dir = folder / 'diagnostics'
        diagnostic_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = diagnostic_dir / f'{site}-page-{page}-{stamp}.html'
        atomic_text(path, text)
        logging.error('분석용 응답 HTML 저장: %s', path.resolve())
        raise


def import_region(path, state):
    # A common entry point for verified title lists from regions with PDF/Excel sources.
    rows = []
    with path.open(encoding='utf-8-sig', newline='') as f:
        for number, record in enumerate(csv.DictReader(f), 2):
            row = {k: (record.get(k) or '').strip() for k in FIELDS}
            if not all(row[k] for k in ('source', 'id', 'title', 'year', 'url')):
                raise ValueError(f'CSV {number}행: source/id/title/year/url이 필요합니다.')
            if row['source'] in ('전국', '서울'):
                raise ValueError('지역 CSV는 전국·서울 자동 수집 자료와 분리해서 사용하세요.')
            if not re.fullmatch(r'\d{4}', row['year']) or parse.urlparse(row['url']).scheme not in ('http','https'):
                raise ValueError(f'CSV {number}행: 연도 또는 출처 URL 형식이 올바르지 않습니다.')
            row['record_type'] = row['record_type'] or '미분류'
            row['evidence'] = row['evidence'] or '사용자 제공 제목 목록'
            row['collected_at'] = datetime.now(timezone.utc).isoformat()
            rows.append(row)
    if not rows:
        raise ValueError('CSV에 가져올 자료가 없습니다.')
    identities = [(r['source'], r['id']) for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('지역 CSV 내에 같은 출처/ID가 중복됩니다.')
    for row in rows:
        state['records']['regional:' + json.dumps([row['source'], row['id']], ensure_ascii=False)] = row
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='전국·서울 과학전람회 제목 수집 (기본: 각 3페이지)')
    parser.add_argument('--site', choices=['national', 'seoul', 'both'], default='both')
    parser.add_argument('--pages', type=int, default=3, help='수집할 마지막 페이지 번호')
    parser.add_argument('--all', action='store_true', help='게시판 마지막 페이지 자동 확인 후 전체 수집')
    parser.add_argument('--import-csv', type=Path, help='검증된 다른 지역 제목 목록 CSV 가져오기')
    parser.add_argument('--export-only', action='store_true', help='인터넷 접속 없이 기존 자료를 분류해 다시 저장')
    parser.add_argument('--delay', type=float, default=3)
    parser.add_argument('--output', type=Path, default=BASE / 'output')
    parser.add_argument('--html', type=Path, help='사이트 접속 없이 저장된 HTML 1개 가져오기; --site 필수')
    args = parser.parse_args()
    if not 1 <= args.pages <= 100000:
        parser.error('페이지 번호는 1~100000 사이여야 합니다.')
    if sum(bool(x) for x in (args.html, args.import_csv, args.export_only)) > 1:
        parser.error('HTML/CSV 가져오기와 재출력은 한 번에 하나만 선택하세요.')
    if args.html and args.site == 'both':
        parser.error('--html에는 --site national 또는 --site seoul을 지정하세요.')
    args.output.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(args.output / 'collector.log', encoding='utf-8'), logging.StreamHandler()], force=True)
    failures = 0
    try:
        state = load_state(args.output)
        if args.export_only:
            export(args.output, state)
        elif args.import_csv:
            logging.info('지역 CSV %d건 가져오기 완료', import_region(args.import_csv, state))
            export(args.output, state)
        elif args.html:
            text = args.html.read_text(encoding='utf-8-sig')
            rows = extract(text, args.site)
            for row in rows:
                state['records'][f"{args.site}:{row['id']}"] = row
            export(args.output, state)
            logging.info('저장 HTML에서 %d건 추출 완료 (온라인 수집 이력과 별도).', len(rows))
        else:
            # Seoul is shorter: complete it before the long national board.
            sites = ['seoul', 'national'] if args.site == 'both' else [args.site]
            for site in sites:
                try:
                    client = Client(args.delay)
                    cached = {}
                    target = args.pages
                    if args.all:
                        client.check_robots(site)
                        first = client.read(make_request(site, 1))
                        first_rows = parse_response(args.output, first, site, 1)
                        info = page_info(first, site)
                        previous = state['pages'].get(f'{site}:1')
                        if previous and previous != fingerprint(first_rows):
                            raise ValueError('첫 페이지가 기존 실행 이후 변경됐습니다. 기존 output을 보존하고 --output output-new로 새로 수집하세요.')
                        old_info = state.get('sources', {}).get(site)
                        if old_info and old_info['total_records'] != info['total_records']:
                            raise ValueError('전체 게시물 수가 변경됐습니다. 새 출력 폴더로 수집하세요.')
                        state.setdefault('sources', {})[site] = info
                        target = info['total_pages']
                        cached[1] = first_rows
                        logging.info('%s 전체 %d건 / %d페이지. 요청 대기만 최소 약 %.0f분.',
                                     SITES[site][0], info['total_records'], target, target * client.delay / 60)
                    pending = [p for p in range(1, target + 1) if f'{site}:{p}' not in state['pages']]
                    if not pending:
                        logging.info('%s: 요청 범위는 이미 수집 완료했습니다.', SITES[site][0])
                        if args.all:
                            collected = sum(k.startswith(site + ':') for k in state['records'])
                            if collected != info['total_records']:
                                raise ValueError('완료 이력과 저장 건수가 일치하지 않습니다. 별도 출력 폴더에서 다시 확인하세요.')
                        continue
                    if not args.all:
                        client.check_robots(site)
                    for page in pending:
                        logging.info('%s %d/%d페이지 요청', SITES[site][0], page, target)
                        rows = cached.get(page)
                        if rows is None:
                            response_text = client.read(make_request(site, page))
                            rows = parse_response(args.output, response_text, site, page)
                        remember(state, site, page, rows)
                        # Checkpoint each page; large CSV exports every ten pages or at end.
                        atomic_text(args.output / 'state.json', json.dumps(state, ensure_ascii=False))
                        if page % 10 == 0 or page == target:
                            export(args.output, state)
                        done = sum(f'{site}:{n}' in state['pages'] for n in range(1, target + 1))
                        logging.info('%s 진행률 %.1f%% (%d/%d), 이번 페이지 %d건 저장',
                                     SITES[site][0], done * 100 / target, done, target, len(rows))
                    if args.all:
                        collected = sum(k.startswith(site + ':') for k in state['records'])
                        expected = state['sources'][site]['total_records']
                        if collected != expected:
                            raise ValueError(f'페이지 순회 완료 후 건수 불일치: 예상 {expected}, 저장 {collected}. 신규/삭제 게시물 또는 겹치는 페이지를 점검하세요.')
                except (error.URLError, OSError, ValueError, UnicodeError) as e:
                    failures += 1
                    logging.error('%s 수집 중단: %s. 기존 성공 결과는 유지됩니다.', SITES[site][0], e)
                except KeyboardInterrupt:
                    export(args.output, state)
                    raise
            export(args.output, state)
        logging.info('저장된 전체 목록: %d건. 결과 위치: %s', len(state['records']), args.output.resolve())
        logging.info('완료된 페이지는 재실행 시 건너뜁니다. 최신 목록 재수집은 새 출력 폴더를 사용하세요.')
        return 1 if failures else 0
    except (OSError, ValueError, error.URLError) as e:
        logging.error('작업 실패: %s', e)
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\n사용자가 중단했습니다. 이미 저장된 페이지는 유지됩니다.')
        sys.exit(130)
