from typing import Dict, List
from model.data import Job, Batch


class BaseGroupingAlgorithm:
    def create_batch_list(self, job_dict: Dict[int, Job], machines) -> List[Batch]: raise NotImplementedError


class CPGrouper(BaseGroupingAlgorithm):
    def create_batch_list(self, job_dict: Dict[int, Job], machines) -> List[Batch]:
        batch_list = list()
        return batch_list
