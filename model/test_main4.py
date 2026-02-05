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
    exp_name = "A_phase2_SA_Tabu"

    current_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"{exp_name}_{current_time_str}.csv"
    full_path = os.path.join(save_dir, file_name)
    headers = ['n_of_job', 'n_of_family', 'problem', 'iteration', 'seed1', 'seed2',
               # 'SA_P1_time', 'SA_P1_bin', 'SA_P1_fitness',
               # 'SA_CP_time', 'SA_CP_fitness',
               # 'Tabu_P1_time', 'TabuA_P1_bin', 'Tabu_P1_fitness',
               # 'Tabu_CP_time', 'Tabu_CP_fitness',
               'EDD_P1_time', 'EDD_P1_bin', 'EDD_P1_fitness',
               'EDD_CP_time', 'EDD_CP_fitness',
               'SST_P1_time', 'SST_P1_bin', 'SST_P1_fitness',
               'SST_CP_time', 'SST_CP_fitness',
               'LA_P1_time', 'LA_P1_bin', 'LA_P1_fitness',
               'LA_CP_time', 'LA_CP_fitness',
               ]

    with open(full_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"\n[*] 실험 시작! 결과는 '{full_path}'에 실시간으로 저장됩니다.\n")
    print(os.path.abspath(full_path))
    # job_list_counts = [24, 36, 48, 60, 120, 180, 300]
    job_list_counts = [30, 60, 120]
    family_counts = [3, 6]
    test_2_dict = {
        (30, 3): 2,
        (30, 6): 4,
        (60, 3): 2,
        (60, 6): 3,
        (120, 3): 0,
        (120, 6): 3
    }

    for n_of_job in job_list_counts:
        for n_of_family in family_counts:
            print(f"--- [Experiment Group] Total Jobs: {n_of_job}, family: {n_of_family} ---")
            for i in range(5):
                problem_seed = 0
                for j in range(10):
                    algorithm_seed = 0
                    result_row = [n_of_job, n_of_family, i, j, 0, 0]
                    model_results = dict()
                    # for model_name in ['SimA', 'Tabu']:
                    for model_name in ['EDD', 'SST', 'LA']:
                        temp_model_result = list()
                        try:
                            cfg = Config()
                            cfg.grouping_sequencer = model_name
                            cfg.scheduling_sequencer = 'OBRKGA'
                            cfg.data_instance['total_n_jobs'] = n_of_job
                            cfg.data_instance['n_families'] = n_of_family

                            algorithm_seed = cfg.random_seed + i
                            set_random_seed(algorithm_seed)
                            if result_row[4] == 0:
                                result_row[4] = algorithm_seed

                            data = Data()
                            data.make_data(cfg)

                            problem_seed = cfg.random_seed + j
                            set_random_seed(problem_seed)

                            if result_row[5] == 0:
                                result_row[5] = problem_seed
                            model_s, model_c = test_model_builder(cfg)

                            print(f"   > [Total Jobs: {n_of_job}, family: {n_of_family},"
                                  f" Problem {i + 1}/5, Iter {j + 1}/10] | Solving...", end='\r')

                            time_before = time.time()
                            batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                            time_after = time.time()
                            temp_model_result.append(round(time_after - time_before, 4))
                            temp_model_result.append(len(batch_list))
                            temp_model_result.append(fitness1)

                            # time_before = time.time()
                            # _, GA_fitness = model_s.solve_phase2(cfg, batch_list, data.machines)
                            # time_after = time.time()
                            # temp_model_result.append(round(time_after - time_before, 4))
                            # temp_model_result.append(GA_fitness)

                            cfg.cp_search_time_limit = 10
                            time_before = time.time()
                            _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                            time_after = time.time()
                            temp_model_result.append(round(time_after - time_before, 4))
                            temp_model_result.append(CP_fitness)

                            model_results[model_name] = temp_model_result
                            print(f"   > [Total Jobs: {n_of_job}, family: {n_of_family},"
                                  f" Problem {i + 1}/5, Iter {j + 1}/10] | {model_name} Solved.")

                        except Exception as e:
                            print(
                                f"\n   !!! [Error] Job: {n_of_job}, Iter: {i + 1}, Model: {model_name} Failed. Reason: {e}")
                            model_results[model_name] = [0] * 7


                    # result_row.extend(model_results.get('SimA', [0] * 5))
                    # result_row.extend(model_results.get('Tabu', [0] * 5))
                    result_row.extend(model_results.get('EDD', [0] * 5))
                    result_row.extend(model_results.get('SST', [0] * 5))
                    result_row.extend(model_results.get('LA', [0] * 5))
                    # result_row.extend(model_results.get('RKGA', [0] * 7))
                    # result_row.extend(model_results.get('BRKGA', [0] * 7))
                    # result_row.extend(model_results.get('OBRKGA', [0] * 7))
                    # result_row.extend(model_results.get('RKGA', [0] * 3))
                    # result_row.extend(model_results.get('BRKGA', [0] * 3))
                    # result_row.extend(model_results.get('OBRKGA', [0] * 3))

                    with open(full_path, 'a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(result_row)

                    print(f"   > [Total Jobs: {n_of_job}, family: {n_of_family},"
                          f" Problem {i + 1}/5, Iter {j + 1}/10] | Final Row Saved.")
                    print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {full_path}")
