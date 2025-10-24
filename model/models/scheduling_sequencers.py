from typing import List
from model.data import Batch
import numpy as np


class BaseSchedulingSequencer:
    def get_sequence_list(self, scheduler, batch_list: List[Batch], machines) -> List[int]: raise NotImplementedError


class EDDSchedulingSequencer(BaseSchedulingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: np.average(batch_list[i].due_date_list))


class MBSchedulingSequencer(BaseSchedulingSequencer):
    def get_sequence_list(self, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: len(batch_list[i].placed_job_list))

