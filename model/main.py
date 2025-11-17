import time
from config import Config
from data import Data
from utils import *
from models import model_builder


if __name__ == '__main__':
    start_time = time.time()

    cfg = Config()
    set_random_seed(cfg.random_seed)
    data = Data()
    data.make_data(cfg)
    model = model_builder(cfg)
    schedule_list, total_tardiness = model.solve(cfg, data.job_list, data.machines)

    print(sum(len(schedule) for schedule in schedule_list), total_tardiness)
    print(time.time() - start_time)
