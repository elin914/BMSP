from typing import List
from data import Job, PlacedJob, Batch


class BaseGrouper:
    def create_batch_list(self, cfg, job_list: List[Job], job_sequence_list: List[int], machines) -> List[Batch]:
        raise NotImplementedError

    # @staticmethod
    # def get_obj(batch_list):
    #     delay_obj = 0
    #     for batch in batch_list:
    #         batch_delay = 0
    #         current_sum = 0
    #         for i, date in enumerate(sorted(batch.due_date_list)):
    #         # for i, date in enumerate(sorted([placed_job.release_date for placed_job in batch.placed_job_list])):
    #             batch_delay += i * date - current_sum
    #             current_sum += date
    #         delay_obj += batch_delay
    #     return delay_obj

    # @staticmethod
    # def get_obj(batch_list):
    #     delay_obj = 0
    #     for batch in batch_list:
    #         d_dates = sorted(batch.due_date_list)
    #         r_dates = sorted([job.release_date for job in batch.placed_job_list])
    #         current_sum_d = 0
    #         current_sum_r = 0
    #         for i, (d_date, r_date) in enumerate(zip(d_dates, r_dates)):
    #             delay_obj += (i * d_date - current_sum_d)
    #             current_sum_d += d_date
    #             delay_obj += (i * r_date - current_sum_r)
    #             current_sum_r += r_date
    #     return delay_obj

    def calculate_fitness(self, cfg, job_sequence_list, job_list, machines, fitness_cache):
        if tuple(job_sequence_list) in fitness_cache:
            return fitness_cache[tuple(job_sequence_list)]
        batch_list, fitness = self.create_batch_list(cfg, job_list, job_sequence_list, machines)
        fitness_cache[tuple(job_sequence_list)] = len(batch_list) * 10000 + fitness
        return len(batch_list) * 10000 + fitness


def due_date_distance(batch, job):
    """배치 평균 납기와 job 납기의 차이 (job을 넣어볼 배치 순서의 기준, 빈 배치는 맨 뒤).
    예전 np.average는 짧은 리스트에서 매우 느려서(평가 시간의 약 75%) batch.mean_due_date(파이썬 sum/len)를 씀.
    정수 납기의 합은 float64에서 정확하므로 np.average와 값이 완전히 같다."""
    if not batch.due_date_list:
        return float('inf')
    return abs(batch.mean_due_date - job.due_date)


class EMS:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class BFFPacker(BaseGrouper):
    def create_batch_list(self, cfg, job_list: List[Job], job_sequence_list: List[int], machines) -> List[Batch]:
        batch_list = list()
        min_area_dict_by_family = dict()
        job_list_by_family = dict()
        for job in job_list:
            if job.family not in min_area_dict_by_family:
                min_area_dict_by_family[job.family] = job.width * job.height
                job_list_by_family[job.family] = [job]
            else:
                if job.width * job.height < min_area_dict_by_family[job.family]:
                    min_area_dict_by_family[job.family] = job.width * job.height
                job_list_by_family[job.family].append(job)

        for job_id in job_sequence_list:
            job = job_list[job_id]
            best_fit_info = self.find_best_fit_in_batch_list(job, batch_list)
            if best_fit_info is None:
                new_batch = Batch(len(batch_list), machines.width, machines.height)
                new_batch.ems_list.append(EMS(0, 0, machines.width, machines.height))
                batch_list.append(new_batch)
                best_fit_info = {'batch_idx': len(batch_list) - 1, 'ems_idx': 0, 'rotation': False,
                                 'width': job.width, 'height': job.height}
            self.place_job_and_update_ems(job, batch_list[best_fit_info['batch_idx']],
                                          min_area_dict_by_family[job.family], best_fit_info)
            job_list_by_family[job.family].remove(job)
            if job.width * job.height == min_area_dict_by_family[job.family]:
                if job_list_by_family[job.family]:
                    min_area_dict_by_family[job.family] = min(temp.width * temp.height
                                                              for temp in job_list_by_family[job.family])
                else:
                    min_area_dict_by_family[job.family] = float('inf')
                for batch in batch_list:
                    if batch.family == job.family:
                        batch.ems_list = [ems for ems in batch.ems_list
                                          if ems.width * ems.height >= min_area_dict_by_family[job.family]]
                        batch.ems_list.sort(key=lambda item: item.width * item.height)

        # return batch_list, self.get_obj(batch_list)
        for batch in batch_list:
            batch.update_by_placed_job_list()
        batch_sequence_list = cfg.heuristic_scheduling_sequencer[0].get_sequence_list(cfg, batch_list, machines)
        return batch_list, cfg.local_scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)[1]

    @staticmethod
    def find_best_fit_in_batch_list(job, batch_list):
        for _, batch in enumerate(sorted(batch_list, key=lambda item: due_date_distance(item, job))):
            if batch.family is not None and batch.family != job.family:
                continue
            for j, ems in enumerate(sorted(batch.ems_list, key=lambda item: item.width * item.height)):
                fit_normal = (ems.width >= job.width and ems.height >= job.height)
                fit_rotated = (ems.width >= job.height and ems.height >= job.width)

                if fit_normal and not fit_rotated:
                    return {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': False,
                            'width': job.width, 'height': job.height}
                if not fit_normal and fit_rotated:
                    return {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': True,
                            'width': job.height, 'height': job.width}
                if fit_normal and fit_rotated:
                    metric_normal = min(ems.width - job.width, ems.height - job.height)
                    metric_rotated = min(ems.width - job.height, ems.height - job.width)
                    if metric_rotated >= metric_normal:
                        return {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': False,
                                'width': job.width, 'height': job.height}
                    else:
                        return {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': True,
                                'width': job.height, 'height': job.width}
        return None

    @staticmethod
    def place_job_and_update_ems(job, batch, min_area, best_fit_info):
        ems_to_place_in = batch.ems_list[best_fit_info['ems_idx']]
        job_x, job_y = ems_to_place_in.x, ems_to_place_in.y
        job_w, job_h = best_fit_info['width'], best_fit_info['height']

        batch.placed_job_list.append(PlacedJob(job, best_fit_info['rotation'], job_x, job_y))
        batch.family = job.family

        newly_generated_ems = []
        for ems in batch.ems_list:
            is_overlapping = (job_x < ems.x + ems.width and job_x + job_w > ems.x and
                              job_y < ems.y + ems.height and job_y + job_h > ems.y)

            if not is_overlapping:
                newly_generated_ems.append(ems)
                continue

            if job_x > ems.x:
                newly_generated_ems.append(EMS(ems.x, ems.y, job_x - ems.x, ems.height))
            if job_x + job_w < ems.x + ems.width:
                newly_generated_ems.append(EMS(job_x + job_w, ems.y, (ems.x + ems.width) - (job_x + job_w), ems.height))
            if job_y > ems.y:
                newly_generated_ems.append(EMS(ems.x, ems.y, ems.width, job_y - ems.y))
            if job_y + job_h < ems.y + ems.height:
                newly_generated_ems.append(EMS(ems.x, job_y + job_h, ems.width, (ems.y + ems.height) - (job_y + job_h)))

        final_ems_list = []
        for i, ems1 in enumerate(newly_generated_ems):
            is_maximal = True
            for j, ems2 in enumerate(newly_generated_ems):
                if i == j:
                    continue
                if (ems2.x <= ems1.x and ems2.y <= ems1.y and
                        ems2.x + ems2.width >= ems1.x + ems1.width and
                        ems2.y + ems2.height >= ems1.y + ems1.height):
                    is_identical = (ems2.x == ems1.x and ems2.y == ems1.y and
                                    ems2.width == ems1.width and ems2.height == ems1.height)
                    # 똑같은 EMS가 여러 개면 서로를 포함한다고 판단해 둘 다 지워지므로, 하나(앞의 것)는 남김
                    if is_identical and j > i:
                        continue
                    is_maximal = False
                    break
            # 남은 job 중 가장 작은 면적과 같은 EMS도 쓸 수 있으므로 >= (아래 family 갱신 부분과 동일 기준)
            if is_maximal and ems1.width * ems1.height >= min_area:
                final_ems_list.append(ems1)

        batch.ems_list = final_ems_list
        batch.ems_list.sort(key=lambda item: item.width * item.height)
        batch.update_by_placed_job_list()


class AdjustedBFFPacker(BFFPacker):
    @staticmethod
    def find_best_fit_in_batch_list(job, batch_list):
        min_primary_metric = float('inf')
        min_secondary_metric = float('inf')
        best_fit_info = None
        for i, batch in enumerate(sorted(batch_list, key=lambda item: due_date_distance(item, job))):
            if batch.family is not None and batch.family != job.family:
                continue
            for j, ems in enumerate(sorted(batch.ems_list, key=lambda item: item.width * item.height)):
                for rotation in [False, True]:
                    job_w = job.width if not rotation else job.height
                    job_h = job.height if not rotation else job.width
                    if ems.width >= job_w and ems.height >= job_h:
                        primary_metric = (ems.width - job_w) + (ems.height - job_h)
                        secondary_metric = min(ems.width - job_w, ems.height - job_h)
                        if min_primary_metric > primary_metric:
                            min_primary_metric = primary_metric
                            min_secondary_metric = secondary_metric
                            best_fit_info = {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': rotation,
                                             'width': job_w, 'height': job_h}
                        elif min_primary_metric == primary_metric and min_secondary_metric > secondary_metric:
                            min_secondary_metric = secondary_metric
                            best_fit_info = {'batch_idx': batch.idx, 'ems_idx': j, 'rotation': rotation,
                                             'width': job_w, 'height': job_h}
            if best_fit_info is not None:
                return best_fit_info
        return best_fit_info
