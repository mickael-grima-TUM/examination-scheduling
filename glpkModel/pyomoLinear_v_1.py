
from __future__ import division 

import sys
import os
PATHS = os.getcwd().split('/')
PROJECT_PATH = ''
for p in PATHS:
    PROJECT_PATH += '%s/' % p
    if p == 'examination-scheduling':
        break
sys.path.append(PROJECT_PATH)

import itertools
import random
import networkx as nx
import math 
from time import time
    
import pyomo.environ as pymo

from gurobipy import Model, quicksum, GRB, GurobiError
from model.instance import build_random_data

'''

        -Model GurobiLinear_v_3 has fewer variables since it doesnt create x_(i,k,l) if room k is closed in period l
        -Model GurobiLinear_v_4_Cliques adds Clique constraints for conflicts only one exam in a clique conflict can take place at a time
        -Model GurobiLinear_v_4_Cliques changed r in BIG-M-Method  to 12 so far

'''

'''
        ***************  POSSIBLE IMPROVEMENTS    ***************
        
        -Add an option that such that courses in Garching are only schedule in rooms in Garchin and vice versa -> Removes lots of variables
        -Change in "c6: any multi room exam takes place at one moment in time" the r in big M-Method from r to min{10, ceil(si/75)} or similiar [to discuss]
        -Idea for linking variables x and y
                *c1b creates l*i constraints this could be reduced to only i constraints
                *reason
                        +"c1a" says if one exam takes place in some period than y_i,l cannot be zero 
                        + then constraint c2 forces all other y_i,l to be 0 anyway
                        + now say for all i sum(x_i,k,l for all k and for all l) >= 1 this forces at least one y_i,l to be 1 - this only has i constraints but more columns
'''

# def find_smallest_room_to_fit_in(**kwords):
#     n,s,r,c = kwords.get('n', 1), kwords.get('s', 1), kwords.get('r', 1), kwords.get('c', 1)   

#     sR = [r+1 for i in range(n)]

#     for i in range(n):
#         for l in range(r):
#             if s[i] <= c[l]:
#                 sR[i] = l

#     return sR
             

    
def build_model(data, n_cliques = 0):
    
    # Load Data Format
    n = data['n']
    r = data['r']
    p = data['p']
    s = data['s']
    c = data['c']
    h = data['h']
    conflicts = data['conflicts']
    locking_times = data['locking_times']
    T = data['T']
    # sR = find_smallest_room_to_fit_in(n=n,s=s,r=r,c=c)
    #print sR
    
    model = pymo.AbstractModel()
    
    print("Building variables...")
    model.n = pymo.Param(initialize = n)
    model.r = pymo.Param(initialize = r)
    model.p = pymo.Param(initialize = p)
    
    model.N = pymo.RangeSet(1, model.n)
    model.R = pymo.RangeSet(1, model.r)
    model.P = pymo.RangeSet(1, model.p)
    
    model.NxN = model.N * model.N
    model.NxP = model.N * model.P
    model.RxP = model.R * model.P
    model.NxRxP = model.N * model.RxP
    
    model.s = pymo.Param(model.N, initialize=lambda m, i: s[i-1])
    model.c = pymo.Param(model.R, initialize=lambda m, k: c[k-1])
    model.h = pymo.Param(model.P, initialize=lambda m, l: h[l-1])
    model.H = pymo.Param(initialize=h[len(h)-1])
    
    model.conflicts = pymo.Set(model.NxN, filter = lambda i, j: j in conflicts)
    model.cliques = pymo.RangeSet(1, n_cliques)
    model.cxP = model.cliques * model.P
     
    model.x = pymo.Var(model.NxRxP, domain=pymo.Binary)
    model.y = pymo.Var(model.NxP, domain=pymo.Binary)
    
    print("c1: connecting variables x and y")
    def c1a(m, i, l):
        return 
    def c1b(m, i, l):
        return 
    model.cons_1a = pymo.Constraint(model.NxP, rule=lambda m, i, l: sum(m.x[i, k, l] for k in m.R) <= m.r * m.y[i,l])
    model.cons_1b = pymo.Constraint(model.NxP, rule=lambda m, i, l: sum(m.x[i, k, l] for k in m.R) >= m.y[i,l])
    model.cons_1a_v = lambda m, i, l: sum(m.x[i, k, l].value for k in m.R) <= m.r * m.y[i,l].value
    model.cons_1b_v = lambda m, i, l: sum(m.x[i, k, l].value for k in m.R) >= m.y[i,l].value
    
    print("c2: each exam at exactly one time")
    model.cons_2 = pymo.Constraint(model.N, rule=lambda m, i: sum(m.y[i,l] for l in m.P) == 1)
    model.cons_2_v = lambda m, i: sum(m.y[i,l].value for l in m.P) == 1
    
    print("c3: avoiding conflicts")
    def c3(m, i, l):
        if sum(m.y[j,l] for j in conflicts[i]) <= (1 - m.y[i,l]) * sum(conflicts[i]):
            return pymo.Constraint.Feasible
    model.cons_3 = pymo.Constraint(model.NxP, rule=c3)
    model.cons_3_v = lambda m, i, l: sum(m.y[j,l].value for j in conflicts[i]) <= (1 - m.y[i,l].value) * sum(conflicts[i])
    
    print("c4: seats for all students")
    model.cons_4 = pymo.Constraint(model.N, rule=lambda m, i: sum(m.x[i,k,l] * m.c[k] for (k,l) in m.RxP) >= m.s[i])
    model.cons_4_v = lambda m, i: sum(m.x[i,k,l].value * m.c[k] for (k,l) in m.RxP) >= m.s[i]
    
    print("c5: only one exam per room per period")
    def c5(m, k, l):
        return 
    model.cons_5 = pymo.Constraint(model.RxP, rule= lambda m, k, l: sum(m.x[i,k,l] for i in m.N) <= 1 )
    model.cons_5_v = lambda m, k, l: sum(m.x[i,k,l].value for i in m.N) <= 1 
    
    #"""
    #Idea:   -instead of saving a conflict Matrix, save Cliques of exams that cannot be written at the same time
            #-then instead of saying of one exam is written in a given period all conflicts cannot be written in the same period we could say
            #-for all exams in a given clique only one can be written
    #"""
    
    print("c7: Building %d clique constraints" %n_cliques)
    if n_cliques > 0:
        G = nx.Graph()
        for i in range(n):
            G.add_node(i)  
        for i in range(n):
            for j in conflicts[i]:
                G.add_edge(i,j)
        
        cliques = [] # generator
        counter = 0
        for clique in nx.find_cliques(G):
            if counter >= n_cliques:
                break
            cliques.append(clique)
            counter += 1
        #for clique in cliques:
            #print clique
        #print("____")
        #print(len(cliques))
        
        def c3(m, i, l):
            return sum([m.y[j+1,l] for j in cliques[i-1]]) <= 1
                
        model.cons_7 = pymo.Constraint(model.cxP, rule=c3)
        
    
    print("Building Objective...")
    model.OBJ = pymo.Objective(sense=pymo.minimize, rule = lambda m: sum(m.x[i,k,l] for i,k,l in m.NxRxP))
    model.OBJ_v = lambda m: sum(m.x[i,k,l].value/m.s[i] for i,k,l in m.NxRxP)
    
    print("Creating instance...")
    instance = model.create_instance()
    
    print("OK - Model built")
    return(instance)

from pyomo.opt import SolverFactory
from pyomo.core import Constraint
    
# check if model has integer solution
# NOTE: load results into the model!!
def is_integer_solution(model):
    val_x = [model.x[i,k,l].value for (i,k,l) in model.NxRxP]
    val_y = [model.y[i,l].value for (i,l) in model.NxP]
    return all(v == round(v) for v in val_x + val_y)

def schedule_exams(data, solver_name="gurobi", n_cliques=0, print_results=False):
    
    optimizer = SolverFactory(solver_name)
    
    if solver_name == "gurobi":
        optimizer.options["threads"] = 1
        optimizer.options["--solver-suffixes"] = ".*"
    print optimizer.options
    
    t = time()
    instance = build_model(data, n_cliques = 0)        
    print("Solving...")
    results = optimizer.solve(instance)
    t = time() - t   
    
    instance.solutions.load_from(results)
    x = [instance.x[i,k,l].value for (i,k,l) in instance.NxRxP]
    y = [instance.y[i,l].value for (i,l) in instance.NxP]
    objVal = instance.OBJ_v(instance)
    
    if is_integer_solution(instance):
        print "All integer solution!"
        x = map(int, x)
        y = map(int, y)
        
    objVal = sum(x)
    
    if print_results:
        print instance.display()
    print (results)
        
    return instance, x, y, objVal, t

    
if __name__ == "__main__":
    
    n = 170
    r = 20
    p = 10

    # generate data
    random.seed(42)
    data = build_random_data(n=n, r=r, p=p, prob_conflicts=0.5)
    exams = [ 'Ana%s' % (i+1) for i in range(n) ]
    rooms = ['MI%s' % (k+1) for k in range(r)]
    
    model, x, y, objVal, t = schedule_exams(data, n_cliques=0, solver_name = "gurobi")
    
    model2, x2, y2, objVal2, t2 = schedule_exams(data, n_cliques=0, solver_name = "glpk")
    
    print('Runtime: %0.2f s' % t)
    print('Runtime: %0.2f s' % t2)
    
    index_y = ["[%d,%d]" %(i,l) for (i,l) in model.NxP if model.y[i,l].value == 1]
    index_y2 = ["[%d,%d]" %(i,l) for (i,l) in model2.NxP if model2.y[i,l].value == 1]
    
    #print all([ y[i] == y2[i] for i in range(len(y))])
    #print all([ x[i] == x2[i] for i in range(len(x))])
    
    print objVal
    print objVal2