from typing import List, Tuple
from model.data import Batch
import numpy as np


class BaseScheduler:
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        raise NotImplementedError

    @staticmethod
    def calculate_single_machine_tardiness(batch_sequence_list, batch_list):
        completion_time = 0
        tardiness = 0
        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            completion_time = max(batch.max_release_date, completion_time) + batch.processing_time
            for due_date in batch.due_date_list:
                tardiness += max(0, completion_time - due_date)
        return tardiness

    @staticmethod
    def calculate_single_machine_jit(batch_sequence_list, batch_list):
        jit = 0
        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            jit += sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
        return jit

    def calculate_fitness(self, cfg, batch_sequence_list, batch_list, machines, fitness_cache):
        if tuple(batch_sequence_list) in fitness_cache:
            return fitness_cache[tuple(batch_sequence_list)]
        schedule_list, fitness = self.get_schedule(cfg, batch_list, batch_sequence_list, machines)
        fitness_cache[tuple(batch_sequence_list)] = fitness
        return fitness


class GLScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        machine_available_time_list = [0] * machines.n_machine
        schedule_list = [[] for _ in range(machines.n_machine)]
        total_tardiness = 0

        for idx in batch_sequence_list:
            best_machine_idx = -1
            best_machine_tardiness = float('inf')
            batch = batch_list[idx]
            # 모든 기계를 확인하여 이 배치를 가장 빨리 끝낼 수 있는 기계 탐색
            for m_idx in range(machines.n_machine):
                completion_time = (max(machine_available_time_list[m_idx], batch.max_release_date)
                                   + batch.processing_time)
                new_tardiness = 0
                for due_date in batch.due_date_list:
                    new_tardiness += max(0, completion_time - due_date)
                if new_tardiness < best_machine_tardiness:
                    best_machine_idx = m_idx
                    best_machine_tardiness = new_tardiness
                elif (new_tardiness == best_machine_tardiness
                      and machine_available_time_list[m_idx] > machine_available_time_list[best_machine_idx]):
                    best_machine_idx = m_idx

            schedule_list[best_machine_idx].append(batch.idx)
            machine_available_time_list[best_machine_idx] =\
                max(machine_available_time_list[best_machine_idx], batch.max_release_date) + batch.processing_time

            total_tardiness += best_machine_tardiness

        return schedule_list, total_tardiness


class IBHScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        schedule_list = [[] for _ in range(machines.n_machine)]
        machine_tardiness_list = [0] * machines.n_machine

        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            tardiness_dict = dict()
            for m_idx in range(machines.n_machine):
                for insert_pos_idx in range(len(schedule_list[m_idx]) + 1):
                    temp_schedule = schedule_list[m_idx][:]
                    temp_schedule.insert(insert_pos_idx, batch.idx)
                    temp_tardiness = self.calculate_single_machine_tardiness(temp_schedule, batch_list)
                    tardiness_dict[m_idx, insert_pos_idx] = temp_tardiness - machine_tardiness_list[m_idx]
            min_tardiness = min(tardiness_dict.values())
            (m_idx, insert_pos_idx) =\
                sorted([key for key, value in tardiness_dict.items() if value == min_tardiness])[0]
            schedule_list[m_idx].insert(insert_pos_idx, batch.idx)
            machine_tardiness_list[m_idx] = self.calculate_single_machine_tardiness(schedule_list[m_idx], batch_list)

        return schedule_list, sum(machine_tardiness_list)


class BackWardScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        schedule_list = [[] for _ in range(machines.n_machine)]

        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            if len(batch.due_date_list) % 2:
                ideal_end = int(np.median(batch.due_date_list))
            else:
                ideal_end = sorted(batch.due_date_list)[len(batch.due_date_list) // 2]
            ideal_start = ideal_end - batch.processing_time
            start_time_list = [batch_list[b_idx].start_time for schedule in schedule_list for b_idx in schedule]
            while ideal_start in start_time_list:
                ideal_start -= 1
                if ideal_start < batch.max_release_date:
                    ideal_start = ideal_end - batch.processing_time + 1
                    break
            while ideal_start < batch.max_release_date or ideal_start in start_time_list:
                ideal_start += 1
            ideal_end = ideal_start + batch.processing_time

            is_push = False
            best_m_idx = None
            best_slack_time = float('inf')
            for m_idx in range(machines.n_machine):
                if not schedule_list[m_idx]:
                    best_m_idx = m_idx
                    break
            while best_m_idx is None and not is_push:
                for m_idx in range(machines.n_machine):
                    slack_time = batch_list[schedule_list[m_idx][0]].start_time - ideal_end
                    if 0 <= slack_time <= best_slack_time:
                        best_m_idx = m_idx
                        best_slack_time = slack_time
                if best_m_idx is not None:
                    break
                else:
                    ideal_start -= 1
                    if ideal_start < batch.max_release_date:
                        is_push = True
                        ideal_start = batch.max_release_date
                        while ideal_start in start_time_list:
                            ideal_start += 1
                    else:
                        while ideal_start in start_time_list:
                            ideal_start -= 1
                            if ideal_start < batch.max_release_date:
                                ideal_start = batch.max_release_date
                                is_push = True
                                while ideal_start in start_time_list:
                                    ideal_start += 1
                                break
                    ideal_end = ideal_start + batch.processing_time

            if is_push:
                best_delay_sum = float('inf')
                for m_idx in range(machines.n_machine):
                    delay_sum = 0
                    completion_time = ideal_end
                    for b_idx2 in schedule_list[m_idx]:
                        batch2 = batch_list[b_idx2]
                        if batch2.start_time < completion_time:
                            while completion_time in start_time_list:
                                completion_time += 1
                            completion_time += batch2.processing_time
                            temp_end_time = completion_time
                            delay_sum += sum(abs(due_date - temp_end_time)
                                             for due_date in batch2.due_date_list) - batch2.delay_time
                        else:
                            break
                    if delay_sum < best_delay_sum:
                        best_delay_sum = delay_sum
                        best_m_idx = m_idx

                completion_time = ideal_end
                for b_idx2 in schedule_list[best_m_idx]:
                    batch2 = batch_list[b_idx2]
                    if batch2.start_time < completion_time:
                        while completion_time in start_time_list:
                            completion_time += 1
                        batch2.start_time = completion_time
                        completion_time += batch2.processing_time
                        batch2.end_time = completion_time
                        batch2.delay_time = sum(abs(batch2.end_time - due_date) for due_date in batch2.due_date_list)
            batch.start_time = ideal_start
            batch.end_time = ideal_end
            batch.delay_time = sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)
            schedule_list[best_m_idx].insert(0, b_idx)

        fitness = 0
        for batch in batch_list:
            fitness += batch.delay_time
        return schedule_list, fitness


class RealBackWardScheduler(BaseScheduler):
    def get_schedule(self, cfg, batch_list: List[Batch], batch_sequence_list, machines) -> Tuple[List[int], int]:
        family_dict = cfg.family_dict
        schedule_list = [[] for _ in range(machines.n_machine)]

        # [최적화] Family별 배치 객체 리스트 미리 매핑 (검사 속도 향상용)
        # 예: {1: [BatchObj1, BatchObj2], 2: [...]}
        batches_by_family = {}
        for b in batch_list:
            if b.family not in batches_by_family:
                batches_by_family[b.family] = []
            batches_by_family[b.family].append(b)

        # ------------------------------------------------------------------
        # [Helper Functions]
        # ------------------------------------------------------------------
        def get_real_end_time(start_t, pt, fam_code):
            """시작일로부터 소요기간 계산 (Hard/Soft 반영)"""
            family = family_dict[fam_code]
            if start_t in family.hard_unavailable: return None

            current_t = start_t
            worked = 0
            while worked < pt:
                if current_t in family.hard_unavailable: return None
                if current_t not in family.holidays:
                    worked += 1
                if worked < pt:
                    current_t += 1
            return current_t

        def calculate_ideal_start(target_end, pt, fam_code):
            """Backward: 목표 종료일로부터 역산"""
            family = family_dict[fam_code]
            curr_t = target_end
            needed_work = pt
            while needed_work > 0:
                curr_t -= 1
                if curr_t in family.hard_unavailable: continue
                if curr_t in family.holidays: continue
                needed_work -= 1
            return curr_t

        def check_family_gap_dynamic(target_start, my_batch_id, fam_code):
            """
            [핵심 수정] 현재 스케줄에 배치된(start_time이 None이 아닌)
            같은 Family의 '다른' 배치들과 실시간 3일 간격 체크
            """
            if fam_code == 0: return True

            # 미리 분류해둔 리스트 사용
            members = batches_by_family.get(fam_code, [])
            for member in members:
                # 나 자신은 제외
                if member.id == my_batch_id: continue
                # 아직 배치 안 된 녀석도 제외
                if member.start_time is None: continue

                # 간격 체크
                if abs(target_start - member.start_time) < 3:
                    return False
            return True

        def is_machine_available(m_idx, start_t, end_t):
            """마지막 머신 불가용 기간 체크"""
            if m_idx == machines.n_machine - 1:
                for u_day in machines.unavailable_list:
                    if start_t <= u_day <= end_t:
                        return False
            return True

        # ------------------------------------------------------------------
        # [Main Loop]
        # ------------------------------------------------------------------
        # 초기화: 모든 배치의 start_time을 None으로 (배치 여부 판단용)
        for b in batch_list:
            b.start_time = None

        for b_idx in batch_sequence_list:
            batch = batch_list[b_idx]
            fam_code = batch.family

            # 1. Ideal Start 역산
            if len(batch.due_date_list) % 2:
                ideal_end_target = int(np.median(batch.due_date_list))
            else:
                ideal_end_target = sorted(batch.due_date_list)[len(batch.due_date_list) // 2]

            ideal_start = calculate_ideal_start(ideal_end_target, batch.processing_time, fam_code)
            ideal_end = ideal_end_target

            # 전역 시작 시간 리스트 (동시 시작 방지)
            # 매번 새로 구함 (배치가 이동했을 수 있으므로)
            start_time_list = set(b.start_time for b in batch_list if b.start_time is not None)

            # ------------------------------------------------------------------
            # Phase 1: Backward Search
            # ------------------------------------------------------------------
            is_push = False
            best_m_idx = None

            while best_m_idx is None and not is_push:
                # A. 동시 시작 방지
                while ideal_start in start_time_list:
                    ideal_start -= 1
                    if ideal_start < batch.max_release_date: break

                # B. Release Date 체크 -> Push 전환
                if ideal_start < batch.max_release_date:
                    is_push = True
                    ideal_start = batch.max_release_date
                    # Push 시작점도 제약 만족해야 함
                    while True:
                        # 1. 동시 시작 체크
                        if ideal_start in start_time_list:
                            ideal_start += 1;
                            continue
                        # 2. Family Gap 체크 (동적)
                        if not check_family_gap_dynamic(ideal_start, batch.id, fam_code):
                            ideal_start += 1;
                            continue
                        # 3. Hard/Duration 체크
                        ideal_end = get_real_end_time(ideal_start, batch.processing_time, fam_code)
                        if ideal_end is None:
                            ideal_start += 1;
                            continue

                        break  # 모두 통과
                    break

                    # C. Backward 유효성 검증
                ideal_end = get_real_end_time(ideal_start, batch.processing_time, fam_code)
                is_fam_ok = check_family_gap_dynamic(ideal_start, batch.idx, fam_code)

                if ideal_end is None or not is_fam_ok:
                    ideal_start -= 1
                    continue

                # D. 머신 선택
                best_slack_time = float('inf')

                # 1) 빈 머신
                for m_idx in range(machines.n_machine):
                    if not schedule_list[m_idx]:
                        if is_machine_available(m_idx, ideal_start, ideal_end):
                            best_m_idx = m_idx
                            break

                            # 2) Slack 비교
                if best_m_idx is None:
                    for m_idx in range(machines.n_machine):
                        if not schedule_list[m_idx]: continue

                        # [주의] Backward Insert(0)이므로 index 0이 가장 빠른(Early) 배치
                        first_batch = batch_list[schedule_list[m_idx][0]]

                        # 겹치지 않아야 함 (내 끝 < 기존 시작)
                        if ideal_end < first_batch.start_time:
                            slack_time = first_batch.start_time - ideal_end
                            if slack_time <= best_slack_time:  # Slack은 작을수록 좋음
                                if is_machine_available(m_idx, ideal_start, ideal_end):
                                    best_m_idx = m_idx
                                    best_slack_time = slack_time

                if best_m_idx is None:
                    ideal_start -= 1

            # ------------------------------------------------------------------
            # Phase 2: Forward Search (Push Simulation)
            # ------------------------------------------------------------------
            if is_push:
                best_delay_sum = float('inf')
                best_m_idx = None

                for m_idx in range(machines.n_machine):
                    if not is_machine_available(m_idx, ideal_start, ideal_end): continue

                    delay_sum = 0
                    completion_time = ideal_end
                    valid_machine = True

                    # 시뮬레이션용 임시 리스트 (순서: 빠른 시간 -> 늦은 시간)
                    machine_batches = [batch_list[i] for i in schedule_list[m_idx]]
                    # 이미 정렬되어 있다고 가정 (Insert 0 & Sort)

                    for batch2 in machine_batches:
                        if batch2.start_time < completion_time:
                            # ------------------------------------------------------
                            # [핵심 수정] 밀리는 배치의 위치 찾기 (Gap 검사 포함)
                            # ------------------------------------------------------
                            sim_start = completion_time

                            while True:
                                # 1. 동시 시작 회피
                                if sim_start in start_time_list:
                                    sim_start += 1;
                                    continue

                                # 2. [추가] 밀리는 놈도 Family Gap 지켜야 함!
                                # 주의: 자기 자신(batch2)은 제외하고 검사
                                if not check_family_gap_dynamic(sim_start, batch2.id, batch2.family):
                                    sim_start += 1;
                                    continue

                                # 3. Hard/Duration 체크
                                sim_end = get_real_end_time(sim_start, batch2.processing_time, batch2.family)
                                if sim_end is None:
                                    sim_start += 1;
                                    continue

                                # 365일 이상 밀리면 포기
                                if sim_start > batch2.start_time + 365:
                                    sim_end = None  # Fail flag
                                    break

                                break  # 유효한 위치 찾음

                            if sim_end is None:
                                valid_machine = False;
                                break

                            delay_sum += sum(abs(d - sim_end) for d in batch2.due_date_list) - batch2.delay_time
                            completion_time = sim_end
                        else:
                            break  # 안 겹치면 중단

                    if valid_machine and delay_sum < best_delay_sum:
                        best_delay_sum = delay_sum
                        best_m_idx = m_idx

            # ------------------------------------------------------------------
            # Phase 3: 확정 및 적용 (Application)
            # ------------------------------------------------------------------
            # Push할 머신이 결정되었거나(best_m_idx), Backward로 찾았음
            # Backward 실패했는데 Push도 실패할 수 있음 (best_m_idx is None) -> 예외처리 필요
            # 여기선 무한루프 돌며 찾았다고 가정 (is_push logic에서 유효 start 보장했으므로)

            if best_m_idx is not None:
                # 1. 새 배치 정보 업데이트
                batch.start_time = ideal_start
                batch.end_time = ideal_end
                batch.delay_time = sum(abs(batch.end_time - d) for d in batch.due_date_list)

                # 리스트에 추가 (일단 넣고 정렬)
                schedule_list[best_m_idx].append(b_idx)
                schedule_list[best_m_idx].sort(key=lambda i: batch_list[i].start_time)

                # 2. Push 적용 (기존 배치들 밀기)
                if is_push:
                    # 해당 머신 다시 순회하며 겹치는 것들 밀기
                    completion_time = ideal_end

                    # 이미 schedule_list에 batch(새 놈)가 들어갔음.
                    # 새 놈 뒤에 있는 애들부터 밀리기 시작해야 함.

                    target_batches = [batch_list[i] for i in schedule_list[best_m_idx]]
                    # 정렬되어 있으므로, 새 배치(ideal_start) 이후의 배치들이 검사 대상

                    for batch2 in target_batches:
                        if batch2.id == batch.id: continue  # 방금 넣은 놈은 패스

                        # 겹치면 민다 (새 놈 끝 > 기존 놈 시작)
                        if completion_time > batch2.start_time:
                            new_start = completion_time

                            # [핵심 수정] 실제 적용 단계에서도 Loop 돌며 유효 위치 찾기
                            while True:
                                if new_start in start_time_list:
                                    new_start += 1;
                                    continue

                                # 밀리는 놈 Family Gap 검사
                                if not check_family_gap_dynamic(new_start, batch2.id, batch2.family):
                                    new_start += 1;
                                    continue

                                new_end = get_real_end_time(new_start, batch2.processing_time, batch2.family)
                                if new_end is None:
                                    new_start += 1;
                                    continue

                                break  # 찾음

                            # 업데이트
                            batch2.start_time = new_start
                            batch2.end_time = new_end
                            batch2.delay_time = sum(abs(batch2.end_time - d) for d in batch2.due_date_list)
                            completion_time = new_end
                        else:
                            # 정렬되어 있으므로 안 겹치면 그 뒤도 안전... 하지 않음!
                            # 왜냐하면 밀린 놈이 그 뒷놈을 또 밀 수 있음.
                            # 하지만 completion_time을 계속 갱신하므로,
                            # 다음 loop에서 (갱신된 completion_time > 다음 놈 start)를 검사하게 됨.
                            # 즉, 연쇄 작용(Cascade)은 자연스럽게 처리됨.
                            # 단, "안 겹친다"의 기준은 completion_time <= batch2.start_time 임.
                            # 이 경우엔 break 해도 됨. (completion_time이 더 이상 안 늘어나므로)
                            break

            # 전역 start_time_list 갱신은 다음 loop 시작 시 수행됨

        fitness = sum(b.delay_time for b in batch_list)

        print("\n[Start Strict Validation]")
        is_valid = True

        # 1. [Machine Overlap] 기계별로 배치가 겹치는지 검사
        for m_idx, b_indices in enumerate(schedule_list):
            # 시간순 정렬 (Start Time 기준)
            sorted_batches = sorted([batch_list[i] for i in b_indices], key=lambda b: b.start_time)

            for i in range(len(sorted_batches) - 1):
                b1 = sorted_batches[i]
                b2 = sorted_batches[i + 1]

                # 앞 배치 종료시간 > 뒤 배치 시작시간 = 충돌
                if b1.end_time > b2.start_time:
                    print(
                        f"[FAIL] Machine {m_idx} Overlap: Batch {b1.idx}(~{b1.end_time}) vs Batch {b2.idx}({b2.start_time}~)")
                    is_valid = False

        # 2. [Machine Unavailable] 마지막 기계가 불가 기간에 도는지 검사
        last_m_idx = machines.n_machine - 1
        if schedule_list[last_m_idx]:  # 마지막 기계에 배치가 있다면
            unavailable_set = set(machines.unavailable_list)
            for b_idx in schedule_list[last_m_idx]:
                batch = batch_list[b_idx]
                # 배치의 실행 기간 중 하루라도 unavailable_list에 포함되면 에러
                for t in range(batch.start_time, batch.end_time):
                    if t in unavailable_set:
                        print(f"[FAIL] Machine {last_m_idx} (Last) works on Unavailable Day {t}: Batch {batch.idx}")
                        is_valid = False

        # 3. [Family Constraint] 같은 Family끼리 3일 간격 검사
        family_starts = {code: [] for code in family_dict.keys()}
        for b in batch_list:
            family_starts[b.family].append((b.start_time, b))

        for code, items in family_starts.items():
            if code == 0: continue
            items.sort(key=lambda x: x[0])  # 시작시간 순 정렬
            for i in range(len(items) - 1):
                t1, b1 = items[i]
                t2, b2 = items[i + 1]
                if abs(t2 - t1) < 3:
                    print(
                        f"[FAIL] Family {code} Gap Violation: Batch {b1.idx}({t1}) & Batch {b2.idx}({t2}) Diff={t2 - t1}")
                    is_valid = False

        # 4. [Hard Constraint] 불가용일 작업 검사
        for b in batch_list:
            family = family_dict[b.family]
            for t in range(b.start_time, b.end_time):
                if t in family.hard_unavailable:
                    print(f"[FAIL] Hard Constraint: Batch {b.idx} works on Hard Day {t}")
                    is_valid = False

        result_msg = "PASSED" if is_valid else "FAILED"
        print(f"[Validation Result] : {result_msg}\n")

        return schedule_list, fitness
