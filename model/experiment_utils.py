import csv
import os
import traceback
from datetime import datetime


class ResultLogger:
    """실험 결과 CSV 기록기.

    헤더와 행을 같은 정의(id_cols, model_names, fields)로 만들기 때문에
    모델 목록이나 측정 항목을 바꿔도 열이 밀리지 않는다.
    - 헤더: id_cols + [f'{model}_{field}' ...] + ['failed']
    - 실패/미완료 칸은 0이 아니라 빈 칸('')으로 남기고, 'failed' 열에 모델 이름을 적는다.
      (0은 정상 fitness 값과 구분이 안 되기 때문)
    - 에러 traceback은 CSV와 같은 이름의 .log 파일에 기록한다.
    """

    def __init__(self, save_dir, exp_name, id_cols, fields, model_names=None):
        os.makedirs(save_dir, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_path = os.path.join(save_dir, f'{exp_name}_{stamp}.csv')
        self.log_path = os.path.splitext(self.csv_path)[0] + '.log'
        self.id_cols = list(id_cols)
        self.fields = list(fields)
        self.model_names = list(model_names) if model_names else [None]

        self.headers = self.id_cols + [self._col(m, f) for m in self.model_names for f in self.fields] + ['failed']
        with open(self.csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(self.headers)
        print(f"\n[*] 실험 시작! 결과는 '{os.path.abspath(self.csv_path)}'에 실시간으로 저장됩니다.\n")

    @staticmethod
    def _col(model_name, field):
        return field if model_name is None else f'{model_name}_{field}'

    def log_error(self, context):
        """except 블록 안에서 호출. 화면에는 요약, .log 파일에는 전체 traceback."""
        print(f"\n   !!! [Error] {context} (자세한 내용: {self.log_path})")
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {context}\n{traceback.format_exc()}\n")

    def write_row(self, id_values, model_results):
        """model_results: {model_name: [field 값들]} (model_names가 None이면 {None: [...]})
        값이 fields보다 적으면(중간에 실패) 나머지를 빈 칸으로 채우고 failed에 표시한다."""
        if len(id_values) != len(self.id_cols):
            raise ValueError(f"id 값 {len(id_values)}개, id 열 {len(self.id_cols)}개로 개수가 다릅니다.")
        row = list(id_values)
        failed = list()
        for m in self.model_names:
            values = list(model_results.get(m, []))
            if len(values) > len(self.fields):
                raise ValueError(f"{m}: 값 {len(values)}개가 fields {len(self.fields)}개보다 많습니다.")
            if len(values) < len(self.fields):
                failed.append(m or 'run')
                values += [''] * (len(self.fields) - len(values))
            row.extend(values)
        row.append(';'.join(failed))
        with open(self.csv_path, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(row)
