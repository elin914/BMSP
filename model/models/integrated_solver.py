from typing import List, Tuple
from model.data import Job


class BaseSolver:
    def get_schedule(self, cfg, job_list: List[Job], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPSolver(BaseSolver):
    def get_schedule(self, cfg, job_list, machines):
        pass


class GASolver(BaseSolver):
    def get_schedule(self, cfg, job_list, machines):
        pass
