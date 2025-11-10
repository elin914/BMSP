import os
import time
import pandas as pd


class Config:
    def __init__(self):
        self.random_seed = 42

        self.data_instance = {
            'size_type': 'A',  # A, B
            'n_machines': 5,  # 3, 4, 5
            'n_families': 3,  # 3, 6, 12
            'total_n_jobs': 60,  # 60, 180, 300
            'alpha': 0.5,  # 0.25, 0.5, 0.75
            'beta': 0.5  # 0.25, 0.5, 0.75
        }

        # Integrated, Sequential_Sequential, Sequential_Integrated, Integrated_Sequential, Integrated_Integrated
        self.model_type = 'Sequential_Sequential'
        self.integrated_solver = 'CP'
        self.grouping_sequencer = 'OBRKGA'  # EDD, SST, SA, LA, RKGA, BRKGA, OBRKGA, SA, LNS
        self.grouper = 'ABFF'  # BFF, ABFF
        self.integrated_grouper = 'CP'
        self.scheduling_sequencer = 'OBRKGA'  # EDD, MB, RKGA, BRKGA, OBRKGA, SA, LNS
        self.scheduler = 'IBH'  # GL, IBH
        self.integrated_scheduler = 'CP'  # CP, CP2

        self.GAgrouper_parameter = {
            'population_size': 100,  # jobs * 30
            'generations': 100,
            'elite_rate': 0.1,
            'mutation_rate': 0.05,
            'mutant_rate': 0.15,
            'tournament_size': 4,
            'crossover_prob': 0.7
        }
        self.GAsequencer_parameter = {
            'population_size': 300,  # jobs * 30
            'generations': 100,
            'elite_rate': 0.1,
            'mutation_rate': 0.05,
            'mutant_rate': 0.15,
            'tournament_size': 4,
            'crossover_prob': 0.7
        }

        current_time = time.localtime()
        self.result_folder_path = '../results/{0}_{1}h_{2}m_{3}s'.format(time.strftime('%Y%m%d'),
                                                                         str(current_time.tm_hour),
                                                                         str(current_time.tm_min),
                                                                         str(current_time.tm_sec))
        if not os.path.exists(self.result_folder_path):
            os.mkdir(self.result_folder_path)
        self.save_config()

    def save_config(self, name=None):
        config_series = pd.Series(self.__dict__.copy())
        config_df = config_series.to_frame(name='Value')
        save_path = self.result_folder_path + '/configuration.xlsx' if name is None \
            else self.result_folder_path + '/' + name + '.xlsx'
        config_df.to_excel(save_path, index=True, header=['Value'])
