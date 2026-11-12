import os
import time
import pandas as pd


class Config:
    def __init__(self):
        self.random_seed = 42
        self.start_date = 31
        self.time_duration = 60

        self.data_instance = {
            'size_type': 'A',  # A, B
            'n_machines': 4,  # 3, 4, 5
            'n_families': 6,  # 3, 6, 12
            'total_n_jobs': 60,  # 60, 180, 300
            'alpha': 0.5,  # 0.25, 0.5, 0.75
            'beta': 0.5  # 0.25, 0.5, 0.75
        }

        # Integrated, Sequential_Sequential, Sequential_Integrated, Integrated_Sequential, Integrated_Integrated
        self.model_type = 'Sequential_Integrated'
        self.integrated_solver = 'CP'
        self.grouping_sequencer = 'OBRKGA'  # EDD, SST, SA, LA, RKGA, BRKGA, OBRKGA, SimA, Tabu
        self.grouper = 'ABFF'  # BFF, ABFF
        self.integrated_grouper = 'CP'
        self.scheduling_sequencer = 'LDD'  # EDD, LDD, MB, RKGA, BRKGA, OBRKGA, SimA, Tabu
        self.scheduler = 'RBW'  # GL, IBH, BW, RBW
        self.integrated_scheduler = 'RCP'  # CP, RCP

        self.GAgrouper_parameter = {
            'population_size': 1000,  # jobs * 30
            'generations': 1000,
            'elite_rate': 0.15,
            'mutation_rate': 0.05,
            'mutant_rate': 0.3,
            'tournament_size': 2,
            'crossover_prob': 0.6,
            'early_stop_count': 20
        }
        self.GAsequencer_parameter = {
            'population_size': 1000,  # jobs * 30
            'generations': 1000,
            'elite_rate': 0.15,
            'mutation_rate': 0.05,
            'mutant_rate': 0.3,
            'tournament_size': 2,
            'crossover_prob': 0.6,
            'early_stop_count': 30
        }

        self.cp_search_time_limit = 300
        self.cp_log = False  # True면 CP Optimizer 탐색 로그를 화면에 출력
        self.use_starting_point = False  # 휴리스틱 해를 CP 초기해로 사용
        # CP 스케줄러(CPIntegratedScheduler) 모델 표현. 같은 문제를 다르게 표현한 것이라 최적해는 같고, 시간 제한 안의 결과만 다름
        #   cp_objective: 'abs' (납기마다 abs 항, 예전 방식) / 'end_eval' (배치별 구간 선형 비용 함수)
        #     -> 10초 비교(13개 인스턴스)에서 end_eval이 평균 1% 좋고 job 120~300개에서 최대 7% 좋았음
        #   cp_distinct_start: 'all_diff' (예전 방식) / 'no_overlap'
        #     -> no_overlap은 이점이 없었고, 보조 변수 때문에 Community Edition 한계를 job 300개에서 초과함
        self.cp_objective = 'abs'
        self.cp_distinct_start = 'all_diff'

        self.heuristic_grouping_sequencer = ['EDD', 'SST', 'SA', 'LA']
        self.heuristic_scheduling_sequencer = ['LDD', 'EDD', 'MB']
        self.local_grouper = 'ABFF'
        self.local_scheduler = 'BW'

        current_time = time.localtime()
        self.result_folder_path = './results/{0}_{1}h_{2}m_{3}s'.format(time.strftime('%Y%m%d'),
                                                                        str(current_time.tm_hour),
                                                                        str(current_time.tm_min),
                                                                        str(current_time.tm_sec))
        # self.save_config()

    def save_config(self, name=None):
        os.makedirs(self.result_folder_path, exist_ok=True)
        config_series = pd.Series(self.__dict__.copy())
        config_df = config_series.to_frame(name='Value')
        save_path = os.path.join(self.result_folder_path, 'configuration.xlsx') if name is None \
            else os.path.join(self.result_folder_path, name + '.xlsx')
        config_df.to_excel(save_path, index=True, header=['Value'])
