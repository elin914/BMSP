import numpy as np
import pandas as pd
from datetime import timedelta


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
        self.unavailable_list = list()

    def add_unavailable(self, unavailable_start, unavailable_end):
        self.unavailable_list.extend(range(unavailable_start, unavailable_end + 1))


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
        self.med_due_date = None
        self.start_time = None
        self.end_time = None
        self.delay_time = None

    def update_by_placed_job_list(self):
        self.processing_time = self.placed_job_list[0].job.p_time
        self.max_release_date = max([placedjob.release_date for placedjob in self.placed_job_list])
        self.due_date_list = [placedjob.due_date for placedjob in self.placed_job_list]
        self.med_due_date = int(np.median(self.due_date_list)) if len(self.due_date_list) % 2\
            else sorted(self.due_date_list)[len(self.due_date_list) // 2]


def create_job_list(df_real, lead_time_margin):
    # 원본 보존 및 중복 제거
    df_real = df_real.copy()
    df_real = df_real.drop_duplicates(subset=['키값'], keep='first')

    # 키값 파싱
    df_real['prefix'] = df_real['키값'].apply(lambda x: x[:-1])
    df_real['suffix'] = df_real['키값'].apply(lambda x: x[-1])

    # -----------------------------------------------------
    # 기준일 계산
    # -----------------------------------------------------
    min_due_date_global = df_real['소요일'].min()

    if pd.api.types.is_datetime64_any_dtype(df_real['소요일']):
        if isinstance(lead_time_margin, int):
            margin_delta = timedelta(days=lead_time_margin)
        else:
            margin_delta = lead_time_margin
    else:
        margin_delta = lead_time_margin

    base_date = min_due_date_global - margin_delta

    # 매핑 정보
    manu_map = {'S': 0, 'HZ': 1, 'C': 2, 'HK': 3}
    # manu_map = {'HK': 0, 'HZ': 1, 'S': 2, 'C': 3}

    def get_ptime(maker):
        if maker == 'S':
            return 8
        elif maker in ['HZ', 'C']:
            return 10
        elif maker == 'HK':
            return 12
        return 10

    job_list = []
    job_id_counter = 0
    total_time_gap = 0

    # -----------------------------------------------------
    # [변경] 그룹핑 기준: 하역일 -> 품목항차
    # -----------------------------------------------------
    # 데이터에 '품목항차' 컬럼이 반드시 있어야 합니다.
    grouped = df_real.groupby(['품목항차', '제작처', '품목구분'])

    for (voyage, manufacturer, item_category), group in grouped:

        family_id = manu_map.get(manufacturer, 0)
        p_time = get_ptime(manufacturer)

        # [중요] 그룹 내 대표 하역일 추출
        # (같은 항차면 하역일이 같다고 가정하고 첫 번째 행의 값을 사용)
        unloading_date = group['하역일'].iloc[0]

        # -------------------------------------------------
        # 내부 함수
        # -------------------------------------------------
        def add_job(width, height, due_date_obj):
            nonlocal job_id_counter, total_time_gap

            # 1. 치수 10배 및 정수화
            scaled_width = int(width * 10)
            scaled_height = int(height * 10)

            # 2. 날짜 정규화
            delta_due = due_date_obj - base_date
            delta_release = (due_date_obj - margin_delta) - base_date

            rel_due_date = delta_due.days if hasattr(delta_due, 'days') else delta_due
            rel_release_date = delta_release.days if hasattr(delta_release, 'days') else delta_release

            # 3. Job 생성
            new_job = Job(
                idx=job_id_counter,
                family=family_id,
                width=scaled_width,
                height=scaled_height,
                p_time=p_time,
                release_date=rel_release_date,
                due_date=rel_due_date
            )
            job_list.append(new_job)

            job_id_counter += 1

            # 4. Metric 계산 (대표 하역일 unloading_date 사용)
            gap = abs(due_date_obj - unloading_date)
            gap_val = gap.days if hasattr(gap, 'days') else gap
            total_time_gap += gap_val

        # -------------------------------------------------
        # 로직 (이전과 동일)
        # -------------------------------------------------
        if item_category == 'B_AA':
            for _, row in group.iterrows():
                add_job(row['BTH'], row['LTH'], row['소요일'])

        elif item_category == 'B_CC':
            pairs_1 = group[group['suffix'] == '1'].set_index('prefix')
            pairs_2 = group[group['suffix'] == '2'].set_index('prefix')
            common_prefixes = pairs_1.index.intersection(pairs_2.index)

            for prefix in common_prefixes:
                b1 = pairs_1.loc[prefix]
                if isinstance(b1, pd.DataFrame): b1 = b1.iloc[0]
                b2 = pairs_2.loc[prefix]
                if isinstance(b2, pd.DataFrame): b2 = b2.iloc[0]

                merged_due = min(b1['소요일'], b2['소요일'])
                add_job(max(b1['BTH'], b2['BTH']), max(b1['LTH'], b2['LTH']), merged_due)

            processed_keys = set([p + '1' for p in common_prefixes] + [p + '2' for p in common_prefixes])
            leftovers = group[~group['키값'].isin(processed_keys)]
            for _, row in leftovers.iterrows():
                add_job(row['BTH'], row['LTH'], row['소요일'])

        elif item_category == 'B_BB':
            stacks = []

            pairs_1 = group[group['suffix'] == '1'].set_index('prefix')
            pairs_2 = group[group['suffix'] == '2'].set_index('prefix')
            common_prefixes = pairs_1.index.intersection(pairs_2.index)

            for prefix in common_prefixes:
                b1 = pairs_1.loc[prefix]
                if isinstance(b1, pd.DataFrame): b1 = b1.iloc[0]
                b2 = pairs_2.loc[prefix]
                if isinstance(b2, pd.DataFrame): b2 = b2.iloc[0]

                stacks.append({
                    'width': max(b1['BTH'], b2['BTH']),
                    'height': max(b1['LTH'], b2['LTH']),
                    'due_date': min(b1['소요일'], b2['소요일']),
                    'level': 2
                })

            singles = group[group['suffix'] == '3'].to_dict('records')

            for stack in stacks:
                while stack['level'] < 4 and singles:
                    s_block = singles.pop(0)
                    stack['width'] = max(stack['width'], s_block['BTH'])
                    stack['height'] = max(stack['height'], s_block['LTH'])
                    stack['due_date'] = min(stack['due_date'], s_block['소요일'])
                    stack['level'] += 1

            while singles:
                chunk = singles[:4]
                singles = singles[4:]
                if not chunk: break

                stacks.append({
                    'width': max(c['BTH'] for c in chunk),
                    'height': max(c['LTH'] for c in chunk),
                    'due_date': min(c['소요일'] for c in chunk),
                    'level': len(chunk)
                })

            processed_keys = set([p + '1' for p in common_prefixes] + [p + '2' for p in common_prefixes])
            orphans = group[(group['suffix'].isin(['1', '2'])) & (~group['키값'].isin(processed_keys))]
            for _, row in orphans.iterrows():
                add_job(row['BTH'], row['LTH'], row['소요일'])

            for stack in stacks:
                add_job(stack['width'], stack['height'], stack['due_date'])

    return job_list, total_time_gap, base_date


class Family:
    def __init__(self):
        self.hard_unavailable = [] # df_1 유래: 아예 작업 불가 (D-30 ~ D-day)
        self.holidays = []         # df_2 유래: 휴일/지연 (WorkingDay=0 or 악기상=1)

    def add_hard_unavailable(self, date_list):
        # 중복 제거 및 기존 리스트와 병합
        self.hard_unavailable = sorted(list(set(self.hard_unavailable + date_list)))

    def add_holiday(self, date):
        if date not in self.holidays:
            self.holidays.append(date)
            self.holidays.sort() # 삽입 시 정렬 유지


class Data:
    def __init__(self):
        self.job_list = None
        self.machines = None
        self.family_dict = None

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
        temp = (np.sum(p_time_list) * np.average(area_list) / (cfg.data_instance['n_machines'] * bin_size * bin_size))
        release_date_list =\
            np.random.randint(0, max(1, int(cfg.data_instance['alpha'] * temp)) + 1,
                              size=cfg.data_instance['total_n_jobs'])
        due_date_list = (
                np.random.randint(0, max(1, int(cfg.data_instance['beta'] * temp)) + 1,
                                  size=cfg.data_instance['total_n_jobs'])
                + release_date_list + p_time_list)
        self.job_list = [Job(i, int(family_id_list[i]), int(width_list[i]), int(height_list[i]),
                             int(p_time_list[i]), int(release_date_list[i]), int(due_date_list[i]))
                         for i in range(cfg.data_instance['total_n_jobs'])]

    def load_data(self, cfg):
        self.machines = Machine(10, 290, 94)
        file_path = './data/data.xlsx'
        file_path2 = './data/data2.xlsx'

        df_real = pd.read_excel(file_path2, sheet_name='Sheet3')
        t_time = 41275
        mask = df_real['LTH'] < df_real['BTH']
        df_real.loc[mask, ['LTH', 'BTH']] = df_real.loc[mask, ['BTH', 'LTH']].values
        df_data = df_real[(df_real['LTH'] <= 29) & (df_real['BTH'] <= 9.4)]
        df_slice = df_data[(df_data['소요일'] >= t_time + cfg.start_date) & (df_data['소요일'] <= t_time + cfg.start_date + cfg.time_duration)].reset_index()
        cfg.fitness1 = len(set(df_slice['품목항차']))
        self.job_list, cfg.fitness2, base_date = create_job_list(df_slice, 30)
        cfg.n_of_job = len(self.job_list)
        cfg.save_config()
        m_unavilable_start = 41439
        m_unavilable_end = 41470
        if base_date <= m_unavilable_end:
            self.machines.add_unavailable(max(m_unavilable_start-base_date, 0), m_unavilable_end - base_date)

        df1 = pd.read_excel(file_path, sheet_name='Sheet1')
        df2 = pd.read_excel(file_path, sheet_name='Sheet3')

        manu_map = {'S': 0, 'HZ': 1, 'C': 2, 'HK': 3}
        # manu_map = {'HK': 0, 'HZ': 1, 'S': 2, 'C': 3}
        family_dict = {i: Family() for i in manu_map.values()}
        valid_df1 = df1[df1['제작처'].isin(manu_map.keys())].copy()

        for row in valid_df1.itertuples():
            fam_name_str = row.제작처
            ship_date = int(row.선적일)

            # 해당 제작처의 정수 코드 조회 (예: 'S' -> 0)
            fam_code = manu_map[fam_name_str]

            # D-30 ~ D-Day 계산
            start_date = ship_date - 30
            end_date = ship_date

            # 0 이상인 날짜만 리스트 생성
            unavailable_range = [d for d in range(start_date, end_date + 1) if d >= 0]

            if unavailable_range:
                family_dict[fam_code].add_hard_unavailable(unavailable_range)

        # -------------------------------------------------------------------------
        # 3. [df_2 처리] Soft Constraint (휴일)
        # 로직: Specific > ALL 우선순위 적용
        # -------------------------------------------------------------------------
        # 3-1. 전처리: 제작처 NaN -> 'ALL', 날짜 음수 제거
        df_2_clean = df2.copy()
        df_2_clean['제작처'] = df_2_clean['제작처'].fillna('ALL')
        df_2_clean = df_2_clean[df_2_clean['날짜'] >= 0]

        # 3-2. 날짜별 그룹화
        date_groups = df_2_clean.groupby('날짜')

        for date_val, group in date_groups:
            current_date = int(date_val)

            # [Step A] 해당 날짜의 'ALL' 상태 확인 (Default)
            default_is_holiday = False
            row_all = group[group['제작처'] == 'ALL']
            if not row_all.empty:
                r = row_all.iloc[0]
                if r.WorkingDay == 0 or r.악기상 == 1:
                    default_is_holiday = True

            # [Step B] 각 Family별 상태 결정 (문자열 이름과 정수 코드를 매핑하며 순회)
            for fam_name_str, fam_code in manu_map.items():
                # 해당 Family 문자열('S', 'HZ' 등)로 된 행이 있는지 확인
                row_spec = group[group['제작처'] == fam_name_str]

                is_holiday = default_is_holiday  # 기본값은 ALL을 따름

                if not row_spec.empty:
                    # 특정 제작처 행이 있으면 Override
                    r = row_spec.iloc[0]
                    if r.WorkingDay == 0 or r.악기상 == 1:
                        is_holiday = True
                    else:
                        is_holiday = False  # ALL이 휴일이어도 나는 정상이면 정상

                # [Step C] 휴일이면 해당 정수 코드(fam_code)의 Family 객체에 추가
                if is_holiday:
                    family_dict[fam_code].add_holiday(current_date)
        cfg.family_dict = family_dict
