from typing import List
from model.data import Batch
from .grouping_sequencers import RKGAGroupingSequencer, BRKGAGroupingSequencer, OBRKGAGroupingSequencer
import numpy as np


class BaseSchedulingSequencer:
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        raise NotImplementedError


class EDDSchedulingSequencer(BaseSchedulingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: np.average(batch_list[i].due_date_list))


class MBSchedulingSequencer(BaseSchedulingSequencer):
    # most job first?
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: len(batch_list[i].placed_job_list), reverse=True)


class RKGASchedulingSequencer(BaseSchedulingSequencer, RKGAGroupingSequencer):
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        param = cfg.GAsequencer_parameter
        heuristic_sequencers = [
            EDDSchedulingSequencer(),
            MBSchedulingSequencer()
        ]
        return self.run_genetic_algorithm(scheduler, batch_list, machines, param, heuristic_sequencers)


class BRKGASchedulingSequencer(RKGASchedulingSequencer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouping_sequencer = BRKGAGroupingSequencer()

    def generate_new_population(self, *args, **kwargs):
        return self.grouping_sequencer.generate_new_population(*args, **kwargs)

    def select_parents(self, *args, **kwargs):
        return self.grouping_sequencer.select_parents(*args, **kwargs)

    @staticmethod
    def crossover(*args, **kwargs):
        return BRKGAGroupingSequencer.crossover(*args, **kwargs)


class OBRKGASchedulingSequencer(BRKGASchedulingSequencer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouping_sequencer = OBRKGAGroupingSequencer()

    def initialize_population(self, *args, **kwargs):
        return self.grouping_sequencer.initialize_population(*args, **kwargs)
