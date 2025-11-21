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
    exp_name = "S_S_job"

    current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"{exp_name}_{current_time_str}.csv"
    full_path = os.path.join(save_dir, file_name)
    headers = ['n_of_job', 'iteration', 'seed', 'P1_time', 'P1_bin', 'P1_fitness', 'GA_time', 'GA_fitness',
               'CP_10_time', 'CP_10_fitness', 'CP_30_time', 'CP_30_fitness',
               'CP_60_time', 'CP_60_fitness', 'CP_180_time', 'CP_180_fitness']
    with open(full_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"\n[*] 실험 시작! 결과는 '{full_path}'에 실시간으로 저장됩니다.\n")
    print(os.path.abspath(full_path))
    job_list_counts = [24, 36, 48, 60, 120, 180, 300]
    # job_list_counts = [48, 60]

    for n_of_job in job_list_counts:
        print(f"--- [Experiment Group] Total Jobs: {n_of_job} ---")
        for i in range(10):
            current_seed = 0
            try:
                cfg = Config()

                cfg.data_instance['total_n_jobs'] = n_of_job
                cfg.random_seed += i
                current_seed = cfg.random_seed

                set_random_seed(cfg.random_seed)
                data = Data()
                data.make_data(cfg)
                model_s, model_c = test_model_builder(cfg)

                print(f"   > [Iter {i + 1}/10] Seed: {current_seed} | Solving...", end='\r')

                result_row = [n_of_job, i + 1, current_seed]
                time_before = time.time()
                batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                time_after = time.time()
                result_row.append(round(time_after - time_before, 4))
                result_row.append(len(batch_list))
                result_row.append(fitness1)

                time_before = time.time()
                _, GA_fitness = model_s.solve_phase2(cfg, batch_list, data.machines)
                time_after = time.time()
                result_row.append(round(time_after - time_before, 4))
                result_row.append(GA_fitness)

                for search_limit in [10, 30, 60, 180]:
                    cfg.cp_search_time_limit = search_limit
                    time_before = time.time()
                    _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                    time_after = time.time()
                    result_row.append(round(time_after - time_before, 4))
                    result_row.append(CP_fitness)
                    if CP_fitness <= GA_fitness:
                        break
                result_row.extend([0] * (len(headers) - len(result_row)))

                with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(result_row)
                print(
                    f"   > [Total Jobs: {n_of_job}, Iter {i + 1}/10] Seed: {current_seed} | Saved.")

            except Exception as e:
                # 에러가 나도 실험이 멈추지 않고 로그를 남기고 다음으로 넘어가도록 처리
                print(f"\n   !!! [Error] Job: {n_of_job}, Iter: {i} Failed. Reason: {e}")
                with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    result_row = [n_of_job, i + 1, current_seed]
                    result_row.extend([0] * (len(headers) - len(result_row)))
                    writer.writerow(result_row)
        print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {full_path}")
