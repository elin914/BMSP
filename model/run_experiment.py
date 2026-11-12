"""실험 실행기.

사용법 (저장소 루트에서)
    python model/run_experiment.py --list               # 실험 목록과 실행 횟수
    python model/run_experiment.py A_phase1             # 실험 실행 -> results/A_phase1_<시각>.csv (+ .log)
    python model/run_experiment.py A_phase1 --limit 2   # 앞의 인스턴스 2개만 (코드 확인용)

실험 내용은 experiments.py 에서 정의한다.
"""
import argparse
import copy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data import Data
from utils import set_random_seed
from models import test_model_builder
from experiment_utils import ResultLogger
from experiments import EXPERIMENTS


def step_fields(step):
    if step == 'P1':
        return ['P1_time', 'P1_bin', 'P1_fitness']
    if step == 'P2':
        return ['P2_time', 'P2_fitness']
    if isinstance(step, tuple) and step[0] == 'CP':
        return ['CP_time', 'CP_fitness']
    raise ValueError(f'알 수 없는 step: {step}')


def apply_overrides(cfg, overrides):
    """cfg 속성 덮어쓰기. dict 속성(GA 파라미터 등)은 일부 키만 바꿀 수 있게 update"""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(getattr(cfg, key, None), dict):
            getattr(cfg, key).update(copy.deepcopy(value))
        else:
            setattr(cfg, key, copy.deepcopy(value))


def build_cfg(exp, instance, model_overrides):
    cfg = Config()
    apply_overrides(cfg, exp.get('cfg', {}))
    apply_overrides(cfg, model_overrides)
    for key in ('total_n_jobs', 'n_families'):
        if key in instance:
            cfg.data_instance[key] = instance[key]
    if 'cfg_start_date' in instance:
        cfg.start_date = instance['cfg_start_date']
        cfg.time_duration = instance['cfg_time_duration']
    cfg.random_seed = instance['problem_seed']
    return cfg


def run_model(exp, instance, model_overrides, id_extra, cp_limit=None):
    """한 인스턴스 x 한 모델. 측정값 리스트를 반환 (중간에 실패하면 예외가 그대로 올라감)"""
    values = list()
    cfg = build_cfg(exp, instance, model_overrides)
    set_random_seed(instance['problem_seed'])
    data = Data()
    if exp['data'] == 'synthetic':
        data.make_data(cfg)
    else:
        data.load_data(cfg)
        id_extra.update(n_of_job=len(data.job_list), seed=cfg.random_seed,
                        real_bin=cfg.fitness1, real_fitness=cfg.fitness2)
    if instance['algorithm_seed'] is not None:
        set_random_seed(instance['algorithm_seed'])
    model_s, model_c = test_model_builder(cfg)

    batch_list = None
    for step in exp['steps']:
        start = time.time()
        if step == 'P1':
            batch_list, fitness = model_s.solve_phase1(cfg, data.job_list, data.machines)
            values += [round(time.time() - start, 4), len(batch_list), fitness]
        elif step == 'P2':
            _, fitness = model_s.solve_phase2(cfg, batch_list, data.machines)
            values += [round(time.time() - start, 4), fitness]
        else:
            cfg.cp_search_time_limit = step[1] if cp_limit is None else cp_limit
            _, fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
            values += [round(time.time() - start, 4), fitness]
    return values


def run(name, limit=None, save_dir='./results', cp_limit=None):
    exp = EXPERIMENTS[name]
    fields = [f for step in exp['steps'] for f in step_fields(step)]
    model_names = list(exp['models'])
    extra_cols = exp.get('extra_id_cols', [])
    logger = ResultLogger(save_dir=save_dir, exp_name=name, id_cols=exp['id_cols'] + extra_cols,
                          fields=fields, model_names=model_names if model_names != ['S'] else None)

    instances = list(exp['instances']())[:limit]
    for k, instance in enumerate(instances):
        tag = f"[{k + 1}/{len(instances)}] " + ', '.join(f'{c}={instance[c]}' for c in exp['id_cols'])
        results = dict()
        id_extra = {c: '' for c in extra_cols}
        for model_name, model_overrides in exp['models'].items():
            key = None if model_names == ['S'] else model_name
            print(f'   > {tag} | {model_name} Solving...', end='\r')
            try:
                results[key] = run_model(exp, instance, model_overrides, id_extra, cp_limit)
                print(f'   > {tag} | {model_name} Solved.   ')
            except Exception:
                logger.log_error(f'{tag} Model: {model_name}')
                results.setdefault(key, [])
        logger.write_row([instance[c] for c in exp['id_cols']] + [id_extra[c] for c in extra_cols], results)
    print(f'[*] 모든 실험 종료. 최종 파일: {logger.csv_path}')
    return logger.csv_path


def main():
    parser = argparse.ArgumentParser(description='실험 실행 (실험 정의는 experiments.py)')
    parser.add_argument('name', nargs='?', help='실험 이름')
    parser.add_argument('--list', action='store_true', help='실험 목록 보기')
    parser.add_argument('--limit', type=int, default=None, help='앞의 인스턴스 N개만 실행')
    parser.add_argument('--out', default='./results', help='결과 저장 폴더 (기본: ./results)')
    parser.add_argument('--cp-limit', type=int, default=None, help='CP 시간 제한(초)을 이 값으로 덮어씀 (빠른 확인용)')
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 저장소 루트 기준 경로
    if args.list or not args.name:
        for name, exp in EXPERIMENTS.items():
            n = len(list(exp['instances']()))
            print(f"{name:24s} {exp['data']:9s} 인스턴스 {n:4d}개 x 모델 {len(exp['models'])}개  "
                  f"steps={exp['steps']}  models={list(exp['models'])}")
        return
    if args.name not in EXPERIMENTS:
        sys.exit(f"없는 실험입니다: {args.name} (목록: python model/run_experiment.py --list)")
    run(args.name, args.limit, args.out, args.cp_limit)


if __name__ == '__main__':
    main()
