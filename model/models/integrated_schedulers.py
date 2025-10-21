from typing import List
from model.data import Job


class BaseIntegratedSchedulingAlgorithm:
    def get_schedule(self, job_list: List[Job], machines): raise NotImplementedError  # return type은 향후 명시


class CPIntegratedScheduler(BaseIntegratedSchedulingAlgorithm):
    def get_schedule(self, job_list: List[Job], machines):
        return True
