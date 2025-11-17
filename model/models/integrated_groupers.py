from typing import List
from model.data import Job, Batch, PlacedJob
from docplex.cp.model import *
from .grouping_sequencers import EDDGroupingSequencer, SSTGroupingSequencer, SAGroupingSequencer, LAGroupingSequencer
from .groupers import AdjustedBFFPacker


class BaseIntegratedGrouper:
    def create_batch_list(self, cfg, job_list: List[Job], machines) -> List[Batch]: raise NotImplementedError


class CPGrouper(BaseIntegratedGrouper):
    def create_batch_list(self, cfg, job_list: List[Job], machines) -> List[Batch]:
        heuristic_sequencers = [
            EDDGroupingSequencer(),
            SSTGroupingSequencer(),
            SAGroupingSequencer(),
            LAGroupingSequencer()
        ]
        grouper = AdjustedBFFPacker()
        best_batch_list = list()
        best_fitness = float('inf')
        for sequencer in heuristic_sequencers:
            job_sequence_list = sequencer.get_sequence_list(None, None, job_list, None)
            current_batch_list, current_delay = grouper.create_batch_list(cfg, job_list, job_sequence_list, machines)
            current_fitness = len(current_batch_list) * 10000 + current_delay
            if current_fitness < best_fitness:
                best_batch_list = current_batch_list
                best_fitness = current_fitness

        # 초기해 이용방법 찾기
        n_bin = len(best_batch_list) + 1
        batch_list = list()
        model = CpoModel()
        bin_var_dict = dict()
        x_var_dict = dict()
        x_var_list_dict = dict()
        y_var_dict = dict()
        y_var_list_dict = dict()
        for i, job in enumerate(job_list):
            x_var_dict[i] = model.interval_var()
            y_var_dict[i] = model.interval_var()
            x_var_list_dict[i] = []
            y_var_list_dict[i] = []

            bin_var_dict[i] = model.integer_var(1, n_bin)
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
        delay_obj = 0
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
                    # if abs(job1.due_date - job2.due_date) >= 0 and job1.family == job2.family:
                    #     delay_obj += abs(job1.due_date - job2.due_date) * (bin_var_dict[i] == bin_var_dict[j])
                    if abs(job1.release_date - job2.release_date) >= 0 and job1.family == job2.family:
                        delay_obj += abs(job1.release_date - job2.release_date) * (bin_var_dict[i] == bin_var_dict[j])

        # bin_assinged_var_list = [model.binary_var() for _ in range(n_bin)]
        # for i in range(len(job_list)):
        #     model.add(model.element(bin_assinged_var_list, bin_var_dict[i] - 1) == 1)
        # model.minimize(10000 * model.sum(bin_assinged_var_list) + delay_obj)

        num_bin_used = model.integer_var(0, n_bin)
        model.add(num_bin_used == model.count_different(list(bin_var_dict.values())))
        # upper bound
        # model.add(10000 * num_bin_used + delay_obj <= best_fitness)
        model.minimize(10000 * num_bin_used + delay_obj)

        if cfg.use_starting_point:
            start_sol = CpoModelSolution()
            for b_idx, batch in enumerate(best_batch_list):
                bin_value = b_idx + 1
                for placed_job in batch.placed_job_list:
                    j_idx = placed_job.job.idx
                    start_sol.add_integer_var_solution(bin_var_dict[j_idx], bin_value)
                    if placed_job.rotation:
                        start_sol.add_interval_var_solution(x_var_dict[j_idx],
                                                            start=placed_job.x, size=placed_job.height)
                        start_sol.add_interval_var_solution(y_var_dict[j_idx],
                                                            start=placed_job.y, size=placed_job.width)
                    else:
                        start_sol.add_interval_var_solution(x_var_dict[j_idx],
                                                            start=placed_job.x, size=placed_job.width)
                        start_sol.add_interval_var_solution(y_var_dict[j_idx],
                                                            start=placed_job.y, size=placed_job.height)
            model.set_starting_point(start_sol)

        sol = model.solve(TimeLimit=cfg.cp_search_time_limit, SearchType='Auto')
        if sol:
            placed_job_list_dict = dict()
            for i, job in enumerate(job_list):
                b_idx = sol.get_var_solution(bin_var_dict[i]).get_value()
                x = sol.get_var_solution(x_var_dict[i]).get_start()
                y = sol.get_var_solution(y_var_dict[i]).get_start()
                if (sol.get_var_solution(x_var_dict[i]).get_size() == job.width
                        and sol.get_var_solution(y_var_dict[i]).get_size() == job.height):
                    rotation = False
                else:
                    rotation = True

                if b_idx not in placed_job_list_dict:
                    placed_job_list_dict[b_idx] = list()
                placed_job_list_dict[b_idx].append(PlacedJob(job, rotation, x, y))
            for i, placed_job_list in enumerate(placed_job_list_dict.values()):
                batch = Batch(i, machines.width, machines.height)
                batch.placed_job_list = placed_job_list
                batch.update_by_placed_job_list()
                batch_list.append(batch)

            delay_obj = 0
            for batch in batch_list:
                batch_delay = 0
                current_sum = 0
                for i, date in enumerate(sorted(batch.due_date_list)):
                    batch_delay += i * date - current_sum
                    current_sum += date
                delay_obj += batch_delay
            print(len(batch_list), delay_obj)
            return batch_list
        else:
            # 휴리스틱 초기 해 리턴으로 정의
            return best_batch_list
