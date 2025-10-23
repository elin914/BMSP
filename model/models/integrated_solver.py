from typing import List
from model.data import Job


class BaseSolver:
    def get_schedule(self, job_list: List[Job], machines): raise NotImplementedError  # return type은 향후 명시


class CPSolver(BaseSolver):
    def get_schedule(self, job_list, machines):
        pass
