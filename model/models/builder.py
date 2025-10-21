from .sequencers import *
from .packers import *
from .groupers import *
from .schedulers import *
from .integrated_schedulers import *

sequencing_dispatcher = {'SPT': SPTSequencer, 'LPT': LPTSequencer, 'EDD': EDDSequencer, 'MS': MSSequencer}
packing_dispatcher = {'BFF': BFFPacker, 'ABFF': AdujustedBFFPacker}
grouping_dispatcher = {'CP': CPGrouper}
scheduling_dispatcher = {'IBH': IBHScheduler}
integrated_scheduling_dispatcher = {'CP': CPIntegratedScheduler}


class TwoPhaseSequenceGrouping:
    def __init__(self, sequencer, packer, scheduler):
        self.sequencer = sequencer
        self.packer = packer
        self.scheduler = scheduler

    def solve(self, job_list, machines):
        job_sequence_list = self.sequencer.get_sequence_list(job_list, machines)
        batch_list = self.packer.create_batch_list(job_list, job_sequence_list, machines)
        final_schedule = self.scheduler.get_schedule(batch_list)
        return final_schedule


class TwoPhaseIntegratedGrouping:
    def __init__(self, grouper, scheduler):
        self.grouper = grouper
        self.scheduler = scheduler

    def solve(self, job_list, machines):
        batch_list = self.grouper.create_batch_list(job_list, machines)
        final_schedule = self.scheduler.get_schedule(batch_list)
        return final_schedule


class IntegratedScheduling:
    def __init__(self, integrated_scheduler):
        self.integrated_scheduler = integrated_scheduler

    def solve(self, job_list, machines):
        return self.integrated_scheduler.get_schedule(job_list, machines)


def model_builder(config):
    model_type = config.model_type

    if model_type == '2_phase_sequence':
        sequencer = sequencing_dispatcher[config.sequencer]()
        packer = packing_dispatcher[config.packer]()
        scheduler = scheduling_dispatcher[config.scheduler]()

        return TwoPhaseSequenceGrouping(sequencer, packer, scheduler)

    elif model_type == '2_phase_integrated':
        grouper = grouping_dispatcher[config.grouper]()
        scheduler = scheduling_dispatcher[config.scheduler]()

        return TwoPhaseIntegratedGrouping(grouper, scheduler)

    elif model_type == 'integrated':
        integrated_scheduler = integrated_scheduling_dispatcher[config.integrated_scheduler]()
        return IntegratedScheduling(integrated_scheduler)
    else:
        raise ValueError(f"지원하지 않는 모델 타입입니다: {model_type}")
