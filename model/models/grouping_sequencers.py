from typing import List
from model.data import Job
import random
import numpy as np
from model.utils import find_next_prime


class BaseGroupingSequencer:
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]: raise NotImplementedError


class EDDGroupingSequencer(BaseGroupingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].due_date)


class SSTGroupingSequencer(BaseGroupingSequencer):
    """Slack Time이 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].due_date - job_list[i].release_date - job_list[i].p_time)


class SAGroupingSequencer(BaseGroupingSequencer):
    """Area가 작은 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)), key=lambda i: job_list[i].width * job_list[i].height)


class LAGroupingSequencer(BaseGroupingSequencer):
    """Area가 큰 순서대로 정렬"""
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        return sorted(range(len(job_list)),
                      key=lambda i: job_list[i].width * job_list[i].height, reverse=True)


class RKGAGroupingSequencer(BaseGroupingSequencer):
    def get_sequence_list(self, cfg, grouper, job_list: List[Job], machines) -> List[int]:
        param = cfg.GAgrouper_parameter
        heuristic_sequencers = [
            EDDGroupingSequencer(),
            SSTGroupingSequencer(),
            SAGroupingSequencer(),
            LAGroupingSequencer()
        ]
        return self.run_genetic_algorithm(grouper, job_list, machines, param, heuristic_sequencers)

    def run_genetic_algorithm(self, evaluator, data_list, machines, param, heuristic_sequencers):
        best_sequence = list()
        best_fitness = float('inf')
        fitness_cache = dict()
        list_len = len(data_list)
        population = self.initialize_population(evaluator, data_list, machines, param, heuristic_sequencers, fitness_cache)

        for gen in range(param['generations']):
            evaluated_population = [
                (chromosome, evaluator.calculate_fitness(self.decode_chromosome(list_len, chromosome),
                                                         data_list, machines, fitness_cache))
                for chromosome in population
            ]
            evaluated_population.sort(key=lambda x: x[1])
            current_best_chromosome, current_best_fitness = evaluated_population[0]
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_sequence = self.decode_chromosome(list_len, current_best_chromosome)
            new_population = []
            elite_list = [chromosome for chromosome, fitness
                          in evaluated_population[:int(param['population_size'] * param['elite_rate'])]]
            new_population.extend(elite_list)
            population = self.generate_new_population(new_population, evaluated_population, elite_list, param)
            print(f"RKGA Gen {gen} Best Fitness: {best_fitness}")
        return best_sequence

    @staticmethod
    def encode_sequence(sequence, list_len):
        chromosome = [0.0] * list_len
        for rank, job_index in enumerate(sequence):
            chromosome[job_index] = rank * (1.0 / list_len)
        return chromosome

    @staticmethod
    def decode_chromosome(list_len, chromosome):
        return sorted(range(list_len), key=lambda i: chromosome[i])

    @staticmethod
    def tournament_selection(evaluated_population, tournament_size):
        tournament = random.sample(evaluated_population, tournament_size)
        tournament.sort(key=lambda x: x[1])
        return tournament[0][0]

    def initialize_population(self, evaluator, data_list, machines, param, heuristic_sequencers, fitness_cache):
        init_population = list()
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, None, data_list, None)
            chromosome = self.encode_sequence(sequence, len(data_list))
            init_population.append(chromosome)

        init_population.extend([[random.random() for _ in range(len(data_list))]
                                for _ in range(param['population_size'] - len(init_population))])
        return init_population

    def generate_new_population(self, new_population, evaluated_population, elite_list, param):
        while len(new_population) < param['population_size']:
            parent1, parent2 = self.select_parents(evaluated_population, elite_list, param['tournament_size'])
            child = self.crossover(parent1, parent2, param['crossover_prob'])
            child = self.mutate(child, param['mutation_rate'])
            new_population.append(child)
        return new_population

    def select_parents(self, evaluated_population, elite_list, tournament_size):
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
    def generate_new_population(self, new_population, evaluated_population, elite_list, param):
        new_population.extend([[random.random() for _ in range(len(evaluated_population[0][0]))]
                               for _ in range(int(param['mutant_rate'] * param['population_size']))])

        while len(new_population) < param['population_size']:
            parent1, parent2 = self.select_parents(evaluated_population, elite_list, param['tournament_size'])
            new_population.append(self.crossover(parent1, parent2, param['crossover_prob']))
        return new_population

    def select_parents(self, evaluated_population, elite_list, tournament_size):
        parent1 = random.choice(elite_list)
        parent2 = self.tournament_selection(evaluated_population, tournament_size)
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
    def initialize_population(self, evaluator, data_list, machines, param, heuristic_sequencers, fitness_cache):
        init_population = list()
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, None, data_list, None)
            chromosome = self.encode_sequence(sequence, len(data_list))
            init_population.append(chromosome)

        q_level = find_next_prime(len(data_list))
        m_rows = q_level ** 2
        sample_size = min(param['population_size'] * 10, m_rows)
        sample_indices = np.sort(np.random.choice(m_rows, sample_size, replace=False))
        c1_base = sample_indices // q_level
        c2_base = sample_indices % q_level
        oed_table = np.zeros((sample_size, len(data_list)), dtype=int)
        oed_table[:, 0] = c1_base
        oed_table[:, 1] = c2_base

        for j in range(2, len(data_list)):
            oed_table[:, j] = (c1_base + (j - 1) * c2_base) % q_level
        sampled_population = (oed_table / (q_level - 1)).tolist()
        evaluated_samples = [
            (chromosome, evaluator.calculate_fitness(self.decode_chromosome(len(data_list), chromosome),
                                                     data_list, machines, fitness_cache))
            for chromosome in sampled_population
        ]
        evaluated_samples.sort(key=lambda x: x[1])
        num_to_add = min(param['population_size'] - len(init_population), len(evaluated_samples))
        best_samples = [chromo for chromo, fit in evaluated_samples[:num_to_add]]
        init_population.extend(best_samples)

        num_final_random = param['population_size'] - len(init_population)
        if num_final_random > 0:
            random_chromosomes = [[random.random() for _ in range(len(data_list))] for _ in range(num_final_random)]
            init_population.extend(random_chromosomes)

        return init_population
