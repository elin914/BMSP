# BMSP

2D-PBMSP-TW-RC 문제(2차원 배치 묶기 + 병렬 배치 기계 스케줄링)를 푸는 코드.

## 설치

```bash
pip install -r requirements.txt
```

CP 모델(`CP`, `RCP`, `CPGrouper`, `CPSolver`)은 CP Optimizer가 필요하다.
pip로 설치되는 `cplex`는 Community Edition이라 변수·제약이 1000개를 넘으면 풀지 못하므로,
큰 인스턴스는 IBM ILOG CPLEX Optimization Studio를 설치해야 한다.

## 실행

저장소 루트에서 실행한다 (데이터 `./data`, 결과 `./results` 경로가 루트 기준).

```bash
python model/main.py         # config.py 설정으로 한 번 실행 (실제 데이터)
python model/test_main4.py   # 가상 데이터 실험 (test_main*.py)
```

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
- `model/experiment_utils.py`: 실험 결과 CSV/에러 로그 기록 (`ResultLogger`)
