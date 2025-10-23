from typing import List
from model.data import Job, PlacedJob, Batch


class BaseGrouper:
    def create_batch_list(self, job_list: List[Job], job_sequence_list: List[int], machines) -> List[Batch]:
        raise NotImplementedError


class EMS:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class BFFPacker(BaseGrouper):
    def create_batch_list(self, job_list: List[Job], job_sequence_list: List[int], machines) -> List[Batch]:
        batch_list = list()
        first_batch = Batch(machines.width, machines.height)
        first_batch.ems_list.append(EMS(0, 0, machines.width, machines.height))
        batch_list.append(first_batch)

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
                new_batch = Batch(machines.width, machines.height)
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
                        batch.ems_list.sort(key=lambda e: e.width * e.height)

        for batch in batch_list:
            batch.update_by_placed_job_list()
        return batch_list

    @staticmethod
    def find_best_fit_in_batch_list(job, batch_list):
        for i, batch in enumerate(batch_list):
            if batch.family is not None and batch.family != job.family:
                continue
            for j, ems in enumerate(sorted(batch.ems_list, key=lambda k: k.width * k.height)):
                fit_normal = (ems.width >= job.width and ems.height >= job.height)
                fit_rotated = (ems.width >= job.height and ems.height >= job.width)

                if fit_normal and not fit_rotated:
                    return {'batch_idx': i, 'ems_idx': j, 'rotation': False, 'width': job.width, 'height': job.height}
                if not fit_normal and fit_rotated:
                    return {'batch_idx': i, 'ems_idx': j, 'rotation': True, 'width': job.height, 'height': job.width}
                if fit_normal and fit_rotated:
                    metric_normal = min(ems.width - job.width, ems.height - job.height)
                    metric_rotated = min(ems.width - job.height, ems.height - job.width)
                    if metric_rotated >= metric_normal:
                        return {'batch_idx': i, 'ems_idx': j, 'rotation': False,
                                'width': job.width, 'height': job.height}
                    else:
                        return {'batch_idx': i, 'ems_idx': j, 'rotation': True,
                                'width': job.height, 'height': job.width}
        return None

    @staticmethod
    def place_job_and_update_ems(job, batch, min_area, best_fit_info):
        ems_to_place_in = batch.ems_list[best_fit_info['ems_idx']]
        job_x, job_y = ems_to_place_in.x, ems_to_place_in.y
        job_w, job_h = best_fit_info['width'], best_fit_info['height']

        batch.placed_job_list.append(
            PlacedJob(job, best_fit_info['rotation'], job_x, job_y, job_w, job_h)
        )
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
        for ems1 in newly_generated_ems:
            is_maximal = True
            for ems2 in newly_generated_ems:
                if ems1 is ems2:
                    continue
                if (ems2.x <= ems1.x and ems2.y <= ems1.y and
                        ems2.x + ems2.width >= ems1.x + ems1.width and
                        ems2.y + ems2.height >= ems1.y + ems1.height):
                    is_maximal = False
                    break
            if is_maximal and ems1.width * ems1.height > min_area:
                final_ems_list.append(ems1)

        batch.ems_list = final_ems_list
        batch.ems_list.sort(key=lambda e: e.width * e.height)


class AdujustedBFFPacker(BFFPacker):
    @staticmethod
    def find_best_fit_in_batch_list(job, batch_list):
        best_fit_info = None
        min_primary_metric = float('inf')
        min_secondary_metric = float('inf')
        for i, batch in enumerate(batch_list):
            if batch.family is not None and batch.family != job.family:
                continue
            for j, ems in enumerate(sorted(batch.ems_list, key=lambda k: k.width * k.height)):
                for rotation in [False, True]:
                    job_w = job.width if not rotation else job.height
                    job_h = job.height if not rotation else job.width
                    if ems.width >= job_w and ems.height >= job_h:
                        primary_metric = (ems.width - job_w) + (ems.height - job_h)
                        secondary_metric = min(ems.width - job_w, ems.height - job_h)
                        if min_primary_metric > primary_metric:
                            min_primary_metric = primary_metric
                            min_secondary_metric = secondary_metric
                            best_fit_info = {'batch_idx': i, 'ems_idx': j, 'rotation': rotation,
                                             'width': job_w, 'height': job_h}
                        elif min_primary_metric == primary_metric and min_secondary_metric > secondary_metric:
                            min_secondary_metric = secondary_metric
                            best_fit_info = {'batch_idx': i, 'ems_idx': j, 'rotation': rotation,
                                             'width': job_w, 'height': job_h}
        return best_fit_info
