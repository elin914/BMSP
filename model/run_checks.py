"""모든 모델 조합을 가상 인스턴스로 돌리고 해의 타당성을 검사한다.

사용법 (저장소 루트에서)
    python model/run_checks.py            # 빠른 검사: job 12개, 모든 조합 (1분 내외)
    python model/run_checks.py --full     # job 30/60/120개 x seed 3개, 휴리스틱/CP 위주
    python model/run_checks.py --slow     # SimA/Tabu 포함 (오래 걸림)

알고리즘을 고친 뒤 이걸 돌려서 FAIL이 없으면 최소한 '해가 깨지지는 않았다'는 것을 확인할 수 있다.
실제 데이터용 RBW/RCP는 달력 데이터가 필요해서 여기서는 검사하지 않는다.
"""
import argparse
import contextlib
import io
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data import Data
from utils import set_random_seed
from models import model_builder
from validate import validate_solution


BASE = dict(model_type='Sequential_Sequential', grouping_sequencer='EDD', grouper='ABFF',
            scheduling_sequencer='LDD', scheduler='BW', integrated_scheduler='CP')


def cases(mode):
    """(이름, cfg 덮어쓸 값) 목록"""
    out = list()
    if mode in ('quick', 'full'):
        for g in ['EDD', 'SST', 'SA', 'LA']:
            out.append((f'grouping={g}', dict(BASE, grouping_sequencer=g)))
        out.append(('grouper=BFF', dict(BASE, grouper='BFF')))
        for s in ['EDD', 'LDD', 'MB']:
            out.append((f'scheduling_seq={s}', dict(BASE, scheduling_sequencer=s)))
        for sc in ['GL', 'IBH', 'BW']:
            out.append((f'scheduler={sc}', dict(BASE, scheduler=sc)))
        out.append(('Sequential_Integrated(CP)', dict(BASE, model_type='Sequential_Integrated')))
    if mode == 'quick':
        for g in ['RKGA', 'BRKGA', 'OBRKGA']:
            out.append((f'grouping={g}', dict(BASE, grouping_sequencer=g)))
        for s in ['RKGA', 'BRKGA', 'OBRKGA']:
            out.append((f'scheduling_seq={s}', dict(BASE, scheduling_sequencer=s)))
        out.append(('Integrated(CPSolver)', dict(BASE, model_type='Integrated')))
        out.append(('Integrated_Sequential', dict(BASE, model_type='Integrated_Sequential')))
        out.append(('Integrated_Integrated', dict(BASE, model_type='Integrated_Integrated')))
    if mode == 'slow':
        for g in ['SimA', 'Tabu']:
            out.append((f'grouping={g}', dict(BASE, grouping_sequencer=g)))
            out.append((f'scheduling_seq={g}', dict(BASE, scheduling_sequencer=g)))
    return out


def run_case(overrides, n_jobs, n_families, seed, cp_time_limit):
    cfg = Config()
    cfg.data_instance.update(total_n_jobs=n_jobs, n_families=n_families)
    for param in (cfg.GAgrouper_parameter, cfg.GAsequencer_parameter):
        param.update(population_size=30, generations=5, early_stop_count=3)
    cfg.cp_search_time_limit = cp_time_limit
    for key, value in overrides.items():
        setattr(cfg, key, value)

    set_random_seed(seed)
    data = Data()
    data.make_data(cfg)
    with contextlib.redirect_stdout(io.StringIO()):
        model = model_builder(cfg)
        schedule_list, fitness = model.solve(cfg, data.job_list, data.machines)

    # GL/IBH는 tardiness 목적이고 시작 시간 중복 금지(RC)를 다루지 않는 예전 스케줄러
    is_tardiness = overrides['model_type'] == 'Sequential_Sequential' and overrides['scheduler'] in ('GL', 'IBH')
    errors = validate_solution(model.batch_list, schedule_list, data.job_list, data.machines,
                               reported_fitness=fitness,
                               objective='tardiness' if is_tardiness else 'jit',
                               distinct_start=not is_tardiness)
    return fitness, len(model.batch_list), errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--slow', action='store_true')
    args = parser.parse_args()
    mode = 'full' if args.full else 'slow' if args.slow else 'quick'
    instances = [(n, f, s) for n in (30, 60, 120) for f in (3, 6) for s in (42, 43, 44)] if mode == 'full' \
        else [(12, 3, 42)]
    cp_time_limit = 3 if mode == 'full' else 5

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 저장소 루트 기준 경로
    n_fail = 0
    for name, overrides in cases(mode):
        for n_jobs, n_families, seed in instances:
            label = f'{name:28s} n={n_jobs:<3d} fam={n_families} seed={seed}'
            start = time.time()
            try:
                fitness, n_batches, errors = run_case(overrides, n_jobs, n_families, seed, cp_time_limit)
            except Exception:
                n_fail += 1
                print(f'ERROR {label}\n{traceback.format_exc()}')
                continue
            elapsed = time.time() - start
            if errors:
                n_fail += 1
                print(f'FAIL  {label} fit={fitness} bins={n_batches} {elapsed:5.1f}s')
                for e in errors[:5]:
                    print(f'        - {e}')
            else:
                print(f'OK    {label} fit={fitness} bins={n_batches} {elapsed:5.1f}s')
    print(f'\n실패 {n_fail}건' if n_fail else '\n모두 통과')
    sys.exit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
