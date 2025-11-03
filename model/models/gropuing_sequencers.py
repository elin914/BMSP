from typing import List
from model.data import Job


class BaseGroupingSequencer:
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]: raise NotImplementedError


class EDDGroupingSequencer(BaseGroupingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].due_date)


class SSTGroupingSequencer(BaseGroupingSequencer):
    """Slack Time이 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].due_date - job_list[i].release_date - job_list[i].p_time)


class SAGroupingSequencer(BaseGroupingSequencer):
    """Area가 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].width * job_list[i].height)


class LAGroupingSequencer(BaseGroupingSequencer):
    """Area가 큰 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].width * job_list[i].height, reverse=True)
