from typing import List
from model.data import Batch


class BaseSchedulingSequencer:
    def get_sequence_list(self, job_list: List[Batch], machines) -> List[int]: raise NotImplementedError
