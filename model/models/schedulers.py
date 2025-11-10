from typing import List, Tuple
from model.data import Batch


class BaseScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        raise NotImplementedError  # return type은 향후 명시

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

    def calculate_fitness(self, batch_sequence_list, batch_list, machines, fitness_cache):
        if tuple(batch_sequence_list) in fitness_cache:
            return fitness_cache[tuple(batch_sequence_list)]
        schedule_list, fitness = self.get_schedule(None, batch_list, batch_sequence_list, machines)
        fitness_cache[tuple(batch_sequence_list)] = fitness
        return fitness


class GLScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines):
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
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines):
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
