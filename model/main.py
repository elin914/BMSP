import time
from config import Config
from data import Data
from utils import *
from model import Model


if __name__ == '__main__':
    start_time = time.time()

    config = Config()
    set_random_seed(config.random_seed)
    data = Data()
    data.make_data(config)
    model = Model(config)

    print(time.time() - start_time)
