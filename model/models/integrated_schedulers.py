from typing import List, Tuple
from model.data import Batch
from docplex.cp.model import *
from docplex.cp.solver.solver_listener import CpoSolverListener


class BaseIntegratedScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], machines) -> Tuple[List[int], int]: raise NotImplementedError


class ObjectiveHistoryListener(CpoSolverListener):
    def __init__(self):
        super().__init__()
        self.obj_history = []

    def new_result(self, solver, sol):
        current_obj = sol.get_objective_value()
        self.obj_history.append(current_obj)


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], machines):
        heuristic_sequencers = cfg.heuristic_scheduling_sequencer
        scheduler = cfg.local_scheduler
        best_schedule_list = list()
        best_fitness = float('inf')
        best_sequencer = None
        for sequencer in heuristic_sequencers:
            batch_sequence_list = sequencer.get_sequence_list(None, batch_list, None)
            current_schedule_list, current_fitness =\
                scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)
            if current_fitness < best_fitness:
                best_schedule_list = current_schedule_list
                best_fitness = current_fitness
                best_sequencer = sequencer

        model = CpoModel()
        end_time = max(batch_list[b_idx].end_time for schedule in best_schedule_list for b_idx in schedule)
        batch_var_dict = dict()
        obj = 0
        load_function = model.step_at(0, 0)
        for b_idx, batch in enumerate(batch_list):
            var = model.interval_var(start=(batch.max_release_date, end_time), size=batch.processing_time)
            load_function += model.pulse(var, 1)
            obj += model.sum([model.abs(due_date - model.end_of(var)) for due_date in batch.due_date_list])
            # for _, var2 in batch_var_dict.items():
            #     model.add(model.start_of(var) != model.start_of(var2))
            batch_var_dict[b_idx] = var
        all_start_times = [model.start_of(var) for var in batch_var_dict.values()]
        model.add(model.all_diff(all_start_times))
        model.add(load_function <= machines.n_machine)
        model.add(model.minimize(obj))

        obj_listener = ObjectiveHistoryListener()
        model.add_solver_listener(obj_listener)

        if cfg.use_starting_point:
            batch_sequence_list = best_sequencer.get_sequence_list(None, batch_list, None)
            best_schedule_list, best_fitness = \
                scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)
            start_sol = CpoModelSolution()
            for b_idx, batch in enumerate(batch_list):
                start_sol.add_interval_var_solution(batch_var_dict[b_idx], start=batch.start_time)
            model.set_starting_point(start_sol)

        sol = model.solve(TimeLimit=cfg.cp_search_time_limit, SearchType='IterativeDiving')

        if sol:
            print(f"Final objective value: {sol.get_objective_value()}")
            print("Objective value history (변화 과정):")
            print(obj_listener.obj_history)
            schedule_list = [[] for _ in range(machines.n_machine)]
            total_fitness = 0
            for b_idx, var in batch_var_dict.items():
                batch = batch_list[b_idx]
                batch.start_time = sol.get_var_solution(var).get_start()
                batch.end_time = sol.get_var_solution(var).get_end()
                batch.delay_time = sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
                total_fitness += batch.delay_time
            schedule_list[0] = sorted(range(len(batch_list)), key=lambda i: batch_list[i].end_time)
            return schedule_list, total_fitness
        else:
            return best_schedule_list, best_fitness
