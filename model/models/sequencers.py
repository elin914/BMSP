from typing import Dict, List
from model.data import Job


class BaseSequencingAlgorithm:
    def get_sequence_list(self, job_dict: Dict[int, Job], machines) -> List[int]: raise NotImplementedError


class SPTSequencer(BaseSequencingAlgorithm):
    def get_sequence_list(self, job_dict: Dict[int, Job], machines) -> List[int]:
        job_sequence_list = list()
        return job_sequence_list
