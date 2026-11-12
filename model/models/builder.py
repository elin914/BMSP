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
                                  'OBRKGA': OBRKGAGroupingSequencer,
                                  'SimA': SimAGroupingSequencer, 'Tabu': TabuGroupingSequencer}
grouper_dispatcher = {'BFF': BFFPacker, 'ABFF': AdjustedBFFPacker}
integrated_grouper_dispatcher = {'CP': CPGrouper}
scheduling_sequencer_dispatcher = {'LDD': LDDSchedulingSequencer,
                                   'EDD': EDDSchedulingSequencer, 'MB': MBSchedulingSequencer,
                                   'RKGA': RKGASchedulingSequencer, 'BRKGA': BRKGASchedulingSequencer,
                                   'OBRKGA': OBRKGASchedulingSequencer,
                                   'SimA': SimASchedulingSequencer, 'Tabu': TabuSchedulingSequencer}
scheduler_dispatcher = {'GL': GLScheduler, 'IBH': IBHScheduler, 'BW': BackWardScheduler,
                        'RBW': RealBackWardScheduler}
integrated_scheduler_dispatcher = {'CP': CPIntegratedScheduler, 'RCP': RealCPIntegratedScheduler}
                                   # 'ATC': ATCIntegratedScheduler, 'COVERT': COVERTIntegratedScheduler}


class IntegratedModel:
    """묶기 + 스케줄링을 CP 하나로 푸는 모델"""
    def __init__(self, integrated_solver):
        self.integrated_solver = integrated_solver
        self.batch_list = None

    def solve(self, cfg, job_list, machines):
        schedule_list, fitness = self.integrated_solver.get_schedule(cfg, job_list, machines)
        self.batch_list = self.integrated_solver.batch_list
        return schedule_list, fitness


class TwoPhaseModel:
    """1단계(묶기) -> 2단계(스케줄링) 공통 구조.
    solve_phase1: (batch_list, phase1_fitness), solve_phase2: (schedule_list, fitness)
    마지막 batch_list는 self.batch_list에 남겨 검증/결과 저장에 쓸 수 있게 함."""
    def __init__(self):
        self.batch_list = None

    def solve_phase1(self, cfg, job_list, machines):
        raise NotImplementedError

    def solve_phase2(self, cfg, batch_list, machines):
        raise NotImplementedError

    def solve(self, cfg, job_list, machines):
        batch_list, phase1_fitness = self.solve_phase1(cfg, job_list, machines)
        print(phase1_fitness)
        return self.solve_phase2(cfg, batch_list, machines)


class SequentialGroupingMixin:
    def solve_phase1(self, cfg, job_list, machines):
        job_sequence_list = self.grouping_sequencer.get_sequence_list(cfg, job_list, machines)
        batch_list, fitness = self.grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
        self.batch_list = batch_list
        return batch_list, fitness


class IntegratedGroupingMixin:
    def solve_phase1(self, cfg, job_list, machines):
        batch_list = self.integrated_grouper.create_batch_list(cfg, job_list, machines)
        self.batch_list = batch_list
        return batch_list, len(batch_list)  # CPGrouper는 fitness를 따로 반환하지 않음


class SequentialSchedulingMixin:
    def solve_phase2(self, cfg, batch_list, machines):
        self.batch_list = batch_list
        batch_sequence_list = self.scheduling_sequencer.get_sequence_list(cfg, batch_list, machines)
        return self.scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)


class IntegratedSchedulingMixin:
    def solve_phase2(self, cfg, batch_list, machines):
        self.batch_list = batch_list
        return self.integrated_scheduler.get_schedule(cfg, batch_list, machines)


class SequentialGroupingSequentialSchedulingModel(SequentialGroupingMixin, SequentialSchedulingMixin, TwoPhaseModel):
    def __init__(self, grouping_sequencer, grouper, scheduling_sequencer, scheduler):
        super().__init__()
        self.grouping_sequencer = grouping_sequencer
        self.grouper = grouper
        self.scheduling_sequencer = scheduling_sequencer
        self.scheduler = scheduler


class SequentialGroupingIntegratedSchedulingModel(SequentialGroupingMixin, IntegratedSchedulingMixin, TwoPhaseModel):
    def __init__(self, grouping_sequencer, grouper, integrated_scheduler):
        super().__init__()
        self.grouping_sequencer = grouping_sequencer
        self.grouper = grouper
        self.integrated_scheduler = integrated_scheduler


class IntegratedGroupingSequentialSchedulingModel(IntegratedGroupingMixin, SequentialSchedulingMixin, TwoPhaseModel):
    def __init__(self, integrated_grouper, scheduling_sequencer, scheduler):
        super().__init__()
        self.integrated_grouper = integrated_grouper
        self.scheduling_sequencer = scheduling_sequencer
        self.scheduler = scheduler


class IntegratedGroupingIntegratedSchedulingModel(IntegratedGroupingMixin, IntegratedSchedulingMixin, TwoPhaseModel):
    def __init__(self, integrated_grouper, integrated_scheduler):
        super().__init__()
        self.integrated_grouper = integrated_grouper
        self.integrated_scheduler = integrated_scheduler


def _instantiate(value, dispatcher):
    """설정 이름(str)이면 객체로 만들고, 이미 객체면 그대로 둔다 (같은 cfg로 builder를 여러 번 불러도 안전)"""
    if isinstance(value, list):
        return [_instantiate(v, dispatcher) for v in value]
    return dispatcher[value]() if isinstance(value, str) else value


def prepare_local_components(cfg):
    """메타휴리스틱/CP가 내부에서 쓰는 휴리스틱과 평가용 grouper/scheduler를 cfg에 객체로 준비"""
    cfg.heuristic_grouping_sequencer = _instantiate(cfg.heuristic_grouping_sequencer, grouping_sequencers_dispatcher)
    cfg.heuristic_scheduling_sequencer = _instantiate(cfg.heuristic_scheduling_sequencer,
                                                      scheduling_sequencer_dispatcher)
    cfg.local_grouper = _instantiate(cfg.local_grouper, grouper_dispatcher)
    cfg.local_scheduler = _instantiate(cfg.local_scheduler, scheduler_dispatcher)


def model_builder(cfg):
    prepare_local_components(cfg)
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


def test_model_builder(cfg):
    """실험용: 같은 1단계를 공유하는 (순차 2단계 모델, CP 2단계 모델) 쌍.
    model_s.solve_phase1 -> batch_list, 그 batch_list로 model_s.solve_phase2 / model_c.solve_phase2 비교"""
    prepare_local_components(cfg)
    grouping_sequencer = grouping_sequencers_dispatcher[cfg.grouping_sequencer]()
    grouper = grouper_dispatcher[cfg.grouper]()
    scheduling_sequencer = scheduling_sequencer_dispatcher[cfg.scheduling_sequencer]()
    scheduler = scheduler_dispatcher[cfg.scheduler]()
    integrated_scheduler = integrated_scheduler_dispatcher[cfg.integrated_scheduler]()
    model_s = SequentialGroupingSequentialSchedulingModel(grouping_sequencer, grouper, scheduling_sequencer, scheduler)
    model_c = SequentialGroupingIntegratedSchedulingModel(grouping_sequencer, grouper, integrated_scheduler)
    return model_s, model_c
