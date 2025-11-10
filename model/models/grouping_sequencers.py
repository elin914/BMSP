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
        population_size = param['population_size']
        generations = param['generations']
        elite_rate = param['elite_rate']
        tournament_size = param['tournament_size']
        crossover_prob = param['crossover_prob']
        best_sequence = list()
        best_fitness = float('inf')
        fitness_cache = dict()
        heuristic_sequencers = [
            EDDGroupingSequencer(),
            SSTGroupingSequencer(),
            SAGroupingSequencer(),
            LAGroupingSequencer()
        ]
        population = self.initialize_population(job_list, machines, heuristic_sequencers,
                                                grouper, population_size, fitness_cache)

        for gen in range(generations):
            evaluated_population = [
                (chromosome, grouper.calculate_fitness(self.decode_chromosome(len(job_list), chromosome),
                                                       job_list, machines, fitness_cache))
                for chromosome in population
            ]
            evaluated_population.sort(key=lambda x: x[1])
            current_best_chromosome, current_best_fitness = evaluated_population[0]
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_sequence = self.decode_chromosome(len(job_list), current_best_chromosome)
            new_population = []
            elite_list = [chromosome for chromosome, fitness
                          in evaluated_population[:int(population_size * elite_rate)]]
            new_population.extend(elite_list)
            population = self.generate_new_population(new_population, evaluated_population, elite_list,
                                                      population_size, tournament_size, crossover_prob, param)
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

    def initialize_population(self, job_list, machines, heuristic_sequencers, grouper, population_size, fitness_cache):
        init_population = list()
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, None, job_list, None)
            chromosome = self.encode_sequence(sequence, len(job_list))
            init_population.append(chromosome)

        init_population.extend([[random.random() for _ in range(len(job_list))]
                                for _ in range(population_size - len(init_population))])
        return init_population

    def generate_new_population(self, new_population, evaluated_population, elite_list,
                                population_size, tournament_size, crossover_prob, param):
        while len(new_population) < population_size:
            parent1, parent2 = self.select_parents(evaluated_population, elite_list, tournament_size)
            child = self.crossover(parent1, parent2, crossover_prob)
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
    def generate_new_population(self, new_population, evaluated_population, elite_list,
                                population_size, tournament_size, crossover_prob, param):
        new_population.extend([[random.random() for _ in range(len(evaluated_population[0][0]))]
                               for _ in range(int(param['mutant_rate'] * population_size))])

        while len(new_population) < population_size:
            parent1, parent2 = self.select_parents(evaluated_population, elite_list, tournament_size)
            new_population.append(self.crossover(parent1, parent2, crossover_prob))
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
    def initialize_population(self, job_list, machines, heuristic_sequencers, grouper, population_size, fitness_cache):
        init_population = list()
        for sequencer in heuristic_sequencers:
            sequence = sequencer.get_sequence_list(None, None, job_list, None)
            chromosome = self.encode_sequence(sequence, len(job_list))
            init_population.append(chromosome)

        q_level = find_next_prime(len(job_list))
        m_rows = q_level ** 2
        sample_size = min(population_size * 10, m_rows)
        sample_indices = np.sort(np.random.choice(m_rows, sample_size, replace=False))
        c1_base = sample_indices // q_level
        c2_base = sample_indices % q_level
        oed_table = np.zeros((sample_size, len(job_list)), dtype=int)
        oed_table[:, 0] = c1_base
        oed_table[:, 1] = c2_base

        for j in range(2, len(job_list)):
            oed_table[:, j] = (c1_base + (j - 1) * c2_base) % q_level
        sampled_population = (oed_table / (q_level - 1)).tolist()
        evaluated_samples = [
            (chromosome, grouper.calculate_fitness(self.decode_chromosome(len(job_list), chromosome),
                                                   job_list, machines, fitness_cache))
            for chromosome in sampled_population
        ]
        evaluated_samples.sort(key=lambda x: x[1])
        num_to_add = min(population_size - len(init_population), len(evaluated_samples))
        best_samples = [chromo for chromo, fit in evaluated_samples[:num_to_add]]
        init_population.extend(best_samples)

        num_final_random = population_size - len(init_population)
        if num_final_random > 0:
            random_chromosomes = [[random.random() for _ in range(len(job_list))] for _ in range(num_final_random)]
            init_population.extend(random_chromosomes)

        return init_population


