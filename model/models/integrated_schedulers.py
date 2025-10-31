from typing import List, Tuple
from model.data import Batch
from docplex.cp.model import *


class BaseIntegratedScheduler:
    def get_schedule(self, batch_list: List[Batch], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, batch_list: List[Batch], machines):
        model = CpoModel()
        end_time = max([max(batch.due_date_list) for batch in batch_list]) + 1000

        batch_var_dict = dict()
        machine_sequence_var_list = []
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
            machine_sequence_var_list.append(model.sequence_var(vars=machine_interval_lists[m_idx]))
            model.add(model.no_overlap(machine_sequence_var_list[m_idx]))

        obj_var = model.integer_var()
        model.add(obj_var == obj)
        model.add(model.minimize(obj))
        sol = model.solve(TimeLimit=3600)

        machine_solution_list = [dict() for _ in range(machines.n_machine)]
        schedule_list = [[] for _ in range(machines.n_machine)]
        for (b_idx, m_idx), var in batch_var_dict.items():
            if sol.get_var_solution(var).presence:
                machine_solution_list[m_idx][b_idx] = sol.get_var_solution(var).get_start()
        for m_idx, solution_list in enumerate(machine_solution_list):
            schedule_list[m_idx] = [key for key, _ in sorted(solution_list.items(), key=lambda item: item[1])]
        return schedule_list, sol.get_var_solution(obj_var).get_value()
