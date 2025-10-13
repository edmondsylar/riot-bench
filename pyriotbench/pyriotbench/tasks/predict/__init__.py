"""
Predictive tasks for RIoTBench.

This module contains machine learning and predictive modeling benchmarks.

Available Tasks:
    - DecisionTreeClassify: Classification using sklearn decision trees
"""

from pyriotbench.tasks.predict.decision_tree_classify import DecisionTreeClassify

__all__ = ["DecisionTreeClassify"]
