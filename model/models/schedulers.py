from typing import List, Tuple
from model.data import Batch
import numpy as np


class BaseScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        raise NotImplementedError

    @staticmethod
    def calculate_single_machine_tardiness(batch_sequence_list, batch_list):
        completion_time = 0
        tardiness = 0
        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            completion_time = max(batch.max_release_date, completion_time) + batch.processing_time
            for due_date in batch.due_date_list:
                tardiness += max(0, completion_time - due_date)
        return tardiness

    @staticmethod
    def calculate_single_machine_jit(batch_sequence_list, batch_list):
        jit = 0
        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            jit += sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
        return jit

    def calculate_fitness(self, cfg, batch_sequence_list, batch_list, machines, fitness_cache):
        if tuple(batch_sequence_list) in fitness_cache:
            return fitness_cache[tuple(batch_sequence_list)]
        schedule_list, fitness = self.get_schedule(cfg, batch_list, batch_sequence_list, machines)
        fitness_cache[tuple(batch_sequence_list)] = fitness
        return fitness


class GLScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        machine_available_time_list = [0] * machines.n_machine
        schedule_list = [[] for _ in range(machines.n_machine)]
        total_tardiness = 0

        for idx in batch_sequence_list:
            best_machine_idx = -1
            best_machine_tardiness = float('inf')
            batch = batch_list[idx]
            # 모든 기계를 확인하여 이 배치를 가장 빨리 끝낼 수 있는 기계 탐색
            for m_idx in range(machines.n_machine):
                completion_time = (max(machine_available_time_list[m_idx], batch.max_release_date)
                                   + batch.processing_time)
                new_tardiness = 0
                for due_date in batch.due_date_list:
                    new_tardiness += max(0, completion_time - due_date)
                if new_tardiness < best_machine_tardiness:
                    best_machine_idx = m_idx
                    best_machine_tardiness = new_tardiness
                elif (new_tardiness == best_machine_tardiness
                      and machine_available_time_list[m_idx] > machine_available_time_list[best_machine_idx]):
                    best_machine_idx = m_idx

            schedule_list[best_machine_idx].append(batch.idx)
            machine_available_time_list[best_machine_idx] =\
                max(machine_available_time_list[best_machine_idx], batch.max_release_date) + batch.processing_time

            total_tardiness += best_machine_tardiness

        return schedule_list, total_tardiness


class IBHScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        schedule_list = [[] for _ in range(machines.n_machine)]
        machine_tardiness_list = [0] * machines.n_machine

        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            tardiness_dict = dict()
            for m_idx in range(machines.n_machine):
                for insert_pos_idx in range(len(schedule_list[m_idx]) + 1):
                    temp_schedule = schedule_list[m_idx][:]
                    temp_schedule.insert(insert_pos_idx, batch.idx)
                    temp_tardiness = self.calculate_single_machine_tardiness(temp_schedule, batch_list)
                    tardiness_dict[m_idx, insert_pos_idx] = temp_tardiness - machine_tardiness_list[m_idx]
            min_tardiness = min(tardiness_dict.values())
            (m_idx, insert_pos_idx) =\
                sorted([key for key, value in tardiness_dict.items() if value == min_tardiness])[0]
            schedule_list[m_idx].insert(insert_pos_idx, batch.idx)
            machine_tardiness_list[m_idx] = self.calculate_single_machine_tardiness(schedule_list[m_idx], batch_list)

        return schedule_list, sum(machine_tardiness_list)


class BackWardScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        schedule_list = [[] for _ in range(machines.n_machine)]

        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            if len(batch.due_date_list) % 2:
                ideal_end = int(np.median(batch.due_date_list))
            else:
                ideal_end = sorted(batch.due_date_list)[len(batch.due_date_list) // 2]
            ideal_start = ideal_end - batch.processing_time
            start_time_list = [batch_list[b_idx].start_time for schedule in schedule_list for b_idx in schedule]
            while ideal_start in start_time_list:
                ideal_start -= 1
                if ideal_start < batch.max_release_date:
                    ideal_start = ideal_end - batch.processing_time + 1
                    break
            while ideal_start < batch.max_release_date or ideal_start in start_time_list:
                ideal_start += 1
            ideal_end = ideal_start + batch.processing_time

            is_push = False
            best_m_idx = None
            best_slack_time = float('inf')
            for m_idx in range(machines.n_machine):
                if not schedule_list[m_idx]:
                    best_m_idx = m_idx
                    break
            while best_m_idx is None and not is_push:
                for m_idx in range(machines.n_machine):
                    slack_time = batch_list[schedule_list[m_idx][0]].start_time - ideal_end
                    if 0 <= slack_time <= best_slack_time:
                        best_m_idx = m_idx
                        best_slack_time = slack_time
                if best_m_idx is not None:
                    break
                else:
                    ideal_start -= 1
                    if ideal_start < batch.max_release_date:
                        is_push = True
                        ideal_start = batch.max_release_date
                        while ideal_start in start_time_list:
                            ideal_start += 1
                    else:
                        while ideal_start in start_time_list:
                            ideal_start -= 1
                            if ideal_start < batch.max_release_date:
                                ideal_start = batch.max_release_date
                                is_push = True
                                while ideal_start in start_time_list:
                                    ideal_start += 1
                                break
                    ideal_end = ideal_start + batch.processing_time

            if is_push:
                best_delay_sum = float('inf')
                for m_idx in range(machines.n_machine):
                    delay_sum = 0
                    completion_time = ideal_end
                    for b_idx2 in schedule_list[m_idx]:
                        batch2 = batch_list[b_idx2]
                        if batch2.start_time < completion_time:
                            while completion_time in start_time_list:
                                completion_time += 1
                            completion_time += batch2.processing_time
                            temp_end_time = completion_time
                            delay_sum += sum(abs(due_date - temp_end_time)
                                             for due_date in batch2.due_date_list) - batch2.delay_time
                        else:
                            break
                    if delay_sum < best_delay_sum:
                        best_delay_sum = delay_sum
                        best_m_idx = m_idx

                completion_time = ideal_end
                for b_idx2 in schedule_list[best_m_idx]:
                    batch2 = batch_list[b_idx2]
                    if batch2.start_time < completion_time:
                        while completion_time in start_time_list:
                            completion_time += 1
                        batch2.start_time = completion_time
                        completion_time += batch2.processing_time
                        batch2.end_time = completion_time
                        batch2.delay_time = sum(abs(batch2.end_time - due_date) for due_date in batch2.due_date_list)
            batch.start_time = ideal_start
            batch.end_time = ideal_end
            batch.delay_time = sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
            schedule_list[best_m_idx].insert(0, b_idx)

        fitness = 0
        for batch in batch_list:
            fitness += batch.delay_time
        return schedule_list, fitness
