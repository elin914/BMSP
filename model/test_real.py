import time
from config import Config
from data import Data
from utils import *
from models import test_model_builder
import csv
import os
from datetime import datetime


if __name__ == '__main__':
    save_dir = './results'
    os.makedirs(save_dir, exist_ok=True)
    exp_name = "real_data"

    current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"{exp_name}_{current_time_str}.csv"
    full_path = os.path.join(save_dir, file_name)
    headers = ['n_of_job', 'seed',
               'real_fitness', 'real_fitness',
               'P1_time', 'P1_bin', 'P1_fitness',
               'CP_300_time', 'CP_300_fitness']
    with open(full_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"\n[*] 실험 시작! 결과는 '{full_path}'에 실시간으로 저장됩니다.\n")
    print(os.path.abspath(full_path))
    # start_date_list = [41306, 41334, 41365]
    start_date_list = [41365]
    time_duration_list = [60, 90, 120]
    t_time = 41275

    for start_idx in start_date_list:
        for time_duration in time_duration_list:
            print(
                f"   > [{start_idx} + {time_duration}] | Start.")
            try:
                cfg = Config()
                cfg.start_date = start_idx - t_time
                cfg.time_duration = time_duration
                current_seed = cfg.random_seed

                set_random_seed(cfg.random_seed)
                data = Data()
                data.load_data(cfg)
                model_s, model_c = test_model_builder(cfg)

                result_row = [len(data.job_list), current_seed, cfg.fitness1, cfg.fitness2]
                time_before = time.time()
                batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                time_after = time.time()
                result_row.append(round(time_after - time_before, 4))
                result_row.append(len(batch_list))
                result_row.append(fitness1)

                time_before = time.time()
                _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                time_after = time.time()
                result_row.append(round(time_after - time_before, 4))
                result_row.append(CP_fitness)

                result_row.extend([0] * (len(headers) - len(result_row)))

                with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(result_row)
                print(
                    f"   > [{start_idx} + {time_duration}, Total Jobs: {len(data.job_list)} Seed: {current_seed} | Saved.")

            except Exception as e:
                # 에러가 나도 실험이 멈추지 않고 로그를 남기고 다음으로 넘어가도록 처리
                with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    result_row = []
                    result_row.extend([0] * (len(headers) - len(result_row)))
                    writer.writerow(result_row)
        print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {full_path}")
