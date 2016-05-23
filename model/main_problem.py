#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base_problem import BaseProblem


class MainProblem(BaseProblem):
    def __init__(self, name='MainProblem'):
        super(MainProblem, self).__init__(name=name)
        self.available_constants = ['s', 'c', 'Q', 'T', 'h']
        self.ModelName = name

    def build_dimensions(self, data):
        """ get the dimension from data
        """
        self.dimensions['n'] = data.get('n', 0)
        self.dimensions['r'] = data.get('r', 0)
        self.dimensions['p'] = data.get('p', 0)
        if not self.dimensions['n'] or not self.dimensions['r'] or not self.dimensions['p']:
            self.logger.warning("%s: at least one variable is missing" % self.__class__.__name__)
            return False
        return True

    def build_constants(self, data):
        for name in self.available_constants:
            self.constants[name] = data.get(name, [])
        return True
