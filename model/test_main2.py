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
    exp_name = "S_S_job_OBRKGA_test"

    current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"{exp_name}_{current_time_str}.csv"
    full_path = os.path.join(save_dir, file_name)
    headers = ['n_of_job', 'iteration', 'seed',
               # 'RKGA_P1_time', 'RKGA_P1_bin', 'RKGA_P1_fitness',
               'RKGA_P2_time', 'RKGA_P2_fitness', 'RKGA_CP_time', 'RKGA_CP_fitness',
               'BRKGA_P1_time', 'BRKGA_P1_bin', 'BRKGA_P1_fitness',
               'BRKGA_P2_time', 'BRKGA_P2_fitness', 'BRKGA_CP_time', 'BRKGA_CP_fitness',
               'OBRKGA_P1_time', 'OBRKGA_P1_bin', 'OBRKGA_P1_fitness',
               'OBRKGA_P2_time', 'OBRKGA_P2_fitness', 'OBRKGA_CP_time', 'OBRKGA_CP_fitness'
               ]

    with open(full_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"\n[*] 실험 시작! 결과는 '{full_path}'에 실시간으로 저장됩니다.\n")
    print(os.path.abspath(full_path))
    job_list_counts = [24, 36, 48, 60, 120, 180, 300]
    # job_list_counts = [24, 60, 180, 300]

    parameter_list = [(60, 2), (60, 7), (120, 1), (180, 1), (300, 1)]

    for n_of_job in job_list_counts:
    # for (n_of_job, problem_idx) in parameter_list:
        print(f"--- [Experiment Group] Total Jobs: {n_of_job} ---")
        for i in range(10):
            current_seed = 0
            result_row = [n_of_job, i + 1, 0]
            model_results = dict()
            # for model_name in ['RKGA', 'BRKGA', 'OBRKGA']:
            for model_name in ['OBRKGA']:
                temp_model_result = list()
                try:
                    cfg = Config()
                    cfg.grouping_sequencer = model_name
                    cfg.scheduling_sequencer = model_name
                    cfg.data_instance['total_n_jobs'] = n_of_job
                    cfg.random_seed += i
                    current_seed = cfg.random_seed
                    set_random_seed(cfg.random_seed)

                    data = Data()
                    data.make_data(cfg)

                    if result_row[2] == 0:
                        result_row[2] = current_seed
                    model_s, model_c = test_model_builder(cfg)

                    print(f"   > [Iter {i + 1}/10] Seed: {current_seed} | Solving...", end='\r')

                    time_before = time.time()
                    batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                    time_after = time.time()
                    temp_model_result.append(round(time_after - time_before, 4))
                    temp_model_result.append(len(batch_list))
                    temp_model_result.append(fitness1)

                    time_before = time.time()
                    _, GA_fitness = model_s.solve_phase2(cfg, batch_list, data.machines)
                    time_after = time.time()
                    temp_model_result.append(round(time_after - time_before, 4))
                    temp_model_result.append(GA_fitness)

                    cfg.cp_search_time_limit = 10
                    time_before = time.time()
                    _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                    time_after = time.time()
                    temp_model_result.append(round(time_after - time_before, 4))
                    temp_model_result.append(CP_fitness)

                    model_results[model_name] = temp_model_result
                    print(f"   > [Total Jobs: {n_of_job}, Iter {i + 1}/10] Seed: {current_seed} | {model_name} Solved.")

                except Exception as e:
                    print(f"\n   !!! [Error] Job: {n_of_job}, Iter: {i + 1}, Model: {model_name} Failed. Reason: {e}")
                    model_results[model_name] = [0] * 7

            result_row.extend(model_results.get('RKGA', [0] * 7))
            result_row.extend(model_results.get('BRKGA', [0] * 7))
            result_row.extend(model_results.get('OBRKGA', [0] * 7))
            # result_row.extend(model_results.get('RKGA', [0] * 3))
            # result_row.extend(model_results.get('BRKGA', [0] * 3))
            # result_row.extend(model_results.get('OBRKGA', [0] * 3))

            with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(result_row)

            print(f"   > [Total Jobs: {n_of_job}, Iter {i + 1}/10] Final Row Saved.")
            print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {full_path}")
