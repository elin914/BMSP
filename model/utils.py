import numpy as np
import os
import random


def set_random_seed(random_seed):
    os.environ['PYTHONHASHSEED'] = str(random_seed)
    random.seed(random_seed)
    np.random.seed(random_seed)


def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def find_next_prime(n):
    if n <= 2:
        return n
    if n % 2 == 0:
        n += 1
    while True:
        if is_prime(n):
            return n
        n += 2
