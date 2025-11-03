import numpy as np


class Job:
    def __init__(self, idx, family, width, height, p_time, release_date, due_date):
        self.idx = idx
        self.family = family
        self.width = width
        self.height = height
        self.p_time = p_time
        self.release_date = release_date
        self.due_date = due_date


class Machine:
    def __init__(self, n_machine, width, height):
        self.n_machine = n_machine
        self.width = width
        self.height = height


class PlacedJob:
    def __init__(self, job, rotation, x, y):
        self.job = job
        self.rotation = rotation
        self.x = x
        self.y = y
        self.width = job.width
        self.height = job.height
        self.p_time = job.p_time
        self.release_date = job.release_date
        self.due_date = job.due_date


class Batch:
    def __init__(self, idx, width, height):
        self.idx = idx
        self.width = width
        self.height = height
        self.family = None
        self.placed_job_list = list()
        self.ems_list = list()
        self.processing_time = None
        self.max_release_date = None
        self.due_date_list = list()

    def update_by_placed_job_list(self):
        self.processing_time = self.placed_job_list[0].job.p_time
        self.max_release_date = max([placedjob.release_date for placedjob in self.placed_job_list])
        self.due_date_list = [placedjob.due_date for placedjob in self.placed_job_list]


class Data:
    def __init__(self):
        self.job_list = None
        self.machines = None

    def make_data(self, cfg):
        bin_size = 10 if cfg.data_instance['size_type'] == 'A' else 100
        self.machines = Machine(cfg.data_instance['n_machines'], bin_size, bin_size)

        job_per_family = int(cfg.data_instance['total_n_jobs'] / cfg.data_instance['n_families'])
        p_time_per_family_list = (
            np.random.choice([2, 4, 10, 16, 20], size=cfg.data_instance['n_families'], p=[0.2, 0.2, 0.3, 0.2, 0.1]))
        family_id_list = np.repeat(np.arange(cfg.data_instance['n_families']), job_per_family)
        p_time_list = np.repeat(p_time_per_family_list, job_per_family)
        if cfg.data_instance['size_type'] == 'A':
            width_list = np.random.randint(1, 11, size=cfg.data_instance['total_n_jobs'])
            height_list = np.random.randint(1, 11, size=cfg.data_instance['total_n_jobs'])
        else:
            width_list = np.random.randint(20, 81, size=cfg.data_instance['total_n_jobs'])
            height_list = np.random.randint(20, 81, size=cfg.data_instance['total_n_jobs'])
        area_list = width_list * height_list
        temp = (np.sum(p_time_list) * np.average(area_list) /
                # temp = (np.average(p_time_list * area_list) /
                # temp = (np.sum(p_time_family_list) * np.average(area_list) /
                (cfg.data_instance['n_machines'] * bin_size * bin_size))
        release_date_list =\
            np.random.randint(0, max(1, int(cfg.data_instance['alpha'] * temp)) + 1,
                              size=cfg.data_instance['total_n_jobs'])
        due_date_list = (
                np.random.randint(0, max(1, int(cfg.data_instance['alpha'] * temp)) + 1,
                                  size=cfg.data_instance['total_n_jobs'])
                + release_date_list + p_time_list)
        self.job_list = [Job(i, int(family_id_list[i]), int(width_list[i]), int(height_list[i]),
                             int(p_time_list[i]), int(release_date_list[i]), int(due_date_list[i]))
                         for i in range(cfg.data_instance['total_n_jobs'])]
