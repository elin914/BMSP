from typing import List
from model.data import Batch


class BaseSchedulingAlgorithm:
    def get_schedule(self, batch_list: List[Batch]): raise NotImplementedError  # return type은 향후 명시


class IBHScheduler(BaseSchedulingAlgorithm):
    def get_schedule(self, batch_list: List[Batch]):
        return True
