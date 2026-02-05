from typing import List
from model.data import Job
import random
import numpy as np
from model.utils import find_next_prime
import multiprocessing
from multiprocessing import Pool
import math
from collections import deque


class BaseGroupingSequencer:
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]: raise NotImplementedError


class EDDGroupingSequencer(BaseGroupingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].due_date)


class SSTGroupingSequencer(BaseGroupingSequencer):
    """Slack Time이 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].due_date - job_list[i].release_date - job_list[i].p_time)


class SAGroupingSequencer(BaseGroupingSequencer):
    """Area가 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].width * job_list[i].height)


class LAGroupingSequencer(BaseGroupingSequencer):
    """Area가 큰 순서대로 정렬"""
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].width * job_list[i].height, reverse=True)


def worker_fitness_calculation(args):
    chromosome, list_len, cfg, evaluator, data_list, machines = args
    decoded_seq = RKGAGroupingSequencer.decode_chromosome(list_len, chromosome)
    seq_tuple = tuple(decoded_seq)
    fitness = evaluator.calculate_fitness(cfg, decoded_seq, data_list, machines, {})
    return chromosome, fitness, seq_tuple


class RKGAGroupingSequencer(BaseGroupingSequencer):
    def get_sequence_list(self, cfg, job_list: List[Job], machines) -> List[int]:
        param = cfg.GAgrouper_parameter
        heuristic_sequencers = cfg.heuristic_grouping_sequencer
        evaluator = cfg.local_grouper
        return self.run_genetic_algorithm(cfg, evaluator, job_list, machines, param, heuristic_sequencers)

    def run_genetic_algorithm(self, cfg, evaluator, data_list, machines, param, heuristic_sequencers):
        best_sequence = list()
        best_fitness = float('inf')
        fitness_cache = dict()
        list_len = len(data_list)
        population = self.initialize_population(cfg, evaluator, data_list, machines, param,
                                                heuristic_sequencers, fitness_cache)

        early_stop_count = 0
        with Pool(processes=None, maxtasksperchild=100) as pool:
            for gen in range(param['generations']):
                evaluated_population = []
                to_calculate_args = []
                for chromosome in population:
                    decoded_seq = self.decode_chromosome(list_len, chromosome)
                    seq_key = tuple(decoded_seq)
                    if seq_key in fitness_cache:
                        fit = fitness_cache[seq_key]
                        evaluated_population.append((chromosome, fit))
                    else:
                        to_calculate_args.append(
                            (chromosome, list_len, cfg, evaluator, data_list, machines)
                        )
                if len(to_calculate_args) > 0:
                    results = pool.map(worker_fitness_calculation, to_calculate_args)
                    for chromo, fit, key in results:
                        evaluated_population.append((chromo, fit))
                        fitness_cache[key] = fit

                evaluated_population.sort(key=lambda x: x[1])
                current_best_chromosome, current_best_fitness = evaluated_population[0]
                if current_best_fitness < best_fitness:
                    best_fitness = current_best_fitness
                    best_sequence = self.decode_chromosome(list_len, current_best_chromosome)
                    early_stop_count = 0
                else:
                    early_stop_count += 1
                population = self.generate_new_population(evaluated_population, param)
                print(f"RKGA Gen {gen} Best Fitness: {best_fitness}")
                if early_stop_count >= param['early_stop_count']:
                    break
        cfg.best_fitness = best_fitness
        return best_sequence

    @staticmethod
    def encode_sequence(sequence, list_len):
        chromosome = [0.0] * list_len

        random_pool = sorted([random.uniform(0, 1) for _ in range(list_len)])
        for rank, job_index in enumerate(sequence):
            chromosome[job_index] = random_pool[rank]
        return chromosome

    @staticmethod
    def decode_chromosome(list_len, chromosome):
        return sorted(range(list_len), key=lambda i: chromosome[i])

    @staticmethod
    def tournament_selection(evaluated_population, tournament_size):
        tournament = random.sample(evaluated_population, tournament_size)
        tournament.sort(key=lambda x: x[1])
        return tournament[0][0]

    def initialize_population(self, cfg, evaluator, data_list, machines, param, heuristic_sequencers, fitness_cache):
        init_population = list()
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, data_list, None)
            chromosome = self.encode_sequence(sequence, len(data_list))
            init_population.append(chromosome)

        init_population.extend([[random.random() for _ in range(len(data_list))]
                                for _ in range(param['population_size'] - len(init_population))])
        return init_population

    def generate_new_population(self, evaluated_population, param):
        new_population = []
        num_elite = int(param['population_size'] * param['elite_rate'])
        elite_list = [chromosome for chromosome, fitness in evaluated_population[:num_elite]]
        new_population.extend(elite_list)
        while len(new_population) < param['population_size']:
            parent1, parent2 = self.select_parents(evaluated_population, num_elite, param['tournament_size'])
            child = self.crossover(parent1, parent2, param['crossover_prob'])
            child = self.mutate(child, param['mutation_rate'])
            new_population.append(child)
        return new_population

    def select_parents(self, evaluated_population, num_elite, tournament_size):
        parent1 = self.tournament_selection(evaluated_population, tournament_size)
        parent2 = self.tournament_selection(evaluated_population, tournament_size)
        return parent1, parent2

    @staticmethod
    def crossover(parent1, parent2, crossover_prob):
        child = list()
        for i in range(len(parent1)):
            if random.random() < 0.5:
                child.append(parent1[i])
            else:
                child.append(parent2[i])
        return child

    @staticmethod
    def mutate(chromosome, mutation_rate):
        mutated_child = list(chromosome)
        for i in range(len(chromosome)):
            if random.random() < mutation_rate:
                mutated_child[i] = random.random()
        return mutated_child


class BRKGAGroupingSequencer(RKGAGroupingSequencer):
    def generate_new_population(self, evaluated_population, param):
        new_population = []
        num_elite = int(param['population_size'] * param['elite_rate'])
        elite_list = [chromosome for chromosome, fitness in evaluated_population[:num_elite]]
        new_population.extend(elite_list)

        new_population.extend([[random.random() for _ in range(len(evaluated_population[0][0]))]
                               for _ in range(int(param['mutant_rate'] * param['population_size']))])

        while len(new_population) < param['population_size']:
            parent1, parent2 = self.select_parents(evaluated_population, num_elite, param['tournament_size'])
            new_population.append(self.crossover(parent1, parent2, param['crossover_prob']))
        return new_population

    def select_parents(self, evaluated_population, num_elite, tournament_size):
        parent1 = random.choice(evaluated_population[:num_elite])[0]
        parent2 = self.tournament_selection(evaluated_population[num_elite:], tournament_size)
        return parent1, parent2

    @staticmethod
    def crossover(parent1, parent2, crossover_prob):
        child = list()
        for i in range(len(parent1)):
            if random.random() < crossover_prob:
                child.append(parent1[i])
            else:
                child.append(parent2[i])
        return child


class OBRKGAGroupingSequencer(BRKGAGroupingSequencer):
    def initialize_population(self, cfg, evaluator, data_list, machines, param, heuristic_sequencers, fitness_cache):
        init_population = list()
        data_len = len(data_list)
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, data_list, None)
            chromosome = self.encode_sequence(sequence, data_len)
            init_population.append(chromosome)

        q_level = find_next_prime(data_len)
        m_rows = q_level * (q_level - 1)
        sample_indices = np.arange(m_rows)
        c1_base = sample_indices // (q_level - 1)
        c2_base = (sample_indices % (q_level - 1)) + 1
        oed_table = np.zeros((m_rows, data_len), dtype=int)
        oed_table[:, 0] = c1_base
        for j in range(data_len):
            oed_table[:, j] = (c1_base + j * c2_base) % q_level

        oed_sequences = np.argsort(oed_table, axis=1)
        unique_sequences = np.unique(oed_sequences, axis=0)
        sample_size = min(4000, len(unique_sequences))
        selected_indices = np.random.choice(len(unique_sequences), sample_size, replace=False)
        sequences = unique_sequences[selected_indices]

        process_args = [(seq, data_len) for seq in sequences]
        with Pool() as pool:
            sampled_population = pool.starmap(self.encode_sequence, process_args)

        if param['population_size'] - len(init_population) < len(sampled_population):
            list_len = len(data_list)
            to_calc_args = [
                (chromosome, list_len, cfg, evaluator, data_list, machines)
                for chromosome in sampled_population
            ]
            with Pool() as pool:
                results = pool.map(worker_fitness_calculation, to_calc_args)
            evaluated_samples = []
            for chromo, fit, key in results:
                evaluated_samples.append((chromo, fit))
                fitness_cache[key] = fit

            evaluated_samples.sort(key=lambda x: x[1])
            num_to_add = param['population_size'] - len(init_population)
            best_samples = [chromo for chromo, fit in evaluated_samples[:num_to_add]]

            # best_samples = random.sample(sampled_population, param['population_size'] - len(init_population))

            init_population.extend(best_samples)
        else:
            init_population.extend(sampled_population)
            num_to_add = param['population_size'] - len(init_population)
            if num_to_add > 0:
                random_chromosomes = [[random.random() for _ in range(len(data_list))] for _ in range(num_to_add)]
                init_population.extend(random_chromosomes)

        return init_population


class SimAGroupingSequencer(RKGAGroupingSequencer):
    def get_sequence_list(self, cfg, job_list, machines) -> list:
        # Grouping용 파라미터 로딩
        param = cfg.GAgrouper_parameter
        evaluator = cfg.local_grouper
        heuristic_sequencers = cfg.heuristic_grouping_sequencer

        # 공통 실행 함수 호출
        return self.run_sa(cfg, evaluator, job_list, machines, param, heuristic_sequencers)

    def run_sa(self, cfg, evaluator, data_list, machines, param, heuristic_sequencers):
        """SA 핵심 로직 (Job/Batch 공용)"""
        list_len = len(data_list)

        # 초기 해 생성
        if heuristic_sequencers:
            current_seq = heuristic_sequencers[0].get_sequence_list(None, data_list, None)
        else:
            current_seq = list(range(list_len))
            random.shuffle(current_seq)

        init_chromo = self.encode_sequence(current_seq, list_len)
        args = (init_chromo, list_len, cfg, evaluator, data_list, machines)
        _, current_fitness, _ = worker_fitness_calculation(args)

        best_seq = current_seq[:]
        best_fitness = current_fitness

        # 파라미터 매핑
        # param 딕셔너리에서 설정값 가져오기 (없으면 기본값)
        max_iter = 10000

        T = 1000.0
        min_T = 0.1
        cooling_rate = math.pow(min_T / T, 1.0 / max_iter)


        for i in range(max_iter):
            # 이웃 생성 (Swap)
            neighbor_seq = current_seq[:]
            idx1, idx2 = random.sample(range(list_len), 2)
            neighbor_seq[idx1], neighbor_seq[idx2] = neighbor_seq[idx2], neighbor_seq[idx1]

            # 평가
            neighbor_chromo = self.encode_sequence(neighbor_seq, list_len)
            args = (neighbor_chromo, list_len, cfg, evaluator, data_list, machines)
            _, neighbor_fitness, _ = worker_fitness_calculation(args)

            # 수락 판정
            delta = neighbor_fitness - current_fitness
            if delta < 0 or random.random() < math.exp(-delta / T):
                current_seq = neighbor_seq
                current_fitness = neighbor_fitness

                if current_fitness < best_fitness:
                    best_fitness = current_fitness
                    best_seq = current_seq[:]

            # 온도 감소
            T *= cooling_rate
            if i % 100 == 0:
                print(f"[SA] T={T}, fitness={best_fitness}, Iterations={i}")

        print(f"[SA] Finished. Best Fitness: {best_fitness}")
        cfg.best_fitness = best_fitness
        return best_seq


class TabuGroupingSequencer(RKGAGroupingSequencer):
    def get_sequence_list(self, cfg, job_list, machines) -> list:
        # Grouping용 파라미터 로딩
        param = cfg.GAgrouper_parameter
        evaluator = cfg.local_grouper
        heuristic_sequencers = cfg.heuristic_grouping_sequencer

        return self.run_tabu(cfg, evaluator, job_list, machines, param, heuristic_sequencers)

    def run_tabu(self, cfg, evaluator, data_list, machines, param, heuristic_sequencers):
        """Tabu 핵심 로직 (Job/Batch 공용)"""
        list_len = len(data_list)

        # 초기 해
        if heuristic_sequencers:
            current_seq = heuristic_sequencers[0].get_sequence_list(None, data_list, None)
        else:
            current_seq = list(range(list_len))
            random.shuffle(current_seq)

        init_chromo = self.encode_sequence(current_seq, list_len)
        args = (init_chromo, list_len, cfg, evaluator, data_list, machines)
        _, current_fitness, _ = worker_fitness_calculation(args)

        best_seq = current_seq[:]
        best_fitness = current_fitness

        # 파라미터
        max_iter = 1000
        num_neighbors = 50

        tabu_tenure = 20
        tabu_list = deque(maxlen=tabu_tenure)

        with Pool(processes=None) as pool:
            for it in range(max_iter):

                candidates = []
                moves = []
                to_calc_args = []

                for _ in range(num_neighbors):
                    n_seq = current_seq[:]
                    idx1, idx2 = random.sample(range(list_len), 2)
                    n_seq[idx1], n_seq[idx2] = n_seq[idx2], n_seq[idx1]

                    move = tuple(sorted((idx1, idx2)))
                    candidates.append(n_seq)
                    moves.append(move)

                    n_chromo = self.encode_sequence(n_seq, list_len)
                    to_calc_args.append(
                        (n_chromo, list_len, cfg, evaluator, data_list, machines)
                    )

                if to_calc_args:
                    results = pool.map(worker_fitness_calculation, to_calc_args)
                else:
                    results = []

                best_neighbor_fit = float('inf')
                best_neighbor_idx = -1

                for i, res in enumerate(results):
                    fit = res[1]
                    move = moves[i]

                    is_tabu = move in tabu_list
                    is_aspiration = fit < best_fitness

                    if (not is_tabu) or is_aspiration:
                        if fit < best_neighbor_fit:
                            best_neighbor_fit = fit
                            best_neighbor_idx = i

                if best_neighbor_idx != -1:
                    current_seq = candidates[best_neighbor_idx]
                    current_fitness = best_neighbor_fit
                    move_made = moves[best_neighbor_idx]
                    tabu_list.append(move_made)

                    if current_fitness < best_fitness:
                        best_fitness = current_fitness
                        best_seq = current_seq[:]
                if it % 10 == 0:
                    print(f"[TS] Iter {it}/{max_iter} |"
                          f" Best Neighbor: {best_neighbor_fit:.2f} | Global Best: {best_fitness:.2f}")

        print(f"[TS] Finished. Best Fitness: {best_fitness}")
        cfg.best_fitness = best_fitness
        return best_seq
