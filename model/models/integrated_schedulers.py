from typing import List, Tuple
from model.data import Batch
from docplex.cp.model import *


class BaseIntegratedScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], machines) -> Tuple[List[int], int]: raise NotImplementedError


class CPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], machines):
        heuristic_sequencers = cfg.heuristic_scheduling_sequencer
        scheduler = cfg.local_scheduler
        best_schedule_list = list()
        best_fitness = float('inf')
        best_sequencer = None
        best_sequence_list = None
        for sequencer in heuristic_sequencers:
            batch_sequence_list = sequencer.get_sequence_list(None, batch_list, None)
            current_schedule_list, current_fitness =\
                scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)
            if current_fitness < best_fitness:
                best_schedule_list = current_schedule_list
                best_fitness = current_fitness
                best_sequencer = sequencer
                best_sequence_list = batch_sequence_list

        model = CpoModel()
        end_time = max(batch_list[b_idx].end_time for schedule in best_schedule_list for b_idx in schedule)
        batch_var_dict = dict()
        obj = 0
        load_function = model.step_at(0, 0)
        # for b_idx, batch in enumerate(batch_list):
        for b_idx in best_sequence_list:
            batch = batch_list[b_idx]
            var = model.interval_var(start=(batch.max_release_date, end_time), size=batch.processing_time)
            load_function += model.pulse(var, 1)
            obj += model.sum([model.abs(due_date - model.end_of(var)) for due_date in batch.due_date_list])
            # for _, var2 in batch_var_dict.items():
            #     model.add(model.start_of(var) != model.start_of(var2))
            batch_var_dict[b_idx] = var
        all_start_times = [model.start_of(var) for var in batch_var_dict.values()]
        model.add(model.all_diff(all_start_times))
        model.add(load_function <= machines.n_machine)
        model.add(model.minimize(obj))

        if cfg.use_starting_point:
            batch_sequence_list = best_sequencer.get_sequence_list(None, batch_list, None)
            best_schedule_list, best_fitness = \
                scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)
            start_sol = CpoModelSolution()
            for b_idx, batch in enumerate(batch_list):
                start_sol.add_interval_var_solution(batch_var_dict[b_idx], start=batch.start_time)
            model.set_starting_point(start_sol)

        sol = model.solve(TimeLimit=cfg.cp_search_time_limit, SearchType='Auto', log_output=None)

        if sol:
            print(f"Final objective value: {sol.get_objective_value()}")
            schedule_list = [[] for _ in range(machines.n_machine)]
            total_fitness = 0
            for b_idx, var in batch_var_dict.items():
                batch = batch_list[b_idx]
                batch.start_time = sol.get_var_solution(var).get_start()
                batch.end_time = sol.get_var_solution(var).get_end()
                batch.delay_time = sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
                total_fitness += batch.delay_time
            schedule_list[0] = sorted(range(len(batch_list)), key=lambda i: batch_list[i].end_time)
            return schedule_list, total_fitness
        else:
            return best_schedule_list, best_fitness


class RealCPIntegratedScheduler(BaseIntegratedScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], machines):
        heuristic_sequencers = cfg.heuristic_scheduling_sequencer
        scheduler = cfg.local_scheduler

        # 1. Heuristic Warm Start (기존 로직 유지)
        best_schedule_list = list()
        best_fitness = float('inf')
        best_sequencer = None
        best_sequence_list = None

        # CP Solver가 시작점으로 삼을 초기 해를 Heuristic으로 탐색
        for sequencer in heuristic_sequencers:
            batch_sequence_list = sequencer.get_sequence_list(None, batch_list, None)
            current_schedule_list, current_fitness = \
                scheduler.get_schedule(cfg, batch_list, batch_sequence_list, machines)

            if current_fitness < best_fitness:
                best_schedule_list = current_schedule_list
                best_fitness = current_fitness
                best_sequencer = sequencer
                best_sequence_list = batch_sequence_list

        # ==============================================================================
        # 2. CP 모델링 시작
        # ==============================================================================
        model = CpoModel()
        family_dict = cfg.family_dict

        # Heuristic 결과에서 가장 늦은 종료 시간을 기준으로 Horizon 설정 (여유분 추가)
        horizon_end = max(batch_list[b_idx].end_time for schedule in best_schedule_list for b_idx in schedule)
        horizon_end = int(horizon_end + 10000)  # 넉넉하게 잡음

        # --------------------------------------------------------------------------
        # [준비 1] Family 별 Intensity (휴일) & Hard Function (불가) 생성
        # --------------------------------------------------------------------------
        fam_intensity_funcs = {}  # Soft (휴일) 관리용
        fam_hard_funcs = {}  # Hard (불가) 관리용

        for fam_code, family in family_dict.items():
            # A. Intensity Function (Soft: 휴일)
            # 기본값 100(작업 가능), 휴일엔 0(작업 멈춤)
            intensity = CpoStepFunction()
            intensity.set_value(0, horizon_end, 100)

            # holidays 리스트는 연속된 날짜일 수도, 띄엄띄엄일 수도 있음
            # 효율을 위해 연속 구간으로 뭉치거나, loop 돌며 0으로 설정
            for h_day in family.holidays:
                # h_day ~ h_day+1 구간을 0으로 (CP는 시작 포함, 끝 제외)
                intensity.set_value(h_day, h_day + 1, 0)

            fam_intensity_funcs[fam_code] = intensity

            # B. Hard Function (Hard: 절대 불가)
            # 기본값 0(허용), 불가 기간엔 1(금지) -> forbid_extent에 사용
            hard_f = CpoStepFunction()
            hard_f.set_value(0, horizon_end, 0)

            # hard_unavailable 리스트 처리
            # (연속된 구간을 효율적으로 넣으면 좋으나, 안전하게 하루씩 처리)
            for h_day in family.hard_unavailable:
                hard_f.set_value(h_day, h_day + 1, 1)

            fam_hard_funcs[fam_code] = hard_f

        # --------------------------------------------------------------------------
        # [준비 2] Machine Capacity Function 생성 (마지막 머신 불가 반영)
        # --------------------------------------------------------------------------
        # 기본 용량 = n_machine
        # machine_capacity = CpoStepFunction()
        # machine_capacity.set_value(0, horizon_end, machines.n_machine)
        #
        # # 마지막 머신(N-1) 불가 기간에는 용량을 1 줄임 (N -> N-1)
        # for u_day in machines.unavailable_list:
        #     # 해당 날짜의 용량을 -1 (기존 값에서 뺌)
        #     # add_value를 쓰면 기존 값(N)에 -1을 더해 N-1이 됨
        #     machine_capacity.add_value(u_day, u_day + 1, -1)

        # --------------------------------------------------------------------------
        # [준비 3] 변수 생성 및 제약 조건 추가
        # --------------------------------------------------------------------------
        batch_var_dict = dict()
        load_expression = model.step_at(0, 0)  # 누적 자원 사용량
        obj = 0

        # 자원 제약(3일 간격)을 위해 Family별 변수 수집
        vars_by_family = {code: [] for code in family_dict.keys()}

        # batch_sequence_list 순서대로 변수 생성 (Starting Point 매핑을 위해 enumerate 대신 사용 추천)
        # 하지만 map key는 b_idx여야 하므로 batch_list 전체 순회
        for b_idx, batch in enumerate(batch_list):
            fam_code = batch.family

            # 1. Interval Variable 생성
            # size: 순수 작업 시간 (Processing Time)
            # intensity: 휴일 함수 적용 (휴일엔 작업 안함 -> 기간 자동 연장)
            var = model.interval_var(
                size=batch.processing_time,
                intensity=fam_intensity_funcs[fam_code],
                start=(batch.max_release_date, horizon_end),
                name=f"B_{b_idx}"
            )

            # 2. Hard Constraint (forbid_extent)
            # 해당 배치는 Hard Function이 1인 구간(불가일)과 겹칠 수 없음
            # model.add(model.forbid_extent(var, fam_hard_funcs[fam_code]))
            for date in family_dict[fam_code].hard_unavailable:
                model.add(model.start_of(var) != date)
            # 3. Objective (Tardiness)
            obj += model.sum([model.abs(due_date - model.end_of(var)) for due_date in batch.due_date_list])

            # 4. 자원 사용량 (Pulse)
            load_expression += model.pulse(var, 1)

            # 저장
            batch_var_dict[b_idx] = var
            vars_by_family[fam_code].append(var)

        for u_day in machines.unavailable_list:
            # start=u_day, end=u_day+1, size=1 인 구간에서 자원 1 소모
            # interval_var를 만들 필요 없이 바로 pulse에 구간을 넣을 수 있음
            load_expression += model.pulse((u_day, u_day + 1), 1)

        # --------------------------------------------------------------------------
        # [준비 4] Global Constraints
        # --------------------------------------------------------------------------

        # 1. Machine Capacity 제약
        # (누적 사용량) <= (가변 용량 함수: 평소 N, 불가시 N-1)
        model.add(load_expression <= machines.n_machine)

        # 2. 모든 배치의 시작 시간은 달라야 함 (기존 제약 유지)
        all_start_times = [model.start_of(var) for var in batch_var_dict.values()]
        model.add(model.all_diff(all_start_times))

        # 3. [핵심] Family 자원 제약 (3일 간격)
        # Family 0 제외, 같은 Family 내 배치끼리 시작 시간 차이 >= 3
        for fam_code, var_list in vars_by_family.items():
            if fam_code == 0:
                continue

            # 리스트 내 모든 쌍에 대해 제약 추가 (N^2)
            # 배치가 많으면 부담될 수 있으나 CP Solver 성능상 수백개까진 괜찮음
            n_vars = len(var_list)
            for i in range(n_vars):
                for j in range(n_vars):
                    if i == j:
                        continue
                    # |start(i) - start(j)| >= 3
                    model.add(model.abs(model.start_of(var_list[i]) - model.start_of(var_list[j])) >= 3)

        # 목적함수 설정
        model.add(model.minimize(obj))

        # --------------------------------------------------------------------------
        # [준비 5] Starting Point (Warm Start) 설정
        # --------------------------------------------------------------------------
        if cfg.use_starting_point:
            # Heuristic 해를 CP 초기해로 주입
            start_sol = CpoModelSolution()

            for b_idx, batch in enumerate(batch_list):
                # Heuristic 스케줄의 start_time 가져오기
                heuristic_start = batch.start_time

                # 주의: Heuristic 해가 Hard 제약 등을 완벽히 만족하지 못할 경우(미세한 차이 등)
                # Starting Point가 Reject 될 수 있음. 하지만 시도는 함.
                start_sol.add_interval_var_solution(batch_var_dict[b_idx], start=heuristic_start)

            model.set_starting_point(start_sol)

        # ==============================================================================
        # 3. Solve
        # ==============================================================================
        sol = model.solve(TimeLimit=cfg.cp_search_time_limit, SearchType='Auto')

        if sol:
            print(f"Final objective value (CP): {sol.get_objective_value()}")
            schedule_list = [[] for _ in range(machines.n_machine)]  # CP는 Cumulative라 개별 머신 배정 정보는 없음
            total_fitness = 0

            # 결과 업데이트
            # CP 결과에는 머신 배정 정보(어떤 배치가 몇번 머신인지)가 포함되지 않음 (Cumulative Resource 특성)
            # 따라서 결과 반환용으로는 '종료 시간 순'으로 정렬해서 0번 리스트에 몰아넣거나,
            # 사후 처리를 통해 머신에 다시 할당(Bin Packing)해야 함.
            # 여기서는 원본 코드 스타일대로 0번에 몰아넣는 방식을 유지함 (시각화/검증 시 주의 필요)

            sorted_indices = sorted(range(len(batch_list)),
                                    key=lambda i: sol.get_var_solution(batch_var_dict[i]).get_end())

            for b_idx in sorted_indices:
                var = batch_var_dict[b_idx]
                batch = batch_list[b_idx]

                # CP 해 적용
                batch.start_time = sol.get_var_solution(var).get_start()
                batch.end_time = sol.get_var_solution(var).get_end()
                batch.delay_time = sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
                total_fitness += batch.delay_time

            # 머신 할당 정보가 없으므로 임의로 배치하거나, 그냥 리스트 하나에 담음 (기존 코드 로직 따름)
            schedule_list[0] = sorted_indices

            return schedule_list, total_fitness
        else:
            print("CP failed to find a solution. Returning Heuristic solution.")
            return best_schedule_list, best_fitness
