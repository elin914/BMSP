import pandas as pd
import numpy as np


class Job:
    def __init__(self, width, height, s_time, p_time, release_date, due_date):
        self.width = width
        self.height = height
        self.s_time = s_time
        self.p_time = p_time
        self.release_date = release_date
        self.due_date = due_date


class Machine:
    def __init__(self, n_machine, width, height):
        self.n_machine = n_machine
        self.width = width
        self.height = height


class Data:
    def __init__(self):
        self.job_dict = dict()
        self.machine = None

    def get_data(self, config):
        if config.data_type.startswith('cgcut'):
            sheet_name = 'cgcut'
            header_row_index = 7
            job_data_start_row_index = 12
            machine_data_start_row_index = 79
        elif config.data_type.startswith('gcut'):
            sheet_name = 'gcut'
            header_row_index = 9
            job_data_start_row_index = 15
            machine_data_start_row_index = 69
        elif config.data_type.startswith('ngcut'):
            sheet_name = 'ngcut'
            header_row_index = 9
            job_data_start_row_index = 15
            machine_data_start_row_index = 41
        else:
            print(f"지원하지 않는 데이터 타입입니다: {config.data_type}")
            return


        df = pd.read_excel(config.data_file_path, sheet_name=sheet_name, header=None)
        header_row = df.iloc[header_row_index].astype(str).values
        target_col_index = -1
        for i, col_name in enumerate(header_row):
            if config.data_type in col_name:
                target_col_index = i
                break
        if target_col_index == -1:
            print(f"파일 '{config.data_file_path}'의 '{sheet_name}' 시트 8번째 행에서 '{config.data_type}'을 찾을 수 없습니다.")
            return
        number_of_items = df.iloc[header_row_index + 2, target_col_index + 2]
        job_data = df.iloc[job_data_start_row_index:job_data_start_row_index + number_of_items,
                   target_col_index:target_col_index + 3]
        job_data.columns = ['number', 'width', 'height']
        job_data = job_data.dropna().astype(float).astype(int)
        for _, row in job_data.iterrows():
            self.job_dict[row['number']] = Job(width=row['width'],
                                               height=row['height'],
                                               s_time=np.random.randint(1, 11),
                                               p_time=np.random.randint(1, 11),
                                               release_date=np.random.randint(10, 100),
                                               due_date=np.random.randint(10, 100))

        self.machine = Machine(*list(df.iloc[machine_data_start_row_index, target_col_index:target_col_index + 3]))
