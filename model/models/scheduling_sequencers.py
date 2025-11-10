from typing import List
from model.data import Batch
from .grouping_sequencers import RKGAGroupingSequencer, BRKGAGroupingSequencer, OBRKGAGroupingSequencer
import numpy as np


class BaseSchedulingSequencer:
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        raise NotImplementedError


class EDDSchedulingSequencer(BaseSchedulingSequencer):
    """Due Date가 빠른 순서대로 정렬"""
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: np.average(batch_list[i].due_date_list))


class MBSchedulingSequencer(BaseSchedulingSequencer):
    # most job first?
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        return sorted(range(len(batch_list)), key=lambda i: len(batch_list[i].placed_job_list), reverse=True)


class RKGASchedulingSequencer(BaseSchedulingSequencer, RKGAGroupingSequencer):
    def get_sequence_list(self, cfg, scheduler, batch_list: List[Batch], machines) -> List[int]:
        param = cfg.GAsequencer_parameter
        population_size = param['population_size']
        generations = param['generations']
        elite_rate = param['elite_rate']
        tournament_size = param['tournament_size']
        crossover_prob = param['crossover_prob']
        best_sequence = list()
        best_fitness = float('inf')
        fitness_cache = dict()
        heuristic_sequencers = [
            EDDSchedulingSequencer(),
            MBSchedulingSequencer()
        ]
        population = self.initialize_population(batch_list, machines, heuristic_sequencers,
                                                scheduler, population_size, fitness_cache)

        for gen in range(generations):
            evaluated_population = [
                (chromosome, scheduler.calculate_fitness(self.decode_chromosome(len(batch_list), chromosome),
                                                         batch_list, machines, fitness_cache))
                for chromosome in population
            ]
            evaluated_population.sort(key=lambda x: x[1])
            current_best_chromosome, current_best_fitness = evaluated_population[0]
            if current_best_fitness < best_fitness:
                best_fitness = current_best_fitness
                best_sequence = self.decode_chromosome(len(batch_list), current_best_chromosome)
            new_population = []
            elite_list = [chromosome for chromosome, fitness
                          in evaluated_population[:int(population_size * elite_rate)]]
            new_population.extend(elite_list)
            population = self.generate_new_population(new_population, evaluated_population, elite_list,
                                                      population_size, tournament_size, crossover_prob, param)
            print(f"RKGA Gen {gen} Best Fitness: {best_fitness}")
        return best_sequence


class BRKGASchedulingSequencer(RKGASchedulingSequencer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouping_sequencer = BRKGAGroupingSequencer()

    def generate_new_population(self, *args, **kwargs):
        return self.grouping_sequencer.generate_new_population(*args, **kwargs)

    def select_parents(self, *args, **kwargs):
        return self.grouping_sequencer.select_parents(*args, **kwargs)

    @staticmethod
    def crossover(*args, **kwargs):
        return BRKGAGroupingSequencer.crossover(*args, **kwargs)


class OBRKGASchedulingSequencer(BRKGASchedulingSequencer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouping_sequencer = OBRKGAGroupingSequencer()

    def initialize_population(self, *args, **kwargs):
        return self.grouping_sequencer.initialize_population(*args, **kwargs)

