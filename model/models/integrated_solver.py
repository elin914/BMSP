from typing import List, Tuple
from model.data import Job
from docplex.cp.model import *


class BaseSolver:
    def get_schedule(self, cfg, job_list: List[Job], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPSolver(BaseSolver):
    def get_schedule(self, cfg, job_list, machines):
        heuristic_sequencers = cfg.heuristic_grouping_sequencer
        grouper = cfg.local_grouper
        best_batch_list = list()
        best_fitness = float('inf')
        for sequencer in heuristic_sequencers:
            job_sequence_list = sequencer.get_sequence_list(None, job_list, None)
            current_batch_list, current_fitness = grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
            current_batch_fitness = len(current_batch_list) * 10000 + current_fitness
            if current_batch_fitness < best_fitness:
                best_batch_list = current_batch_list
                best_fitness = current_batch_fitness

        heuristic_sequencers = cfg.heuristic_scheduling_sequencer
        scheduler = cfg.local_scheduler
        best_schedule_list = list()
        best_fitness = float('inf')
        best_sequencer = None
        best_sequence_list = None
        for sequencer in heuristic_sequencers:
            batch_sequence_list = sequencer.get_sequence_list(None, best_batch_list, None)
            current_schedule_list, current_fitness = \
                scheduler.get_schedule(cfg, best_batch_list, batch_sequence_list, machines)
            if current_fitness < best_fitness:
                best_schedule_list = current_schedule_list
                best_fitness = current_fitness
                best_sequencer = sequencer
                best_sequence_list = batch_sequence_list

        model = CpoModel()
        end_time = max(best_batch_list[b_idx].end_time for schedule in best_schedule_list for b_idx in schedule)
        n_bin = len(best_batch_list) + 1
        batch_var_dict = dict()
        batch_var_list = list()
        bin_var_dict = dict()
        x_var_dict = dict()
        x_var_list_dict = dict()
        y_var_dict = dict()
        y_var_list_dict = dict()

        load_function = model.step_at(0, 0)
        obj1 = 0
        for b_idx in range(n_bin):
            var = model.interval_var(start=(0, end_time), optional=True)
            batch_var_dict[b_idx] = var
            batch_var_list.append(var)
            load_function += model.pulse(var, 1)
            obj1 += model.presence_of(var)
        model.add(load_function <= machines.n_machine)
        obj2 = 0
        for i, job in enumerate(job_list):
            x_var_dict[i] = model.interval_var()
            y_var_dict[i] = model.interval_var()
            x_var_list_dict[i] = []
            y_var_list_dict[i] = []

            b_idx_var = model.integer_var(0, n_bin - 1)
            bin_var_dict[i] = b_idx_var

            presence_list = [model.presence_of(v) for v in batch_var_list]
            model.add(model.element(presence_list, b_idx_var) == 1)
            size_list = [model.size_of(v) for v in batch_var_list]
            model.add(model.element(size_list, b_idx_var) == job.p_time)
            start_list = [model.start_of(v) for v in batch_var_list]
            model.add(model.element(start_list, b_idx_var) >= job.release_date)
            end_list = [model.end_of(v) for v in batch_var_list]
            current_end_time = model.element(end_list, b_idx_var)
            obj2 += model.abs(job.due_date - current_end_time)

            x_var_list_dict[i].append(model.interval_var(start=(0, machines.width), end=(0, machines.width),
                                                         size=job.width, optional=True))
            x_var_list_dict[i].append(model.interval_var(start=(0, machines.width), end=(0, machines.width),
                                                         size=job.height, optional=True))
            y_var_list_dict[i].append(model.interval_var(start=(0, machines.height), end=(0, machines.height),
                                                         size=job.height, optional=True))
            y_var_list_dict[i].append(model.interval_var(start=(0, machines.height), end=(0, machines.height),
                                                         size=job.width, optional=True))
            model.add(model.presence_of(x_var_list_dict[i][0]) == model.presence_of(y_var_list_dict[i][0]))
            model.add(model.presence_of(x_var_list_dict[i][1]) == model.presence_of(y_var_list_dict[i][1]))
            model.add(model.alternative(x_var_dict[i], x_var_list_dict[i]))
            model.add(model.alternative(y_var_dict[i], y_var_list_dict[i]))

        for i, job1 in enumerate(job_list):
            for j, job2 in enumerate(job_list):
                if i < j:
                    if job1.family != job2.family:
                        model.add(bin_var_dict[i] != bin_var_dict[j])
                    else:
                        model.add(
                            model.any([
                                bin_var_dict[i] != bin_var_dict[j],
                                model.all([
                                    bin_var_dict[i] == bin_var_dict[j],
                                    model.any([
                                        model.overlap_length(x_var_dict[i], x_var_dict[j]) == 0,
                                        model.overlap_length(y_var_dict[i], y_var_dict[j]) == 0
                                    ])
                                ])
                            ])
                        )

        all_start_times = [model.start_of(batch_var_list[i], end_time + 10000 + i) for i in range(n_bin)]
        model.add(model.all_diff(all_start_times))
        model.add(model.minimize(obj1 * 10000 + obj2))
        sol = model.solve(TimeLimit=cfg.cp_search_time_limit, SearchType='Auto')

        if sol:
            pass
        else:
            return best_schedule_list, best_fitness

