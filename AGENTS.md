# JLH — 탐구의 씨앗

## 서비스 목적

JLH는 학원 선생님이 과학전람회에 출전하는 학생을 지도하는 전 과정을 지원하는 웹앱이다. 학생의 관심사와 학년, 예산, 준비 기간, 장소, 장비를 반영해 탐구를 계획하고, 학생과 선생님이 각 판단의 근거를 확인할 수 있게 한다. 학생과 선생님이 후보를 비교해 최종 주제를 선택하고, 선생님이 실험 계획을 검토해 확정한다.

## 학생 지도 흐름

1. **아이디어 생성 및 선정** — 학생이 입력한 원본 주제에서 관심사를 분석하고 기존 수상작과의 중복 위험과 수행 가능성을 확인한다. 필요한 경우 새 주제를 제안해 같은 기준으로 검사·평가한다.
2. **실험 설계 및 진행** — 선정한 주제를 검증할 실험 계획을 세운다. 계획에는 단계별 가설·변수·측정·기록 방법, 준비물·비용, 일정, 안전 유의 사항을 담아 실제 수행에 활용할 수 있게 한다.
3. **결과 분석 및 결론 도출** — 실제로 기록한 관찰과 측정값을 바탕으로 결과를 분석하고, 가설과 비교해 근거와 한계를 드러내는 결론을 도출한다.
4. **보고서 완성** — 탐구 질문, 실험 방법, 실제 결과, 결론과 출처를 이어 학생과 선생님이 검토할 수 있는 보고서를 완성한다.

## 현재 개발 기준

- 상세 요구사항은 Notion의 **기능명세서 v1.0 및 v1.1 추가 명세**를 기준으로 한다. 저장소에서는 [명세 사본](docs/FUNCTIONAL_SPEC_v1.1.md), [명세와 구현 비교](docs/SPEC_GAP_ANALYSIS.md), [개발 기록](docs/DEVELOPMENT_LOG.md)을 참고한다.
- 첫 구현의 완료 범위는 학생·원본 주제 입력 → `Find_Interest` → `Check_Duplicate` → `Eval_Topic` → 필요 시 `Create_Topic`과 재검사·재평가 → 최종 주제 선택 → `Set_Exp`로 이어지는 실험 계획과 로컬 검증이다. 입력과 확인 화면에서 필요한 정보를 보완한다. 실험 진행을 위한 추가 기능, 결과 분석·보고서, 선생님 로그인·대시보드, 공개 배포는 후속 범위다.
- 사용자가 확정한 후보 한도는 원본 최대 20개와 생성 최대 10개, 합계 최대 30개다. 관심사 분석의 근거는 학생이 입력한 원본 주제에서 가져온다. 자동 생성·재평가는 한 차례로 제한하고 추가 생성은 사용자 실행으로 진행한다.
- 추천에는 반올림 전 가중 총점 80점 이상, 실행 가능 상태, 중복 위험 검토 상태를 함께 적용한다. 중복 위험은 확보한 자료 범위와 판단 근거를 함께 보여준다. 검색 실패는 검사 미완료로 표시하고, 수상 가능성 예측과 표절 확정 판정은 범위에서 제외한다.
- Python 서버가 입력·AI 출력 검증, 기능 실행 순서, 총점·순위·비용·일정 계산과 결과 저장을 담당한다. AI는 관심사 분류, 평가 근거, 새 주제 및 실험 계획 초안 작성을 지원한다. 학생 이름과 지역은 AI 요청에서 제외한다. 검색 출처와 가격은 확인한 정보에 근거해 표시하며 추정값을 구분한다.
- 원본 주제, 선생님 검토, 평가 결과와 계획 버전을 보존한다. 수행 조건이나 근거가 바뀌면 영향을 받는 결과에 재평가·재검사 필요를 표시한다.

## Project collaboration

- The user wants periodic, plain-Korean development summaries. At meaningful milestones (features, fixes, dataset changes, tests, deployment), update `docs/DEVELOPMENT_LOG.md` with the current state and evidence.
- Distinguish local development, GitHub commits, GitHub Pages frontend deployment, public backend deployment, mocked tests, and actual provider calls. Do not claim live AI readiness from mocked tests or key presence.
- Keep the shareable Markdown copy at `/workspace/deliverables/탐구의씨앗-개발과배포기록.md` in sync when that workspace directory is available. Mention the updated document in the final reply.
- Never record API key values, full environment dumps, or sensitive raw provider logs in the development log.

### Explain work for a beginner (user preference)

- Before each stage, explain the user-facing capability in plain Korean, why it is next, and what changes in the screen, Python server, AI model and storage.
- At meaningful milestones, explain what now works and what happens next. Connect file/command details to their role in the service.
- For errors, explain the cause, user impact and intended fix. Explain material departures from the agreed requirements before implementing them; do not stop for routine approval.
- At completion, provide a concrete before/after example, the screen/input/button sequence for user testing, and distinguish mocked responses, live AI calls, local execution and public deployment.
- Briefly update completed vs remaining specification stages. Continue authorized work without repeatedly seeking confirmation.
