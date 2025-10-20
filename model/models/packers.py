from typing import List
from model.data import Batch


class BasePackingAlgorithm:
    def create_batch_list(self, job_sequence_list: List[int], machines) -> List[Batch]: raise NotImplementedError


class BFFPacker(BasePackingAlgorithm):
    def create_batch_list(self, job_sequence_list: List[int], machines) -> List[Batch]:
        batch_list = list()
        return batch_list
