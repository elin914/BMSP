# BMSP

2D-PBMSP-TW-RC 문제(2차원 배치 묶기 + 병렬 배치 기계 스케줄링)를 푸는 코드.

## 설치

```bash
pip install -r requirements.txt
```

CP 모델(`CP`, `RCP`, `CPGrouper`, `CPSolver`)은 CP Optimizer가 필요하다.
pip로 설치되는 `cplex`는 Community Edition이라 탐색 공간이 2^1000을 넘으면
`Problem size limit exceeded` 에러가 난다 (변수 수가 아니라 변수 도메인 크기에 따라 정해짐).
가상 데이터 크기 A, 기계 4대 기준으로 측정한 한계:

| 모델 | Community Edition으로 실행됨 | 한계 초과 |
|---|---|---|
| 2단계 CP (`Sequential_Integrated`) | job 360개 (배치 120~130개) | job 600개 |
| 통합 CP (`Integrated_*`) | job 60개 | job 120개 |

이보다 큰 인스턴스는 IBM ILOG CPLEX Optimization Studio(학술 라이선스 등)가 필요하다.

## 실행

저장소 루트에서 실행한다 (데이터 `./data`, 결과 `./results` 경로가 루트 기준).

```bash
python model/main.py --synthetic             # config.py 설정 + 가상 데이터로 한 번 실행 (+ 해 검증)
python model/main.py                         # config.py 설정 + 실제 데이터로 한 번 실행
python model/run_experiment.py --list        # 실험 목록
python model/run_experiment.py A_phase1      # 실험 실행 -> results/A_phase1_<시각>.csv
python model/run_experiment.py A_phase1 --limit 2   # 앞의 인스턴스 2개만 (코드 확인용)
python model/run_checks.py                   # 모든 모델 조합의 해 타당성 검사 (--full, --slow)
```

새 실험은 `model/experiments.py`의 `EXPERIMENTS`에 정의를 하나 추가하면 된다.
실험 결과 CSV에서 실패한 칸은 빈 칸으로 남고 `failed` 열에 모델 이름이 적히며,
에러 내용은 같은 이름의 `.log` 파일에 남는다.

## 구조

- `model/config.py`: 실험 설정 (`model_type`, 알고리즘 선택, GA 파라미터 등)
- `model/data.py`: 가상 데이터 생성(`make_data`), 실제 데이터 로드(`load_data`)
- `model/models/`
  - `grouping_sequencers.py`: 1단계 job 순서 (EDD, SST, SA, LA, RKGA, BRKGA, OBRKGA, SimA, Tabu)
  - `groupers.py`: 2D 배치 묶기 (BFF, ABFF)
  - `scheduling_sequencers.py`: 2단계 배치 순서 (EDD, LDD, MB, RKGA, BRKGA, OBRKGA, SimA, Tabu)
  - `schedulers.py`: 배치 스케줄링 휴리스틱 (GL, IBH, BW, RBW)
  - `integrated_*.py`: CP 모델 (CPSolver, CPGrouper, CP/RCP 스케줄러)
  - `builder.py`: `model_type`에 따라 모델 조립
- `model/experiments.py`: 실험 정의, `model/run_experiment.py`: 실험 실행기
- `model/experiment_utils.py`: 실험 결과 CSV/에러 로그 기록 (`ResultLogger`)
- `model/validate.py`: 해 타당성 검사, `model/run_checks.py`: 모든 조합 검사 실행

`RBW`, `RCP`, `load_data`는 실제 데이터 실적 비교용으로 나중에 추가한 부분이라 엄밀하지 않다.

## 향후 할 일

- CP Optimizer(docplex)를 오픈소스 솔버(예: OR-Tools CP-SAT)로 전환.
  CP-SAT에도 interval 변수, `NoOverlap`, `Cumulative`, 2D 배치용 `NoOverlap2D`가 있어 모델 대부분을 옮길 수 있다.
  RCP의 휴일 처리(`intensity`)는 대응 기능이 없어 다른 방식으로 모델링해야 한다.
