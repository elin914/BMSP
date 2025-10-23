from typing import List
from model.data import Batch


class BaseSchedulingSequencer:
    def get_sequence_list(self, batch_list: List[Batch], machines) -> List[int]: raise NotImplementedError


class EDDSequencer(BaseSchedulingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, batch_list: List[Batch], machines) -> List[int]:
        job_sequence_list = sorted(range(len(batch_list)), key=lambda i: batch_list[i].due_date_list)
        return job_sequence_list
