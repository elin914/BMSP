from typing import List
from model.data import Batch


class BaseScheduler:
    def get_schedule(self, batch_list: List[Batch], batch_sequence_list, machines): raise NotImplementedError  # return type은 향후 명시


class GLScheduler(BaseScheduler):
    def get_schedule(self, batch_list: List[Batch], batch_sequence_list, machines):
        return True


class IBHScheduler(BaseScheduler):
    def get_schedule(self, batch_list: List[Batch], batch_sequence_list, machines):
        return True
