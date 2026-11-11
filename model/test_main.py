import time
from config import Config
from data import Data
from utils import *
from models import test_model_builder
from experiment_utils import ResultLogger


if __name__ == '__main__':
    # CP를 시간 제한별로 돌리다가 GA 이하 결과가 나오면 멈춤 (나머지 시간 제한 칸은 빈 칸)
    # cp_time_limits = [10, 30, 60, 180]
    cp_time_limits = [10]
    logger = ResultLogger(
        save_dir='./results', exp_name='A_4_6',
        id_cols=['n_of_job', 'iteration', 'seed'],
        fields=['P1_time', 'P1_bin', 'P1_fitness', 'GA_time', 'GA_fitness']
               + [f'CP_{limit}_{name}' for limit in cp_time_limits for name in ('time', 'fitness')])

    # job_list_counts = [24, 36, 48, 60, 120, 180, 300]
    n_of_job_list = [24, 60, 180, 300]
    n_iterations = 10

    for n_of_job in n_of_job_list:
        print(f"--- [Experiment Group] Total Jobs: {n_of_job} ---")
        for i in range(n_iterations):
            current_seed = Config().random_seed + i
            tag = f"[Total Jobs: {n_of_job}, Iter {i + 1}/{n_iterations}] Seed: {current_seed}"
            result = list()
            try:
                cfg = Config()
                # 가상 데이터에는 달력(family_dict)이 없으므로 실제 데이터용 RBW/RCP 대신 BW/CP를 명시
                # (config.py 기본값이 실제 데이터용으로 바뀌어도 가상 실험이 깨지지 않게)
                cfg.scheduler = 'BW'
                cfg.integrated_scheduler = 'CP'
                cfg.scheduling_sequencer = 'OBRKGA'  # model_v13 이전 config 기본값 (GA_fitness 열)
                cfg.data_instance['total_n_jobs'] = n_of_job
                cfg.random_seed = current_seed

                set_random_seed(cfg.random_seed)
                data = Data()
                data.make_data(cfg)
                model_s, model_c = test_model_builder(cfg)

                print(f"   > {tag} | Solving...", end='\r')

                time_before = time.time()
                batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                time_after = time.time()
                result.append(round(time_after - time_before, 4))
                result.append(len(batch_list))
                result.append(fitness1)

                time_before = time.time()
                _, GA_fitness = model_s.solve_phase2(cfg, batch_list, data.machines)
                time_after = time.time()
                result.append(round(time_after - time_before, 4))
                result.append(GA_fitness)

                for k, search_limit in enumerate(cp_time_limits):
                    cfg.cp_search_time_limit = search_limit
                    time_before = time.time()
                    _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                    time_after = time.time()
                    result.append(round(time_after - time_before, 4))
                    result.append(CP_fitness)
                    if CP_fitness <= GA_fitness:
                        # 의도적으로 멈춘 것이므로 남은 칸은 빈 칸으로 채워 '실패'로 표시되지 않게 함
                        result.extend([''] * (2 * (len(cp_time_limits) - k - 1)))
                        break
                print(f"   > {tag} | Saved.")

            except Exception:
                logger.log_error(tag)
            logger.write_row([n_of_job, i + 1, current_seed], {None: result})
        print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {logger.csv_path}")
