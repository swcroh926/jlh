# 지역 과학전람회 수상작 수집 기록

수집일: 2026-11-18. 전국대회·서울 자료는 신규 수집 대상에서 제외했습니다. 교육청 산하 과학교육원·융합교육원 공식 사이트도 포함했습니다.

**서울을 제외한 16개 지역 중 6개 지역에서 759건을 추가했습니다. 전체 지역 또는 전체 연도 수집이 완료된 상태가 아닙니다.** 기존 3,053건을 보존하여 총 3,812건입니다. 연도 지정이 없어 이번 수집은 확인 가능한 2025–2026년 결과 파일을 중심으로 진행했습니다.

## 확보한 원본

| 지역 | 연도 | 파일 | 추가 건수 | 공식 게시물 |
|---|---|---|---:|---|
| 경기 | 2026 | [gyeonggi-2026.pdf](../data/regional-sources/gyeonggi-2026.pdf) | 127 | [출처](https://www.gise.kr/gise/na/ntt/selectNttInfo.do?mi=10738&bbsId=6142&nttSn=1200399) |
| 광주 | 2026 | [gwangju-2026.pdf](../data/regional-sources/gwangju-2026.pdf) | 44 | [출처](https://gice.gen.go.kr/board.es?mid=a10301030200&bid=0007&act=view&list_no=16250) |
| 광주 | 2025 | [gwangju-2025.pdf](../data/regional-sources/gwangju-2025.pdf) | 42 | [출처](https://gice.gen.go.kr/board.es?mid=a10301030200&bid=0007&act=view&list_no=12639) |
| 인천 | 2026 | [incheon-2026.xlsx](../data/regional-sources/incheon-2026.xlsx) | 198 | [출처](https://aicei.ice.go.kr/ienet/na/ntt/selectNttInfo.do?mi=1140&nttSn=126894&bbsId=1037) |
| 제주 | 2026 | [jeju-2026.xlsx](../data/regional-sources/jeju-2026.xlsx) | 116 | [출처](https://org.jje.go.kr/cisec/board/view.jje?boardId=BBS_0000241&dataSid=97858&menuCd=DOM_000000204005001000) |
| 제주 | 2025 | [jeju-2025.xlsx](../data/regional-sources/jeju-2025.xlsx) | 89 | [출처](https://org.jje.go.kr/cisec/board/view.jje?boardId=BBS_0000241&dataSid=87811&menuCd=DOM_000000204005001000) |
| 경북 | 2026 | [gyeongbuk-2026.xlsx](../data/regional-sources/gyeongbuk-2026.xlsx) | 21 | [출처](https://www.gbe.kr/gsei/na/ntt/selectNttInfo.do?mi=9981&nttSn=1620503) |
| 경북 | 2025 | [gyeongbuk-2025.xlsx](../data/regional-sources/gyeongbuk-2025.xlsx) | 0 | [출처](https://www.gbe.kr/gsei/na/ntt/selectNttInfo.do?mi=9981&nttSn=1519560) |
| 경남 | 2025 | [gyeongnam-2025.pdf](../data/regional-sources/gyeongnam-2025.pdf) | 122 | [출처](https://gnse.gne.go.kr/gnse/na/ntt/selectNttInfo.do?mi=5733&bbsId=1394&nttSn=2849711) |

다운로드 URL·파일 크기·SHA-256은 [manifest](../data/regional-sources/manifest.json)에 기록했습니다. 원본은 기관이 공개한 파일 그대로이며 개인정보가 포함될 수 있습니다. 검색용 JSON에는 성명·학교·지도교사 정보를 추가하지 않았습니다.

## 정규화와 제외 기준

- 기존 3,053건을 값과 순서 그대로 보존했습니다. 출처+ID로 고유성을 검사하며, 지역대회와 전국대회의 동명 작품은 별도 수상 기록으로 유지합니다.
- 추가 레코드와 행별 제외 기록은 [수집 스냅샷](../data/regional/2026-11-18.json)에 있습니다. 각 항목의 evidence에 시트·행 또는 PDF 근거를 남겼습니다.
- PDF 제목은 좌표로 열을 분리하고 줄바꿈을 공백으로 연결했습니다. PDF에 따른 단어 중간 공백이 남을 수 있으며, 제목 검색에서는 공백을 정규화합니다.
- 경기는 212행 중 상훈이 확인되는 127건을 반영하고 상훈 공란 85행을 제외했습니다.
- 경남은 학생부 125행 중 미출품 3행을 제외한 122건을 반영했습니다. 교원부 미출품은 반영하지 않았습니다.
- 경북 2026년은 학생 결과의 마스킹된 제목을 임의 복원하지 않았습니다. 출품번호로 전국 출품 목록의 완전한 제목과 대조 가능한 21건만 반영했습니다. 나머지 학생 114행과 수상이 확인되지 않는 교원 행은 제외했습니다. 2025년 파일도 제목 마스킹으로 추가하지 않았습니다.
- 인천 원문의 전국특상, 경북 원문의 특상(전국)은 지역 결과 파일의 표기를 그대로 보존했습니다. 이를 전국대회 본상 수상으로 바꾸어 기록하지 않았습니다.
- 광주 교원 작품 4건은 raw_record_type=교원, record_type=확인 필요로 보존했습니다. 학생으로 분류하지 않았습니다. 나머지 추가 755건은 공식 학생부 표기에 근거합니다.

## 아직 확보하지 못한 10개 지역

아래는 이번 접근·검색 결과이며 자료가 존재하지 않는다는 뜻이 아닙니다. 로그인 우회나 TLS 검증 해제는 하지 않았습니다.

| 지역 | 확인한 공식 경로 | 미확보 사유 |
|---|---|---|
| 부산 | [공식 경로](https://home.pen.go.kr/bicce/cm/cntnts/cntntsView.do?cntntsId=597&mi=9520) | 작품 메뉴에 접근 확인 함수가 연결됨. 공개 결과 원본 미확보 |
| 대구 | [공식 경로](https://www.dge.go.kr/dicce/main.do) | SSO 리다이렉트 후 잘못된 요청 응답. 결과 원본 미확보 |
| 대전 | [공식 경로](https://desre.djsch.kr/boardCnts/list.do?boardID=98821&m=040302&s=des) | 확인한 목록은 운영 계획·요강 중심. 지역 수상작 결과 원본 미확보 |
| 울산 | [공식 경로](https://use.go.kr/usm/training/scienceex/scienceex_01.jsp) | TLS 인증서 체인 오류로 원본 다운로드 실패 |
| 강원 | [공식 경로](https://www.gwedu.go.kr/) | TLS 오류·연결 시간 초과로 결과 원본 미확보 |
| 세종 | [공식 경로](https://www.sje.go.kr/sje/ad/ofcrk/ofcrkDeptInfo.do?deptSn=581&mi=52203) | 담당 부서 확인. 공개 수상작 목록 원본 미확보 |
| 충북 | [공식 경로](https://www.cbnse.go.kr/sub.php?menukey=99) | 확인한 목록은 운영 계획·양식 중심. 결과 원본 미확보 |
| 충남 | [공식 경로](https://www.cnse.or.kr/main/board/list.action?q=8f2cfeed46fc96b57b5ed2698747f99ff34fc665e687e4afd322356788a36b81) | 확인한 목록은 운영 계획 중심. 결과 원본 미확보 |
| 전북 | [공식 경로](https://office.jbedu.kr/jise/M01060301/index.do) | 확인한 목록은 운영 계획·포스터 중심. 결과 원본 미확보 |
| 전남 | [공식 경로](https://jncce.jge.go.kr/jnse_da/na/ntt/selectNttList.do?mi=10210415&bbsId=10215722) | 공식 이전 주소 확인. 현재 목록은 계획·양식 중심, 결과 원본 미확보 |

## 앱 반영

출처 필터를 데이터 메타정보에서 생성하고, 검색·중복 검사·평가·주제 생성의 출처 링크 허용 목록에 확보한 6개 기관의 정확한 호스트를 추가했습니다. 기존 의미 검색 색인은 데이터 버전이 다르므로 재생성이 필요합니다. 이번 작업에서 유료 API 호출이나 의미 검색 색인 재생성, 서비스 배포는 하지 않았습니다.
