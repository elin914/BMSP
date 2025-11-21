import os
import time
import pandas as pd


class Config:
    def __init__(self):
        self.random_seed = 42

        self.data_instance = {
            'size_type': 'A',  # A, B
            'n_machines': 4,  # 3, 4, 5
            'n_families': 6,  # 3, 6, 12
            'total_n_jobs': 60,  # 60, 180, 300
            'alpha': 0.75,  # 0.25, 0.5, 0.75
            'beta': 0.75  # 0.25, 0.5, 0.75
        }

        # Integrated, Sequential_Sequential, Sequential_Integrated, Integrated_Sequential, Integrated_Integrated
        self.model_type = 'Sequential_Sequential'
        self.integrated_solver = 'CP'
        self.grouping_sequencer = 'OBRKGA'  # EDD, SST, SA, LA, RKGA, BRKGA, OBRKGA, SA, LNS
        self.grouper = 'ABFF'  # BFF, ABFF
        self.integrated_grouper = 'CP'
        self.scheduling_sequencer = 'OBRKGA'  # EDD, LDD, MB, RKGA, BRKGA, OBRKGA, SA, LNS
        self.scheduler = 'BW'  # GL, IBH, BW
        self.integrated_scheduler = 'CP'  # CP, CP2

        self.GAgrouper_parameter = {
            'population_size': 1000,  # jobs * 30
            'generations': 1000,
            'elite_rate': 0.1,
            'mutation_rate': 0.05,
            'mutant_rate': 0.5,
            'tournament_size': 2,
            'crossover_prob': 0.6,
            'early_stop_count': 20
        }
        self.GAsequencer_parameter = {
            'population_size': 1000,  # jobs * 30
            'generations': 1000,
            'elite_rate': 0.1,
            'mutation_rate': 0.05,
            'mutant_rate': 0.5,
            'tournament_size': 2,
            'crossover_prob': 0.6,
            'early_stop_count': 20
        }

        self.cp_search_time_limit = 60
        self.use_starting_point = False

        self.heuristic_grouping_sequencer = ['EDD', 'SST', 'SA', 'LA']
        self.heuristic_scheduling_sequencer = ['LDD', 'EDD', 'MB']
        self.local_grouper = 'ABFF'
        self.local_scheduler = 'BW'

        current_time = time.localtime()
        self.result_folder_path = './results/{0}_{1}h_{2}m_{3}s'.format(time.strftime('%Y%m%d'),
                                                                        str(current_time.tm_hour),
                                                                        str(current_time.tm_min),
                                                                        str(current_time.tm_sec))
        os.makedirs(self.result_folder_path, exist_ok=True)
        self.save_config()

    def save_config(self, name=None):
        config_series = pd.Series(self.__dict__.copy())
        config_df = config_series.to_frame(name='Value')
        save_path = os.path.join(self.result_folder_path, 'configuration.xlsx') if name is None \
            else os.path.join(self.result_folder_path, name + '.xlsx')
        config_df.to_excel(save_path, index=True, header=['Value'])
