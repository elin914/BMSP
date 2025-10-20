from typing import Dict
from model.data import Job


class BaseIntegratedSchedulingAlgorithm:
    def get_schedule(self, job_dict: Dict[int, Job], machines): raise NotImplementedError  # return type은 향후 명시


class CPIntegratedScheduler(BaseIntegratedSchedulingAlgorithm):
    def get_schedule(self, job_dict: Dict[int, Job], machines):
        return True
