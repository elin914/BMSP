import numpy as np
import os
import random


def set_random_seed(random_seed):
    os.environ['PYTHONHASHSEED'] = str(random_seed)
    random.seed(random_seed)
    np.random.seed(random_seed)
