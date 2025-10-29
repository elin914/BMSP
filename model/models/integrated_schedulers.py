from typing import List, Tuple
from model.data import Batch


class BaseIntegratedScheduler:
    def get_schedule(self, batch_list: List[Batch], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, batch_list: List[Batch], machines):
        return True
