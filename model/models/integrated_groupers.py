from typing import List
from model.data import Job, Batch


class BaseIntegratedGrouper:
    def create_batch_list(self, job_list: List[Job], machines) -> List[Batch]: raise NotImplementedError


class CPGrouper(BaseIntegratedGrouper):
    def create_batch_list(self, job_list: List[Job], machines) -> List[Batch]:
        batch_list = list()
        return batch_list
