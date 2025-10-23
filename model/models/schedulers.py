from typing import List
from model.data import Batch


class BaseScheduler:
    def get_schedule(self, batch_list: List[Batch], machines): raise NotImplementedError  # return type은 향후 명시


class IBHScheduler(BaseScheduler):
    def get_schedule(self, batch_list: List[Batch], machines):
        return True
