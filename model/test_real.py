import time
from config import Config
from data import Data
from utils import *
from models import test_model_builder
from experiment_utils import ResultLogger


if __name__ == '__main__':
    # real_bin: 실제 항차 수, real_fitness: 실제 소요일-하역일 차이 합 (data.load_data에서 계산)
    logger = ResultLogger(
        save_dir='./results', exp_name='real_data',
        id_cols=['start_date', 'time_duration', 'n_of_job', 'seed', 'real_bin', 'real_fitness'],
        fields=['P1_time', 'P1_bin', 'P1_fitness', 'CP_300_time', 'CP_300_fitness'])

    # start_date_list = [41306, 41334, 41365]
    start_date_list = [41365]
    time_duration_list = [60, 90, 120]
    t_time = 41275

    for start_idx in start_date_list:
        for time_duration in time_duration_list:
            tag = f"[{start_idx} + {time_duration}]"
            print(f"   > {tag} | Start.")
            id_values = [start_idx, time_duration, '', '', '', '']
            result = list()
            try:
                cfg = Config()
                cfg.start_date = start_idx - t_time
                cfg.time_duration = time_duration
                id_values[3] = cfg.random_seed

                set_random_seed(cfg.random_seed)
                data = Data()
                data.load_data(cfg)
                model_s, model_c = test_model_builder(cfg)
                id_values[2], id_values[4], id_values[5] = len(data.job_list), cfg.fitness1, cfg.fitness2

                time_before = time.time()
                batch_list, fitness1 = model_s.solve_phase1(cfg, data.job_list, data.machines)
                time_after = time.time()
                result.append(round(time_after - time_before, 4))
                result.append(len(batch_list))
                result.append(fitness1)

                time_before = time.time()
                _, CP_fitness = model_c.solve_phase2(cfg, batch_list, data.machines)
                time_after = time.time()
                result.append(round(time_after - time_before, 4))
                result.append(CP_fitness)
                print(f"   > {tag} Total Jobs: {len(data.job_list)} Seed: {cfg.random_seed} | Saved.")

            except Exception:
                logger.log_error(tag)
            logger.write_row(id_values, {None: result})
        print("--------------------------------------------------\n")
    print(f"[*] 모든 실험 종료. 최종 파일: {logger.csv_path}")
