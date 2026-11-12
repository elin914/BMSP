"""config.py 설정으로 한 번 실행.

    python model/main.py               # 실제 데이터 (data/*.xlsx, config 기본값: RBW/RCP)
    python model/main.py --synthetic   # 가상 데이터 (config.data_instance, BW/CP)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data import Data
from utils import set_random_seed
from models import model_builder
from validate import validate_solution


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic', action='store_true', help='가상 데이터로 실행 (BW/CP 사용)')
    args = parser.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 저장소 루트 기준 경로

    start_time = time.time()
    cfg = Config()
    set_random_seed(cfg.random_seed)
    data = Data()
    if args.synthetic:
        cfg.scheduler = 'BW'
        cfg.integrated_scheduler = 'CP'
        data.make_data(cfg)
    else:
        data.load_data(cfg)
    model = model_builder(cfg)
    schedule_list, fitness = model.solve(cfg, data.job_list, data.machines)

    print(f'배치 {len(model.batch_list)}개, fitness {fitness}, {time.time() - start_time:.1f}s')
    if args.synthetic:
        errors = validate_solution(model.batch_list, schedule_list, data.job_list, data.machines, fitness)
        print('검증 통과' if not errors else '검증 실패:\n  ' + '\n  '.join(errors[:10]))
