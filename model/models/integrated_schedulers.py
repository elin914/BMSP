from typing import List
from model.data import Batch


class BaseIntegratedScheduler:
    def get_schedule(self, job_list: List[Batch], machines): raise NotImplementedError  # return type은 향후 명시


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, job_list: List[Batch], machines):
        return True
