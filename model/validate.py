"""해(solution) 타당성 검사.

모델이 낸 batch_list / schedule_list 가 문제 제약을 지키는지, 보고한 fitness가 맞는지 확인한다.
알고리즘을 고친 뒤 `python model/run_checks.py` 로 한 번에 확인하는 용도.

검사 항목
- 배치(묶기): 모든 job이 정확히 한 번 배치됨 / 한 배치에 한 family / 배치 범위 안 / 직사각형 겹침 없음
- 일정: 모든 배치가 정확히 한 기계에 배정됨 / start >= 배치 내 max release / 길이 = p_time /
        기계 안에서 겹침 없음 / (RC) 배치 시작 시간이 서로 다름
- fitness: 배치 시간으로 다시 계산한 값 == 보고된 값
"""


def placed_size(placed_job):
    """회전을 반영한 (width, height)"""
    job = placed_job.job
    return (job.height, job.width) if placed_job.rotation else (job.width, job.height)


def validate_batches(batch_list, job_list, machines):
    errors = list()
    placed_ids = sorted(pj.job.idx for batch in batch_list for pj in batch.placed_job_list)
    if placed_ids != sorted(job.idx for job in job_list):
        missing = set(job.idx for job in job_list) - set(placed_ids)
        duplicated = len(placed_ids) - len(set(placed_ids))
        errors.append(f"job 누락 {sorted(missing)[:10]} / 중복 {duplicated}개")

    for batch in batch_list:
        if not batch.placed_job_list:
            errors.append(f"B{batch.idx}: 빈 배치")
            continue
        families = {pj.job.family for pj in batch.placed_job_list}
        if len(families) != 1:
            errors.append(f"B{batch.idx}: family 혼합 {sorted(families)}")
        if batch.family is not None and families != {batch.family}:
            errors.append(f"B{batch.idx}: batch.family={batch.family} 와 job family {sorted(families)} 불일치")
        p_times = {pj.job.p_time for pj in batch.placed_job_list}
        if len(p_times) != 1:
            errors.append(f"B{batch.idx}: p_time 혼합 {sorted(p_times)}")

        rects = list()
        for pj in batch.placed_job_list:
            w, h = placed_size(pj)
            if pj.x < 0 or pj.y < 0 or pj.x + w > machines.width or pj.y + h > machines.height:
                errors.append(f"B{batch.idx}: job {pj.job.idx} 범위 밖 ({pj.x},{pj.y},{w}x{h})")
            rects.append((pj.job.idx, pj.x, pj.y, w, h))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                    errors.append(f"B{batch.idx}: job {a[0]}, {b[0]} 겹침")
    return errors


def jit_of(batch):
    """batch의 sum |end - due| (BW/CP 계열 목적함수)"""
    return sum(abs(batch.end_time - due_date) for due_date in batch.due_date_list)


def tardiness_of(batch):
    """batch의 sum max(0, end - due) (GL/IBH 목적함수)"""
    return sum(max(0, batch.end_time - due_date) for due_date in batch.due_date_list)


def set_forward_times(batch_list, schedule_list):
    """GL/IBH처럼 기계별 순서만 주는 스케줄러용: 순서대로 가능한 가장 빠른 시간에 배치"""
    for schedule in schedule_list:
        available = 0
        for b_idx in schedule:
            batch = batch_list[b_idx]
            batch.start_time = max(available, batch.max_release_date)
            batch.end_time = batch.start_time + batch.processing_time
            available = batch.end_time


def validate_schedule(batch_list, schedule_list, machines, distinct_start=True):
    errors = list()
    if len(schedule_list) != machines.n_machine:
        errors.append(f"기계 수 {len(schedule_list)} != {machines.n_machine}")
    assigned = sorted(b_idx for schedule in schedule_list for b_idx in schedule)
    if assigned != list(range(len(batch_list))):
        errors.append(f"배치 배정 누락/중복: 배정 {len(assigned)}개(고유 {len(set(assigned))}) / 배치 {len(batch_list)}개")

    for batch in batch_list:
        if batch.start_time is None or batch.end_time is None:
            errors.append(f"B{batch.idx}: 시간 없음")
            continue
        max_release = max(pj.job.release_date for pj in batch.placed_job_list)
        if batch.start_time < max_release:
            errors.append(f"B{batch.idx}: release 위반 (start {batch.start_time} < {max_release})")
        if batch.end_time - batch.start_time != batch.placed_job_list[0].job.p_time:
            errors.append(f"B{batch.idx}: 길이 {batch.end_time - batch.start_time} != p_time "
                          f"{batch.placed_job_list[0].job.p_time}")
    if errors:
        return errors

    for m_idx, schedule in enumerate(schedule_list):
        intervals = sorted((batch_list[b].start_time, batch_list[b].end_time, b) for b in schedule)
        for k in range(len(intervals) - 1):
            if intervals[k][1] > intervals[k + 1][0]:
                errors.append(f"M{m_idx}: B{intervals[k][2]}(~{intervals[k][1]}) 와 "
                              f"B{intervals[k + 1][2]}({intervals[k + 1][0]}~) 겹침")
    if distinct_start:
        starts = [batch.start_time for batch in batch_list]
        if len(set(starts)) != len(starts):
            errors.append(f"시작 시간 중복 (RC): 배치 {len(starts)}개, 고유 시작 {len(set(starts))}개")
    return errors


def validate_solution(batch_list, schedule_list, job_list, machines, reported_fitness=None,
                      objective='jit', distinct_start=True):
    """objective: 'jit' (sum |C-d|, BW/CP) 또는 'tardiness' (sum max(0, C-d), GL/IBH)
    tardiness 스케줄러는 batch 시간을 기록하지 않으므로 기계 순서로 시간을 다시 계산해서 검사한다."""
    errors = validate_batches(batch_list, job_list, machines)
    if errors:
        return errors
    if objective == 'tardiness':
        set_forward_times(batch_list, schedule_list)
    errors += validate_schedule(batch_list, schedule_list, machines, distinct_start=distinct_start)
    if not errors and reported_fitness is not None:
        recomputed = sum((jit_of if objective == 'jit' else tardiness_of)(batch) for batch in batch_list)
        if recomputed != reported_fitness:
            errors.append(f"fitness 불일치: 보고 {reported_fitness}, 재계산 {recomputed}")
    return errors
