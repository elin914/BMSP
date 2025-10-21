from typing import List
from model.data import Job


class BaseSequencingAlgorithm:
    def get_sequence_list(self, job_list: List[Job], machines) -> List[int]: raise NotImplementedError


class SPTSequencer(BaseSequencingAlgorithm):
    """Processing Time이 짧은 순서대로 정렬"""
    def get_sequence_list(self, job_list: List[Job], machines) -> List[int]:
        job_sequence_list = sorted(range(len(job_list)), key=lambda i: job_list[i].p_time)
        return job_sequence_list


class LPTSequencer(BaseSequencingAlgorithm):
    """Processing Time이 긴 순서대로 정렬"""
    def get_sequence_list(self, job_list: List[Job], machines) -> List[int]:
        job_sequence_list = sorted(range(len(job_list)), key=lambda i: job_list[i].p_time, reverse=True)
        return job_sequence_list


class EDDSequencer(BaseSequencingAlgorithm):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, job_list: List[Job], machines) -> List[int]:
        job_sequence_list = sorted(range(len(job_list)), key=lambda i: job_list[i].due_date)
        return job_sequence_list


class MSSequencer(BaseSequencingAlgorithm):
    """Slack Time이 작은 순서대로 정렬"""
    def get_sequence_list(self, job_list: List[Job], machines) -> List[int]:
        job_sequence_list = sorted(range(len(job_list)),
                                   key=lambda i: job_list[i].due_date - job_list[i].release_date - job_list[i].p_time)
        return job_sequence_list
