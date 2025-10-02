import time
from config import Config
from data import Data


if __name__ == '__main__':
    start_time = time.time()

    config = Config()
    data = Data()
    data.get_data(config)
    # cpmodel = CPModel(config)
    # cpmodel.data_preprocessing()
    # cpmodel.get_heuristic_solution()
    # cpmodel.run_model()

    print(time.time() - start_time)
