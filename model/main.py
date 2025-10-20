import time
from config import Config
from data import Data
from utils import *
from models import model_builder


if __name__ == '__main__':
    start_time = time.time()

    config = Config()
    set_random_seed(config.random_seed)
    data = Data()
    data.make_data(config)
    model = model_builder(config)
    solution = model.solve(data.job_dict, data.machines)

    print(time.time() - start_time)
