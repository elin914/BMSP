from .integrated_solver import *
from .grouping_sequencers import *
from .groupers import *
from .integrated_groupers import *
from .scheduling_sequencers import *
from .schedulers import *
from .integrated_schedulers import *

integrated_solver_dispatcher = {'CP': CPSolver}
grouping_sequencers_dispatcher = {'EDD': EDDGroupingSequencer, 'SST': SSTGroupingSequencer,
                                  'SA': SAGroupingSequencer, 'LA': LAGroupingSequencer,
                                  'RKGA': RKGAGroupingSequencer, 'BRKGA': BRKGAGroupingSequencer,
                                  'OBRKGA': OBRKGAGroupingSequencer}
grouper_dispatcher = {'BFF': BFFPacker, 'ABFF': AdjustedBFFPacker}
integrated_grouper_dispatcher = {'CP': CPGrouper}
scheduling_sequencer_dispatcher = {'LDD': LDDSchedulingSequencer,
                                   'EDD': EDDSchedulingSequencer, 'MB': MBSchedulingSequencer,
                                   'RKGA': RKGASchedulingSequencer, 'BRKGA': BRKGASchedulingSequencer,
                                   'OBRKGA': OBRKGASchedulingSequencer}
scheduler_dispatcher = {'GL': GLScheduler, 'IBH': IBHScheduler, 'BW': BackWardScheduler}
integrated_scheduler_dispatcher = {'CP': CPIntegratedScheduler}
                                   # 'ATC': ATCIntegratedScheduler, 'COVERT': COVERTIntegratedScheduler}


class IntegratedModel:
    def __init__(self, integrated_solver):
        self.integrated_solver = integrated_solver

    def solve(self, cfg, job_list, machines):
        return self.integrated_solver.get_schedule(cfg, job_list, machines)


class SequentialGroupingSequentialSchedulingModel:
    def __init__(self, grouping_sequencer, grouper, scheduling_sequencer, scheduler):
        self.grouping_sequencer = grouping_sequencer
        self.grouper = grouper
        self.scheduling_sequencer = scheduling_sequencer
        self.scheduler = scheduler

    def solve_phase1(self, cfg, job_list, machines):
        job_sequence_list = self.grouping_sequencer.get_sequence_list(cfg, job_list, machines)
        batch_list, fitness = self.grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
        return batch_list, fitness

    def solve_phase2(self, cfg, batch_list, machines):
        batch_sequence_list = self.scheduling_sequencer.get_sequence_list(cfg, batch_list, machines)
        return self.scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)


class SequentialGroupingIntegratedSchedulingModel:
    def __init__(self, grouping_sequencer, grouper, integrated_scheduler):
        self.grouping_sequencer = grouping_sequencer
        self.grouper = grouper
        self.integrated_scheduler = integrated_scheduler

    def solve_phase1(self, cfg, job_list, machines):
        job_sequence_list = self.grouping_sequencer.get_sequence_list(cfg, job_list, machines)
        batch_list, fitness = self.grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
        return batch_list, fitness

    def solve_phase2(self, cfg, batch_list, machines):
        return self.integrated_scheduler.get_schedule(cfg, batch_list, machines)


class IntegratedGroupingSequentialSchedulingModel:
    def __init__(self, integrated_grouper, scheduling_sequencer, scheduler):
        self.integrated_grouper = integrated_grouper
        self.scheduling_sequencer = scheduling_sequencer
        self.scheduler = scheduler

    def solve(self, cfg, job_list, machines):
        batch_list = self.integrated_grouper.create_batch_list(cfg, job_list, machines)
        batch_sequence_list = self.scheduling_sequencer.get_sequence_list(cfg, batch_list, machines)
        return self.scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)


class IntegratedGroupingIntegratedSchedulingModel:
    def __init__(self, integrated_grouper, integrated_scheduler):
        self.integrated_scheduler = integrated_scheduler
        self.integrated_grouper = integrated_grouper

    def solve(self, cfg, job_list, machines):
        batch_list = self.integrated_grouper.create_batch_list(cfg, job_list, machines)
        return self.integrated_scheduler.get_schedule(cfg, batch_list, machines)


def test_model_builder(cfg):
    cfg.heuristic_grouping_sequencer = [grouping_sequencers_dispatcher[key]()
                                        for key in cfg.heuristic_grouping_sequencer]
    cfg.heuristic_scheduling_sequencer = [scheduling_sequencer_dispatcher[key]()
                                          for key in cfg.heuristic_scheduling_sequencer]
    cfg.local_grouper = grouper_dispatcher[cfg.local_grouper]()
    cfg.local_scheduler = scheduler_dispatcher[cfg.local_scheduler]()

    grouping_sequencer = grouping_sequencers_dispatcher[cfg.grouping_sequencer]()
    grouper = grouper_dispatcher[cfg.grouper]()
    scheduling_sequencer = scheduling_sequencer_dispatcher[cfg.scheduling_sequencer]()
    scheduler = scheduler_dispatcher[cfg.scheduler]()
    integrated_scheduler = integrated_scheduler_dispatcher[cfg.integrated_scheduler]()
    model_s = SequentialGroupingSequentialSchedulingModel(grouping_sequencer, grouper, scheduling_sequencer, scheduler)
    model_c = SequentialGroupingIntegratedSchedulingModel(grouping_sequencer, grouper, integrated_scheduler)

    return model_s, model_c
