"""실험 정의 모음.

예전 test_main*.py 5개는 같은 반복문을 복사해서 조금씩 바꾼 형태였다.
여기서는 실험마다 '무엇이 다른지'만 적고, 실제 실행은 run_experiment.py 하나가 맡는다.

실험 정의 항목
- exp_name   : 결과 파일 이름 앞부분 (results/<exp_name>_<시각>.csv)
- data       : 'synthetic' (make_data) 또는 'real' (load_data)
- id_cols    : CSV 앞쪽 식별 열
- instances  : 인스턴스 목록을 만드는 함수. 각 항목은 dict
               (id_cols 값 + data_instance 덮어쓸 값 + problem_seed / algorithm_seed)
               algorithm_seed가 None이면 데이터 생성 후 seed를 다시 설정하지 않음 (예전 test_main/test_main2 방식)
- models     : {모델 이름: cfg에 덮어쓸 값}. CSV 열은 '<모델 이름>_<측정 항목>'
- steps      : 측정 단계 목록 ('P1' = 묶기, 'P2' = 순차 스케줄링, ('CP', 시간제한) = CP 스케줄링)
- cfg        : 모든 모델에 공통으로 덮어쓸 cfg 값

새 실험은 아래 EXPERIMENTS에 하나 추가하고 `python model/run_experiment.py <이름>` 으로 실행한다.
"""

SEED = 42

# 가상 데이터에는 달력(family_dict)이 없으므로 실제 데이터용 RBW/RCP 대신 BW/CP를 명시
SYNTHETIC_CFG = {'scheduler': 'BW', 'integrated_scheduler': 'CP'}


def same_seed_instances(job_counts, n_iterations):
    """데이터와 알고리즘이 같은 seed (예전 test_main.py, test_main2.py)"""
    for n_of_job in job_counts:
        for i in range(n_iterations):
            yield {'n_of_job': n_of_job, 'iteration': i + 1, 'seed': SEED + i,
                   'total_n_jobs': n_of_job, 'problem_seed': SEED + i, 'algorithm_seed': None}


def problem_iteration_instances(job_counts, family_counts, n_problems, n_iterations, only_problem=None):
    """문제(데이터) seed = SEED + problem, 알고리즘 seed = SEED + iteration (예전 test_main3.py, test_main4.py)
    only_problem: {(n_of_job, n_of_family): problem 번호} 가 있으면 그 문제만 실행"""
    for n_of_job in job_counts:
        for n_of_family in family_counts:
            for i in range(n_problems):
                if only_problem is not None and i != only_problem.get((n_of_job, n_of_family)):
                    continue
                for j in range(n_iterations):
                    yield {'n_of_job': n_of_job, 'n_of_family': n_of_family, 'problem': i, 'iteration': j,
                           'problem_seed': SEED + i, 'algorithm_seed': SEED + j,
                           'total_n_jobs': n_of_job, 'n_families': n_of_family}


def real_data_instances(start_dates, time_durations, t_time=41275):
    for start_idx in start_dates:
        for time_duration in time_durations:
            yield {'start_date': start_idx, 'time_duration': time_duration,
                   'cfg_start_date': start_idx - t_time, 'cfg_time_duration': time_duration,
                   'problem_seed': SEED, 'algorithm_seed': None}


EXPERIMENTS = {
    # 예전 test_main.py
    'A_4_6': {
        'data': 'synthetic',
        'id_cols': ['n_of_job', 'iteration', 'seed'],
        'instances': lambda: same_seed_instances([24, 60, 180, 300], 10),
        'models': {'S': {'scheduling_sequencer': 'OBRKGA'}},  # model_v13 이전 config 기본값 (GA로 2단계)
        'steps': ['P1', 'P2', ('CP', 10)],
        'cfg': SYNTHETIC_CFG,
    },
    # 예전 test_main2.py (모델 목록 예: ['RKGA', 'BRKGA', 'OBRKGA'])
    'S_S_job_OBRKGA_test': {
        'data': 'synthetic',
        'id_cols': ['n_of_job', 'iteration', 'seed'],
        'instances': lambda: same_seed_instances([24, 36, 48, 60, 120, 180, 300], 10),
        'models': {m: {'grouping_sequencer': m, 'scheduling_sequencer': m} for m in ['OBRKGA']},
        'steps': ['P1', 'P2', ('CP', 10)],
        'cfg': SYNTHETIC_CFG,
    },
    # 예전 test_main3.py
    'A_phase1': {
        'data': 'synthetic',
        'id_cols': ['n_of_job', 'n_of_family', 'problem', 'iteration', 'problem_seed', 'algorithm_seed'],
        'instances': lambda: problem_iteration_instances(
            [30, 60, 120], [3, 6], n_problems=5, n_iterations=30,
            only_problem={(30, 3): 2, (30, 6): 4, (60, 3): 2, (60, 6): 3, (120, 3): 0, (120, 6): 3}),
        'models': {
            'RKGA': {'grouping_sequencer': 'RKGA', 'scheduling_sequencer': 'RKGA'},
            'BRKGA': {'grouping_sequencer': 'BRKGA', 'scheduling_sequencer': 'BRKGA'},
            'OBRKGA': {'grouping_sequencer': 'OBRKGA', 'scheduling_sequencer': 'OBRKGA',
                       'GAgrouper_parameter': {'early_stop_count': 30}},
        },
        'steps': ['P1'],
        'cfg': SYNTHETIC_CFG,
    },
    # 예전 test_main4.py (모델 목록 예: SimA, Tabu)
    'A_phase2_EDD_SST_LA': {
        'data': 'synthetic',
        'id_cols': ['n_of_job', 'n_of_family', 'problem', 'iteration', 'problem_seed', 'algorithm_seed'],
        'instances': lambda: problem_iteration_instances([30, 60, 120], [3, 6], n_problems=5, n_iterations=10),
        'models': {m: {'grouping_sequencer': m, 'scheduling_sequencer': 'OBRKGA'} for m in ['EDD', 'SST', 'LA']},
        'steps': ['P1', ('CP', 10)],
        'cfg': SYNTHETIC_CFG,
    },
    # 예전 test_real.py (real_bin: 실제 항차 수, real_fitness: 실제 소요일-하역일 차이 합)
    'real_data': {
        'data': 'real',
        'id_cols': ['start_date', 'time_duration'],
        'extra_id_cols': ['n_of_job', 'seed', 'real_bin', 'real_fitness'],
        'instances': lambda: real_data_instances([41365], [60, 90, 120]),
        'models': {'S': {}},
        'steps': ['P1', ('CP', 300)],
        'cfg': {},
    },
}
