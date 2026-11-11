import time
from config import Config
from data import Data
from utils import *
from models import test_model_builder
from experiment_utils import ResultLogger


if __name__ == '__main__':
    # 모델 목록만 바꾸면 CSV 헤더도 자동으로 바뀜 (예: ['SimA', 'Tabu'])
    model_names = ['EDD', 'SST', 'LA']
    logger = ResultLogger(
        save_dir='./results', exp_name='A_phase2_EDD_SST_LA',
        id_cols=['n_of_job', 'n_of_family', 'problem', 'iteration', 'problem_seed', 'algorithm_seed'],
        model_names=model_names,
        fields=['P1_time', 'P1_bin', 'P1_fitness', 'CP_time', 'CP_fitness'])

    # job_list_counts = [24, 36, 48, 60, 120, 180, 300]
    job_list_counts = [30, 60, 120]
    family_counts = [3, 6]
    n_problems = 5
    n_iterations = 10

    for n_of_job in job_list_counts:
        for n_of_family in family_counts:
            print(f"--- [Experiment Group] Total Jobs: {n_of_job}, family: {n_of_family} ---")
            for i in range(n_problems):
                for j in range(n_iterations):
                    # 문제(데이터) seed는 i, 알고리즘 seed는 j로 결정
                    problem_seed = Config().random_seed + i
                    algorithm_seed = Config().random_seed + j
                    tag = (f"[Total Jobs: {n_of_job}, family: {n_of_family},"
                           f" Problem {i + 1}/{n_problems}, Iter {j + 1}/{n_iterations}]")
                    model_results = dict()
                    for model_name in model_names:
                        temp_model_result = list()
                        try:
                            cfg = Config()
                            # 가상 데이터에는 달력(family_dict)이 없으므로 실제 데이터용 RBW/RCP 대신 BW/CP를 명시
                            # (config.py 기본값이 실제 데이터용으로 바뀌어도 가상 실험이 깨지지 않게)
                            cfg.scheduler = 'BW'
                            cfg.integrated_scheduler = 'CP'
                            cfg.grouping_sequencer = model_name
                            cfg.scheduling_sequencer = 'OBRKGA'
                            cfg.data_instance['total_n_jobs'] = n_of_job
                            cfg.data_instance['n_families'] = n_of_family

                            set_random_seed(problem_seed)
                            data = Data()
                            data.make_data(cfg)

                            set_random_seed(algorithm_seed)
                            model_s, model_c = test_model_builder(cfg)

                            print(f"   > {tag} | Solving...", end='\r')

                            time_before = time.time()
                            batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                            time_after = time.time()
                            temp_model_result.append(round(time_after - time_before, 4))
                            temp_model_result.append(len(batch_list))
                            temp_model_result.append(fitness1)

                            cfg.cp_search_time_limit = 10
                            time_before = time.time()
                            _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                            time_after = time.time()
                            temp_model_result.append(round(time_after - time_before, 4))
                            temp_model_result.append(CP_fitness)

                            print(f"   > {tag} | {model_name} Solved.")

                        except Exception:
                            logger.log_error(f"{tag} Model: {model_name}")
                        model_results[model_name] = temp_model_result

                    logger.write_row([n_of_job, n_of_family, i, j, problem_seed, algorithm_seed], model_results)
                    print(f"   > {tag} | Final Row Saved.")
                    print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {logger.csv_path}")
