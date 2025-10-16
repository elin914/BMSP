import numpy as np


class Job:
    def __init__(self, number, family, width, height, p_time):
        self.number = number
        self.family = family
        self.width = width
        self.height = height
        self.p_time = p_time
        self.release_date = None
        self.due_date = None


class Machine:
    def __init__(self, n_machine, width, height):
        self.n_machine = n_machine
        self.width = width
        self.height = height


class Data:
    def __init__(self):
        self.job_dict = dict()
        self.machine = None

    def make_data(self, config):
        setting = config.data_instance
        bin_size = 10 if setting['size_type'] == 'A' else 100
        self.machine = Machine(setting['n_machines'], bin_size, bin_size)

        job_per_family = int(setting['total_n_jobs'] / setting['n_families'])
        for i in range(setting['n_families']):
            p_time_list = []
            for j in range(job_per_family):
                width = np.random.randint(1, 11) if setting['size_type'] == 'A'\
                    else np.random.randint(20, 81)
                height = np.random.randint(1, 11) if setting['size_type'] == 'A'\
                    else np.random.randint(20, 81)
                p_time = int(np.random.choice([2, 4, 10, 16, 20], p=[0.2, 0.2, 0.3, 0.2, 0.1]))
                p_time_list.append(p_time * width * height)
                self.job_dict[i * job_per_family + j] =\
                    Job(i * job_per_family + j, i, width, height, p_time)
            temp_max_time = np.sum(p_time_list) / (setting['n_machines'] * bin_size * bin_size)
            for j in range(job_per_family):
                release_date = np.random.randint(1, max(1, int(setting['alpha'] * temp_max_time)) + 1)
                due_date = (release_date + self.job_dict[i * job_per_family + j].p_time
                            + np.random.randint(1, max(1, int(setting['beta'] * temp_max_time)) + 1))
                self.job_dict[i * job_per_family + j].release_date = release_date
                self.job_dict[i * job_per_family + j].due_date = due_date
