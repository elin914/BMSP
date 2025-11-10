from typing import List, Tuple
from model.data import Batch
from docplex.cp.model import *
from .schedulers import BaseScheduler


class BaseIntegratedScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], machines):
        model = CpoModel()
        end_time = max([max(batch.due_date_list) for batch in batch_list]) + 10000

        batch_var_dict = dict()
        machine_interval_lists = [[] for _ in range(machines.n_machine)]
        batch_presence_of_lists = [[] for _ in range(len(batch_list))]
        obj = 0

        for b_idx, batch in enumerate(batch_list):
            for m_idx in range(machines.n_machine):
                var = model.interval_var(start=(batch.max_release_date, end_time),
                                         size=batch.processing_time, optional=True)
                batch_var_dict[(b_idx, m_idx)] = var
                machine_interval_lists[m_idx].append(var)
                batch_presence_of_lists[b_idx].append(model.presence_of(var))
                obj += model.sum([model.presence_of(var) * model.max(0, model.end_of(var) - due_date)
                                  for due_date in batch_list[b_idx].due_date_list])
        for var_list in batch_presence_of_lists:
            model.add(model.sum(var_list) == 1)

        for m_idx in range(machines.n_machine):
            model.add(model.no_overlap(machine_interval_lists[m_idx]))

        model.add(model.minimize(obj))
        sol = model.solve(TimeLimit=1800, SearchType='IterativeDiving')

        machine_solution_list = [dict() for _ in range(machines.n_machine)]
        schedule_list = [[] for _ in range(machines.n_machine)]
        for (b_idx, m_idx), var in batch_var_dict.items():
            if sol.get_var_solution(var).presence:
                machine_solution_list[m_idx][b_idx] = sol.get_var_solution(var).get_start()
        total_tardiness = 0
        for m_idx, solution_list in enumerate(machine_solution_list):
            schedule_list[m_idx] = [key for key, _ in sorted(solution_list.items(), key=lambda item: item[1])]
            total_tardiness += BaseScheduler.calculate_single_machine_tardiness(schedule_list[m_idx], batch_list)
        return schedule_list, total_tardiness


class CPIntegratedScheduler2(BaseIntegratedScheduler):
    """
    integer로 변형한 함수인데 성능이 별로임...
    """
    def get_schedule(self, cfg, batch_list: List[Batch], machines):
        model = CpoModel()
        machine_var_dict = dict()
        sequence_var_dict = dict()
        completion_var_dict = dict()
        tardiness_var_list = list()
        max_completion = int(sum(b.processing_time for b in batch_list) / 5)
        for b_idx, batch in enumerate(batch_list):
            machine_var = model.integer_var(1, machines.n_machine)
            machine_var_dict[b_idx] = machine_var
            batch_sequence_var = model.integer_var(1, len(batch_list))
            sequence_var_dict[b_idx] = batch_sequence_var
            completion_var = model.integer_var(batch.max_release_date, max_completion)
            completion_var_dict[b_idx] = completion_var
            for placed_job in batch.placed_job_list:
                tardiness_var = model.integer_var(0, max_completion)
                model.add(tardiness_var >= completion_var - placed_job.due_date)
                tardiness_var_list.append(tardiness_var)

        for b_idx1, batch1 in enumerate(batch_list):
            for b_idx2, batch2 in enumerate(batch_list):
                if b_idx1 < b_idx2:
                    model.add(model.any([
                        machine_var_dict[b_idx1] != machine_var_dict[b_idx2],
                        model.all([
                            machine_var_dict[b_idx1] == machine_var_dict[b_idx2],
                            sequence_var_dict[b_idx1] != sequence_var_dict[b_idx2]
                        ])
                    ]))
                if b_idx1 != b_idx2:
                    model.add(model.any([
                        model.any([machine_var_dict[b_idx1] != machine_var_dict[b_idx2],
                                  sequence_var_dict[b_idx1] >= sequence_var_dict[b_idx2]]),
                        completion_var_dict[b_idx2] >= completion_var_dict[b_idx1] + batch2.processing_time
                    ]))
        model.minimize(model.sum(tardiness_var_list))

        sol = model.solve(TimeLimit=300, SearchType='IterativeDiving')
        machine_solution_list = [dict() for _ in range(machines.n_machine)]
        schedule_list = [[] for _ in range(machines.n_machine)]
        for b_idx, batch in enumerate(batch_list):
            m_idx = sol.get_var_solution(machine_var_dict[b_idx]).get_value()
            s_idx = sol.get_var_solution(sequence_var_dict[b_idx]).get_value()
            machine_solution_list[m_idx - 1][b_idx] = s_idx
        total_tardiness = 0
        for m_idx, solution_list in enumerate(machine_solution_list):
            schedule_list[m_idx] = [key for key, _ in sorted(solution_list.items(), key=lambda item: item[1])]
            total_tardiness += BaseScheduler.calculate_single_machine_tardiness(schedule_list[m_idx], batch_list)
        return schedule_list, total_tardiness
