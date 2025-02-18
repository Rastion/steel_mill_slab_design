import sys
import math
import random
from qubots.base_problem import BaseProblem
import os

def read_integers(filename):

    # Resolve relative path with respect to this module’s directory.
    if not os.path.isabs(filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base_dir, filename)

    with open(filename) as f:
        return [int(elem) for elem in f.read().split()]

def pre_compute_waste_for_content(slab_sizes, sum_size_orders):
    """
    Pre-compute the waste for each possible content value (from 0 up to sum_size_orders-1)
    given the available slab sizes. For each content value c that does not exactly match a slab size,
    the waste is defined as (next available slab size - c). Content values that exactly match a slab size yield zero waste.
    """
    waste_for_content = [0] * (sum_size_orders + 1)
    prev_size = 0
    for size in slab_sizes:
        if size < prev_size:
            print("Slab sizes should be sorted in ascending order")
            sys.exit(1)
        for content in range(prev_size + 1, size):
            waste_for_content[content] = size - content
        prev_size = size
    return waste_for_content

class SteelMillSlabDesignProblem(BaseProblem):
    """
    Steel Mill Slab Design Problem

    A steel mill produces slabs of a few fixed sizes. Each order has a quantity (weight) and a color.
    The goal is to assign the orders to slabs (a partition of orders) so that:
      - The total weight (content) of orders in any slab does not exceed the largest slab size.
      - Each slab contains orders of at most a fixed number of colors (here, at most 2).
      - The overall objective is to minimize the total waste, where the waste on a slab is computed
        via a pre-computed “waste profile” that gives the extra steel produced if the slab’s content does not exactly match one of the available sizes.

    Instance File Format:
      - First line: an integer nb_slab_sizes followed by nb_slab_sizes integers giving the available slab sizes (in ascending order).
      - Second line: an integer nb_colors.
      - Third line: an integer nb_orders.
      - Then, for each order, two integers are provided: the order quantity and its color.
    
    Decision Variables:
      A candidate solution is a partition of the orders (indexed 0..nb_orders-1) into slabs.
      We represent a candidate as a list of slabs (each slab is a list of order indices).
      (Empty slabs are allowed; only nonempty slabs count toward the objective.)
    
    Objective:
      For each used slab, let content be the sum of the quantities of orders assigned to it.
      The waste on that slab is given by waste_for_content[content] (which is zero when content exactly matches a slab size).
      The goal is to minimize the total wasted steel summed over all used slabs.
    
    Additional constraints (enforced via penalties in the evaluation):
      - Each order must appear in exactly one slab.
      - In each slab, the number of distinct colors must not exceed 2.
      - The total content of a slab must not exceed the maximum slab size.
    """

    def __init__(self, instance_file):
        self.instance_file = instance_file
        tokens = read_integers(instance_file)
        it = iter(tokens)
        # First, read slab sizes.
        self.nb_slab_sizes = int(next(it))
        self.slab_sizes = [int(next(it)) for _ in range(self.nb_slab_sizes)]
        self.max_size = self.slab_sizes[-1]
        # Next, number of colors.
        self.nb_colors = int(next(it))
        # Then, number of orders.
        self.nb_orders = int(next(it))
        # We assume the number of available slabs equals the number of orders.
        self.nb_slabs = self.nb_orders
        # Read orders: for each order, its quantity and color.
        self.quantities_data = []
        self.colors_data = []
        self.sum_size_orders = 0
        for _ in range(self.nb_orders):
            qty = int(next(it))
            col = int(next(it))
            self.quantities_data.append(qty)
            self.colors_data.append(col)
            self.sum_size_orders += qty
        # Pre-compute the waste profile.
        self.waste_for_content = pre_compute_waste_for_content(self.slab_sizes, self.sum_size_orders)
        # Maximum number of colors allowed per slab (fixed to 2).
        self.nb_colors_max_slab = 2

    def evaluate_solution(self, candidate) -> float:
        """
        Evaluate a candidate solution.
        
        Candidate format: a list of slabs, where each slab is a list of order indices.
        The union of all slabs must equal {0,...,nb_orders-1} (each order appears exactly once).
        
        For each nonempty slab:
          - Compute its content = sum of quantities of orders in the slab.
          - If content exceeds max_size, add a heavy penalty.
          - Compute the number of distinct colors in the slab; if it exceeds nb_colors_max_slab, add a penalty.
          - The waste for the slab is waste_for_content[content] (if content is within the precomputed range).
        
        The objective is the total waste over all used slabs plus any penalties.
        """
        penalty = 0
        used_slab_waste = 0
        orders_in_candidate = []
        # Process each slab.
        for slab in candidate:
            # Collect orders assigned in this slab.
            orders_in_candidate.extend(slab)
            if len(slab) == 0:
                continue
            # Check color constraint.
            slab_colors = {self.colors_data[i] for i in slab}
            if len(slab_colors) > self.nb_colors_max_slab:
                penalty += 1e6 * (len(slab_colors) - self.nb_colors_max_slab)
            # Compute content of the slab.
            content = sum(self.quantities_data[i] for i in slab)
            if content > self.max_size:
                penalty += 1e6 * (content - self.max_size)
            # Get waste: if content is within the range of waste_for_content, use it;
            # otherwise, if content == 0 then waste=0; if content exceeds, add penalty.
            if content < len(self.waste_for_content):
                waste = self.waste_for_content[content]
            else:
                waste = self.max_size - content  # Should not occur if constraints are met.
            used_slab_waste += waste

        # Partition constraint: all orders must appear exactly once.
        if set(orders_in_candidate) != set(range(self.nb_orders)):
            penalty += 1e6

        return used_slab_waste + penalty

    def random_solution(self):
        """
        Generates a random candidate solution.
        
        A simple method: assign each order (0...nb_orders-1) to a random slab (0...nb_slabs-1),
        then group orders by slab.
        """
        assignment = [random.randint(0, self.nb_slabs - 1) for _ in range(self.nb_orders)]
        slabs = [[] for _ in range(self.nb_slabs)]
        for order, slab_id in enumerate(assignment):
            slabs[slab_id].append(order)
        # Optionally, remove empty slabs (or leave them—they contribute no waste).
        candidate = [s for s in slabs]
        return candidate
