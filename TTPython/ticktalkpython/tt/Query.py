# Copyright 2021 Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
TTPython Device Query Interface

Given an Ensemble or EnsembleSet, a programmer needs a method to extract individual ``Ensemble.TTEnsemble``s and ``TTComponent``s.
This can be done with two objects–''TTQuery'' and ''TTQueryCondition''-and their derivatives.  A ``TTQueryCondition`` is a wrapper
around a singular attribute of an Ensemble or Component, restricting it to a particular value or subset of values. A ``TTQuery`` is a set of
``TTQueryCondition``s and a "target" ``Ensemble.TTEnsemble``or ``TTComponent`` object on which they are evaluated.
Queries can inherit their "target" from other queries, allowing for nesting, joining, and disjoining.
'''

from Error import TTQueryError
from Component import TTComponent
import Ensemble

from enum import Enum

class TTConstraint():
    def __init__(self, name = [], components = []):
        self.name = name
        self.components = components

class QueryOp(Enum):
    OR = 1
    AND = 2


class TTQueryCondition:
    '''
    Given that various types of conditions may structure themselves around values in different ways,
    the only guaranteed attribute of a ``TTQueryCondition`` is its ability to be tested against a particular value.
    '''
    def __init__(self):
        pass
    def test(self, value):
        '''
        :param value: The value against which this condition will be tested.
        :type value: any
        :return: result of the query
        :rtype: bool
        '''
        pass

class TTQueryConditionRange(TTQueryCondition):
    '''
    ``TTQueryConditionRange`` indicates whether a given value is within an inclusive bounds.

    :param min: The inclusive minimum of the range
    :type min: float

    :param max: The inclusive maximum of the range
    :type max: float
    '''
    def __init__(self, min, max):
        super().__init__()
        if(type(min) != float or type(max) != float):
            raise TTQueryError("The bounds of a range must be of type float.")
        if(min is None and max is None):
            raise TTQueryError("A range must have at least one inclusive endpoint.")
        self.min = min
        self.max = max

    def test(self, value):
        '''
        Test if a given value is within the range.
        A range with a single defined boundary defaults to
        checking if the value is less than or equal to, or greater than or equal to,
        the given boundary

        :param value: a value to test against the range
        :type value: float

        :return: if the value was found to be within [min, max]
        :rtype: bool
        '''
        if(self.min is not None):
            if(self.max is not None):
                return value in __builtins__.range(min, max)
            else:
                return value >= self.min
        else:
            return value <= self.max

def within(min, max):
    '''
    A shorthand form of the ``TTQueryConditionRange`` constructor for use in complex queries.

    :param min: The inclusive minimum of the range
    :type min: float

    :param max: The inclusive maximum of the range
    :type max: float

    :return: a range condition corresponding to [min, max]
    :rtype: TTQueryConditionRange
    '''
    return TTQueryConditionRange(min, max)

def leq(max):
    '''
    A shorthand form of the ``TTQueryConditionRange`` constructor for use in complex queries.

    :param max: The inclusive maximum of the range
    :type max: float

    :return: a range condition corresponding to [-infinity, max]
    :rtype: TTQueryConditionRange
    '''
    return TTQueryConditionRange(None, max)

def geq(min):
    '''
    A shorthand form of the ``TTQueryConditionRange`` constructor for use in complex queries.

    :param min: The inclusive minimum of the range
    :type min: float

    :return: a range condition corresponding to [min, +infinity]
    :rtype: TTQueryConditionRange
    '''
    return TTQueryConditionRange(min, None)

class TTQueryConditionExclude(TTQueryCondition):
    '''
    ``TTQueryConditionExclude`` indicates whether a given value is excluded from a mixed set of values and conditions.

    :param value_conditions: a set of values and ``TTQueryCondition``s to test against a given value.
    :type value_conditions: tuple

    '''
    def __init__(self, *value_conditions):
        super().__init__()
        self.subconditions = value_conditions

    def test(self, value):
        '''
        Check if the given value is excluded from the set of subconditions. If a subcondition is a ``TTQueryCondition``,
        it's ``test`` function is called on the given value. Other types of conditions are checked for equality.

        :param value: the value to test against the set
        :type value: any

        :return: if the given value was excluded from all subconditions.
        :rtype: bool
        '''
        for condition in self.subconditions:
            if(isinstance(condition, TTQueryCondition)):
                if(condition.test(value)): return False
            else:
                if(condition == value): return False
        return True

def excluding(*conditions):
    '''
    A shorthand form of the ``TTQueryConditionExclude`` constructor for use in complex queries.

    :param value_conditions: a set of values and ``TTQueryCondition``s to test against a given value.
    :type value_conditions: tuple

    :return: an exclude condition corresponding to the set of conditions
    :rtype: TTQueryConditionExclude

    '''
    return TTQueryConditionExclude(conditions)


class TTQCEnsembleName(TTQueryCondition):
    '''
    A ``TTQueryName`` is a ``TTQuery`` for a ``Ensemble.TTEnsemble`` with a given name.

    :param condition: the name of the ``Ensemble.TTEnsemble`` to be queried for.
    :type condition: string
    '''
    def __init__(self, name):
        self.name = name

    def test(self, ens):
        '''
        Tests if the given ``Ensemble.TTEnsemble`` has a matching name.

        :param query_object: the ``Ensemble.TTEnsemble`` to be tested
        :type query_object: ``Ensemble.TTEnsemble``
        '''
        super().test(ens)
        if (not isinstance(ens, Ensemble.TTEnsemble)):
            raise TTQueryError(
                "Expected the queried object to be of type Ensemble.TTEnsemble.")
        return self.name == ens.name


def ensembleName(condition):
    '''
    A shorthand form of TTQueryName for use in complex queries.

    :param condition: the name of the ``Ensemble.TTEnsemble`` to be queried for.
    :type condition: string

    :return: a query for a ``Ensemble.TTEnsemble`` with the given name
    :rtype: ``TTQCEnsembleName``
    '''

    return TTQCEnsembleName(condition)


class TTQCComponentName(TTQueryCondition):
    '''
    A ``TTQCComponentName`` is a ``TTQueryCondition`` for a ``TTComponent`` with a given name.

    :param condition: the name of the ``Ensemble.TTEnsemble`` or ``TTComponent`` to be queried for.
    :type condition: string
    '''
    def __init__(self, name):
        self.name = name

    def test(self, query_object):
        '''
        Tests if the given ``TTComponent``  has a matching name.

        :param query_object: the ``TTComponent`` or ``Ensemble.TTEnsemble`` to be tested
        :type query_object: ``TTComponent`` | ``Ensemble.TTEnsemble``
        '''
        super().test(query_object)
        if (not (isinstance(query_object, TTComponent)
                 or isinstance(query_object, Ensemble.TTEnsemble))):
            raise TTQueryError(
                "Expected the queried object to be of type Ensemble.TTEnsemble or TTComponent."
            )
        if isinstance(query_object, Ensemble.TTEnsemble):
            return self.name in query_object.component_name_map
        if isinstance(query_object, TTComponent):
            return self.name == query_object.name

    def __repr__(self):
        return f"TTQCComponentName: {self.name}"

    def json(self):
        return {'hasComponentName': self.name}


def componentName(condition):
    '''
    A shorthand form of TTQueryName for use in complex queries.

    :param condition: the name of the ``TTComponent`` to be queried for.
    :type condition: string

    :return: a query for a ``TTComponent`` with the given name
    :rtype: ``TTQueryName``
    '''

    return TTQCComponentName(condition)


class TTQuery():
    '''
    A ``TTQuery`` is a set of conditions to be evaluated against a given TTComponent or Ensemble.TTEnsemble. The term
    'conditions' is used to refer to any value; ``TTQueryCondition``s are evaluated using their ``test``
    functions, and all other types are checked for equality.

    :param conditions: the set of values and ``TTQueryCondition``s composing the query.
    :type conditions: tuple
    '''
    def __init__(self, conditions, op):
        self.conditions = conditions
        self.op = op

    def test(self, query_object):
        '''
        Ensures that the given object is of type ``TTComponent`` or ``Ensemble.TTEnsemble``.

        :param query_object: The ``TTComponent`` or ``Ensemble.TTEnsemble`` queried against.
        :type query_object: ``TTComponent`` | ``Ensemble.TTEnsemble``
        '''
        if(not (isinstance(query_object, TTComponent) or isinstance(query_object, Ensemble.TTEnsemble))):
            raise TTQueryError("Expected the queried object to be of type Ensemble.TTEnsemble or TTComponent.")

        logical_list = [c.test(query_object) for c in self.conditions]

        if self.op == QueryOp.AND:
            return not False in logical_list
        elif self.op == QueryOp.OR:
            return True in logical_list
        else:
            raise TTQueryError("Unexpected query operator.")


class TTEnsembleQuery(TTQuery):
    '''
    A ``TTEnsembleQuery`` is a ``TTQuery`` for exclusive use with ``Ensemble.TTEnsemble`` objects.

    :param conditions: the set of values and ``TTQueryCondition``s composing the query.
    :type conditions: tuple
    '''
    def __init__(self, *conditions):
        super().__init__(*conditions)

    def test(self, ensemble):
        if(not isinstance(ensemble, Ensemble.TTEnsemble)):
            raise TTQueryError("Expected 'component' to be of type Ensemble.TTEnsemble.")

class TTQComponent(TTQuery):
    def __init__(self, *conditions):
        super().__init__(*conditions)
    def test(self, component):
        if(not isinstance(component, TTComponent)):
            raise TTQueryError("Expected 'component' to be of type Ensemble.TTComponent.")


class TTQComponentCustomField(TTQComponent):
    def __init__(self, key, condition):
        super().__init__(condition)
        self.key = key
    def test(self, component):
        super().test(component)
        return self.condition.test(component.getCustomField(self.key))

def custom(key, condition):
    return TTQComponentCustomField(key, condition)
