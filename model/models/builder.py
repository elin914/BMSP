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
scheduling_sequencer_dispatcher = {'EDD': EDDSchedulingSequencer, 'MB': MBSchedulingSequencer,
                                   'RKGA': RKGASchedulingSequencer, 'BRKGA': BRKGASchedulingSequencer,
                                   'OBRKGA': OBRKGASchedulingSequencer}
scheduler_dispatcher = {'GL': GLScheduler, 'IBH': IBHScheduler}
integrated_scheduler_dispatcher = {'CP': CPIntegratedScheduler, 'CP2': CPIntegratedScheduler2}
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

    def solve(self, cfg, job_list, machines):
        job_sequence_list = self.grouping_sequencer.get_sequence_list(cfg, self.grouper, job_list, machines)
        batch_list = self.grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
        batch_sequence_list = self.scheduling_sequencer.get_sequence_list(cfg, self.scheduler, batch_list, machines)
        return self.scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)


class SequentialGroupingIntegratedSchedulingModel:
    def __init__(self, grouping_sequencer, grouper, integrated_scheduler):
        self.grouping_sequencer = grouping_sequencer
        self.grouper = grouper
        self.integrated_scheduler = integrated_scheduler

    def solve(self, cfg, job_list, machines):
        job_sequence_list = self.grouping_sequencer.get_sequence_list(cfg, self.grouper, job_list, machines)
        batch_list = self.grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
        return self.integrated_scheduler.get_schedule(cfg, batch_list, machines)


class IntegratedGroupingSequentialSchedulingModel:
    def __init__(self, integrated_grouper, scheduling_sequencer, scheduler):
        self.integrated_grouper = integrated_grouper
        self.scheduling_sequencer = scheduling_sequencer
        self.scheduler = scheduler

    def solve(self, cfg, job_list, machines):
        batch_list = self.integrated_grouper.create_batch_list(cfg, job_list, machines)
        batch_sequence_list = self.scheduling_sequencer.get_sequence_list(cfg, self.scheduler, batch_list, machines)
        return self.scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)


class IntegratedGroupingIntegratedSchedulingModel:
    def __init__(self, integrated_grouper, integrated_scheduler):
        self.integrated_scheduler = integrated_scheduler
        self.integrated_grouper = integrated_grouper

    def solve(self, cfg, job_list, machines):
        batch_list = self.integrated_grouper.create_batch_list(cfg, job_list, machines)
        return self.integrated_scheduler.get_schedule(cfg, batch_list, machines)


def model_builder(cfg):
    model_type = cfg.model_type
    if model_type == 'Integrated':
        integrated_solver = integrated_solver_dispatcher[cfg.integrated_solver]()
        return IntegratedModel(integrated_solver)
    elif model_type == 'Sequential_Sequential':
        grouping_sequencer = grouping_sequencers_dispatcher[cfg.grouping_sequencer]()
        grouper = grouper_dispatcher[cfg.grouper]()
        scheduling_sequencer = scheduling_sequencer_dispatcher[cfg.scheduling_sequencer]()
        scheduler = scheduler_dispatcher[cfg.scheduler]()
        return SequentialGroupingSequentialSchedulingModel(grouping_sequencer, grouper, scheduling_sequencer, scheduler)
    elif model_type == 'Sequential_Integrated':
        grouping_sequencer = grouping_sequencers_dispatcher[cfg.grouping_sequencer]()
        grouper = grouper_dispatcher[cfg.grouper]()
        integrated_scheduler = integrated_scheduler_dispatcher[cfg.integrated_scheduler]()
        return SequentialGroupingIntegratedSchedulingModel(grouping_sequencer, grouper, integrated_scheduler)
    elif model_type == 'Integrated_Sequential':
        integrated_grouper = integrated_grouper_dispatcher[cfg.integrated_grouper]()
        scheduling_sequencer = scheduling_sequencer_dispatcher[cfg.scheduling_sequencer]()
        scheduler = scheduler_dispatcher[cfg.scheduler]()
        return IntegratedGroupingSequentialSchedulingModel(integrated_grouper, scheduling_sequencer, scheduler)
    elif model_type == 'Integrated_Integrated':
        integrated_grouper = integrated_grouper_dispatcher[cfg.integrated_grouper]()
        integrated_scheduler = integrated_scheduler_dispatcher[cfg.integrated_scheduler]()
        return IntegratedGroupingIntegratedSchedulingModel(integrated_grouper, integrated_scheduler)
    else:
        raise ValueError(f"지원하지 않는 모델 타입입니다: {model_type}")
