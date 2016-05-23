#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gurobipy as gb
from model.main_problem import MainProblem
from utils.tools import get_value


class LinearOneVariableProblem(MainProblem):

    def __init__(self, data, name='ExaminationProblem'):
        super(LinearOneVariableProblem, self).__init__(name=name)
        self.c = 0.5  # criteria factor
        self.available_constants = ['s', 'c', 'Q', 'T', 'h']  # every constants names have to be included in this list
        self.ModelName = name

        self.build_problem(data)

    def update_variable(self):
        n, r, p = self.dimensions['n'], self.dimensions['r'], self.dimensions['p']
        x = {(i, k): 1.0 if sum([get_value(self.vars['x'][i, k, l]) for l in range(p)]) > 0 else 0.0
             for i in range(n) for k in range(r)}
        y = {(i, l): get_value(self.vars['y'][i, l]) for i in range(n) for l in range(p)}
        return (x, y)

    def build_variables(self):
        """
            Build the variables of the problem from the data
        """
        n, r, p = self.dimensions['n'], self.dimensions['r'], self.dimensions['p']
        self.vars.setdefault('x', {})
        for i in range(n):
            for k in range(r):
                for l in range(p):
                    self.vars['x'][i, k, l] = self.problem.addVar(vtype=gb.GRB.BINARY, name='x[%s,%s,%s]' % (i, k, l))
        self.vars.setdefault('y', {})
        for i in range(n):
            for l in range(p):
                self.vars['y'][i, l] = self.problem.addVar(vtype=gb.GRB.BINARY, name='x[%s,%s]' % (i, l))
        return True


    def build_objectif(self):
        """ @param n, r, p: number of exams, rooms and periods
            Build the constants of the problem from the data
        """
        n, r, p = self.dimensions['n'], self.dimensions['r'], self.dimensions['p']
        obj1 = (gb.quicksum([self.vars['x'][i, k, l] * self.constants['s'][i] for i in range(n) for k in range(r) for l in range(p)]))
        obj = obj1
        self.problem.setObjective(obj, gb.GRB.MINIMIZE)
        self.problem.optimize()
        return True

    def build_constraints(self):
        """
            Build the variables of the problem from the data
        """
        n, r, p = self.dimensions['n'], self.dimensions['r'], self.dimensions['p']
        
        print("Building constraints...")
        
        # Exactly one period and one room per exam
        for i in range(n):
            constraint = (gb.quicksum([self.vars['x'][i, k, l] for k in range(r) for l in range(p)]) >= 1)
            self.problem.addConstr(constraint, "c0")
        print("built constraint c0")
            
        # Enough seat for one exam
        for i in range(n):
            constraint = (
                gb.quicksum([self.vars['x'][i, k, l] * self.constants['c'][k] for k in range(r) for l in range(p)]) >=
                self.constants['s'][i]
            )
            self.problem.addConstr(constraint, "c1")
        print("built constraint c1")
        
        # maximal one exam per room per period
        for k in range(r):
            for l in range(p):
                constraint = (gb.quicksum([self.vars['x'][i, k, l] for i in range(n)]) <= self.constants['T'][k][l])
                self.problem.addConstr(constraint, "c2")
        print("built constraint c2")
             
        # eine Prüfung, die in mehreren Räumen abgehalten wird, findet nur zu einem Zeitpunkt statt
        for i in range(n):
            for l in range(p):
                constraint = (gb.quicksum([self.vars['x'][i, k, l] for k in range(r)]) <= r*self.vars['y'][i, l])
                self.problem.addConstr(constraint, "c3")
        print("built constraint c3")
        
        for i in range(n):
            for l in range(p):
                constraint = (gb.quicksum([self.vars['x'][i, k, m] for k in range(r) for m in range(p) if m != l]) <= r*(1-self.vars['y'][i, l]))
                self.problem.addConstr(constraint, "c4")
        print("built constraint c4")
         
        # No conflicts
        for i in range(n):
            for l in range(p):
                constraint = (
                    gb.quicksum([self.constants['Q'][i][j] * self.vars['x'][j, k, l] for k in range(r) for j in range(i+1,n)]) <=
                    (1 - self.vars['y'][i, l]) * sum(self.constants['Q'][i])
                )
                self.problem.addConstr(constraint, "c5")
        print("built constraint c6")
        print("OK")
