
import itertools
import math
import datetime

import rdflib

from . import Utils

ODRL_IRI = "http://www.w3.org/ns/odrl/2/"
ODRL = rdflib.Namespace(ODRL_IRI)


class Constraint:
    def __init__(self, leftOperand=None, operator=None, rightOperand=None, **args):
        if leftOperand is None:
            LogicalConstraint.__init__(self, **args)
        else:
            ArithmeticConstraint.__init__(self, leftOperand=leftOperand, operator=operator, rightOperand=rightOperand)

    @staticmethod
    def create(leftOperand=None, operator=None, rightOperand=None, **args):
        if leftOperand is not None:
            return ArithmeticConstraint(leftOperand=leftOperand, operator=operator,
                                        rightOperand=rightOperand).normalise()
        elif "odrl:leftOperand" in args:
            left_operand = args["odrl:leftOperand"]
            operator = args["odrl:operator"]
            right_operand = args["odrl:rightOperand"]
            return ArithmeticConstraint(leftOperand=left_operand, operator=operator, rightOperand=right_operand)
        else:
            return LogicalConstraint(operator=operator, **args)

    def evaluate(self):
        pass


class Refinement(Constraint):
    def __init__(self, leftOperand=None, operator=None, rightOperand=None, **args):
        super().__init__(self, leftOperand=None, operator=None, rightOperand=None, **args)

    def evaluate(self):
        pass


class ArithmeticConstraint(Constraint):
    def __init__(self, leftOperand, operator, rightOperand):
        self.operator = operator
        self.leftOperand = leftOperand  # The specific operand that needs an exact match to proceed
        self.rightOperand = rightOperand

    def __str__(self):
        return f"({self.leftOperand} {self.operator} {self.rightOperand})"

    def __eq__(self, other):
        if isinstance(other, ArithmeticConstraint):
            return self.leftOperand == other.leftOperand and self.operator == other.operator and self.rightOperand == other.rightOperand
        else:
            return False

    def check_constraint(self, leftOperandValue, value):
        # First, check if the leftOperand matches exactly
        if self.leftOperand is not None and self.leftOperand != leftOperandValue:
            return False  # The leftOperand does not match; constraint check does not proceed

        # Proceed with the constraint checks
        if self.operator == ODRL_IRI + 'eq':
            return value == self.rightOperand
        elif self.operator == ODRL_IRI + 'gt':
            return value > self.rightOperand
        elif self.operator == ODRL_IRI + 'gteq':
            return value >= self.rightOperand
        elif self.operator == ODRL_IRI + 'lt':
            return value < self.rightOperand
        elif self.operator == ODRL_IRI + 'lteq':
            return value <= self.rightOperand
        elif self.operator == ODRL_IRI + 'neq':
            return value != self.rightOperand
        elif self.operator == ODRL_IRI + "isA":  # This will require OWL reasoning for completeness.
            return value.type == self.rightOperand
        elif self.operator == ODRL_IRI + "hasPart":
            return all(item in self.rightOperand for item in value)
        elif self.operator == ODRL_IRI + "isPartOf":
            return all(item in value for item in self.rightOperand)
        elif self.operator == ODRL_IRI + "isAllOf":
            return all(item == self.rightOperand for item in value)
        elif self.operator == ODRL_IRI + "isAnyOf":
            return any(item == self.rightOperand for item in value)
        elif self.operator == ODRL_IRI + "isNoneOf":
            return all(item != self.rightOperand for item in value)
        else:
            return False

    def normalise(self):
        if self.operator == ODRL_IRI + 'eq':
            return self
        elif self.operator == ODRL_IRI + 'gt':
            return self
        elif self.operator == ODRL_IRI + 'gteq':
            interval_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "gt", self.rightOperand)
            equality_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "eq", self.rightOperand)
            or_constraint = LogicalConstraint(operator="or", constraints=[interval_1, equality_1])
            return or_constraint
        elif self.operator == ODRL_IRI + 'lt':
            return self
        elif self.operator == ODRL_IRI + 'lteq':
            interval_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "lt", self.rightOperand)
            equality_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "eq", self.rightOperand)
            or_constraint = LogicalConstraint(operator="or", constraints=[interval_1, equality_1])
            return or_constraint
        elif self.operator == ODRL_IRI + 'neq':
            if isinstance(self.rightOperand, (int, float)):
                interval_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "gt", self.rightOperand)
                interval_2 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "lt", self.rightOperand)
                or_constraint = LogicalConstraint(operator="or", constraints=[interval_1, interval_2])
                return or_constraint
            elif isinstance(self.rightOperand, str):
                try:
                    timestamp = datetime.datetime.fromisoformat(self.rightOperand).timestamp()
                    interval_1 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "gt", timestamp)
                    interval_2 = ArithmeticConstraint(self.leftOperand, ODRL_IRI + "lt", timestamp)
                    or_constraint = LogicalConstraint(operator="or", constraints=[interval_1, interval_2])
                    return or_constraint
                except:
                    return self
            else:
                return self
        else:
            return self


    def __neg__(self):
        if self.operator == ODRL_IRI + 'eq':
            return ArithmeticConstraint(self.leftOperand, "neq", self.rightOperand)
        elif self.operator == ODRL_IRI + 'gt':
            return ArithmeticConstraint(self.leftOperand, "lteq", self.rightOperand)
        elif self.operator == ODRL_IRI + 'gteq':
            return ArithmeticConstraint(self.leftOperand, "lt", self.rightOperand)
        elif self.operator == ODRL_IRI + 'lt':
            return ArithmeticConstraint(self.leftOperand, "gteq", self.rightOperand)
        elif self.operator == ODRL_IRI + 'lteq':
            return ArithmeticConstraint(self.leftOperand, "gt", self.rightOperand)
        elif self.operator == ODRL_IRI + 'neq':
            return ArithmeticConstraint(self.leftOperand, "eq", self.rightOperand)
        else:
            return LogicalConstraint("not", [self])

    def get_values_per_left_operand(self):
        return {self.leftOperand: [self.rightOperand]}

    def split_intervals(self, value_map):
        left_operand_map = dict()
        for key in value_map.keys():  # For each left operand:
            min_value = -math.inf
            max_value = math.inf
            if self.leftOperand == key:  # Does it contain the current left operand?
                if self.operator == ODRL_IRI + "gt":
                    min_value = max(min_value, self.rightOperand)
                elif self.operator == ODRL_IRI + "lt":
                    max_value = min(max_value, self.rightOperand)
                elif self.operator == ODRL_IRI + "eq":
                    min_value = self.rightOperand
                    max_value = self.rightOperand
            if min_value == max_value:
                left_operand_map[key] = [min_value]
            elif min_value == -math.inf and max_value == math.inf:
                left_operand_map[key] = []
            else:
                left_operand_map[key] = [min_value, max_value]
        final_intervals = []
        for key in left_operand_map.keys():
            interval = left_operand_map[key]
            if len(interval) == 1:
                if len(final_intervals) == 0:
                    final_intervals.append(
                        [Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=interval[0])])
                else:
                    new_final_constraints = []
                    for c in final_intervals:
                        c_copy = c.copy()
                        c_copy.append(
                            Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=interval[0]))
                        new_final_constraints.append(c_copy)
                    final_intervals = new_final_constraints
            else:
                min_value = -math.inf
                max_value = math.inf
                if len(interval) == 2:
                    min_value = interval[0]
                    max_value = interval[1]
                key_intervals = value_map[key]
                valid_interval = [min_value] + [x for x in key_intervals if min_value < x < max_value] + [max_value]
                or_intervals = []
                if len(valid_interval) == 2:  # No values between min value and max value.
                    and_intervals = []
                    if not min_value == -math.inf:
                        and_intervals.append(
                            Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt", rightOperand=min_value))
                    if not max_value == math.inf:
                        and_intervals.append(
                            Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt", rightOperand=max_value))
                    or_intervals.append(and_intervals)
                elif len(valid_interval) > 2:
                    for i in range(len(valid_interval) - 1):
                        and_intervals = []
                        if i == 0:
                            if valid_interval[i] == -math.inf:
                                or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                       rightOperand=valid_interval[i + 1])])
                            else:
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                       rightOperand=valid_interval[i]))
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                       rightOperand=valid_interval[i + 1]))
                                or_intervals.append(and_intervals)

                        elif i == len(valid_interval) - 2:
                            if valid_interval[i + 1] == math.inf:
                                or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                       rightOperand=valid_interval[i])])
                            else:
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                       rightOperand=valid_interval[i]))
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                       rightOperand=valid_interval[i + 1]))
                                or_intervals.append(and_intervals)
                            or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq",
                                                                   rightOperand=valid_interval[i])])

                            break
                        else:
                            and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                   rightOperand=valid_interval[i]))
                            and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                   rightOperand=valid_interval[i + 1]))
                            or_intervals.append(and_intervals)
                            or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq",
                                                                   rightOperand=valid_interval[i])])
                if len(final_intervals) == 0:
                    for interval in or_intervals:
                        final_intervals.append(interval)
                else:
                    new_final_constraints = []
                    for c in final_intervals:
                        for or_interval in or_intervals:
                            new_final_constraints.append(c + or_interval)
                    final_intervals = new_final_constraints
        return Constraint.create(operator="or", constraints=final_intervals)
    
    def to_triples(self, subject):
        if self.leftOperand == ODRL_IRI + "dateTime":
            proper_datetime = datetime.datetime.fromtimestamp(self.rightOperand, tz=datetime.timezone.utc).isoformat()
            return [(subject, ODRL.leftOperand, Utils.string_to_rdflib_node(self.leftOperand)), (subject, ODRL.operator, Utils.string_to_rdflib_node(self.operator)),
                (subject, ODRL.rightOperand, Utils.string_to_rdflib_node(proper_datetime))]
        else:
            return [(subject, ODRL.leftOperand, Utils.string_to_rdflib_node(self.leftOperand)), (subject, ODRL.operator, Utils.string_to_rdflib_node(self.operator)),
                (subject, ODRL.rightOperand, Utils.string_to_rdflib_node(self.rightOperand))]


class LogicalConstraint(Constraint):
    def __init__(self, operator=None, constraints=None, **args):
        if operator is None:
            if (ODRL_IRI + 'and') in args:
                op = 'and'
            elif (ODRL_IRI + 'or') in args:
                op = 'or'
            elif (ODRL_IRI + 'xor') in args:
                op = 'xor'
            elif (ODRL_IRI + 'andSequence') in args:
                op = 'andSequence'
            else:
                op = operator
            constraint = args[op]
            if isinstance(constraint, list):
                self.constraints = [Constraint.create(**c) for c in constraint]
            elif isinstance(constraint, dict):
                self.constraints = [Constraint.create(**constraint)]
            self.operator = op
        else:
            self.operator = operator
            self.constraints = constraints

    def __str__(self):
        list_to_string = ""
        for constraint in self.constraints:
            list_to_string += str(constraint) + " "
        list_to_string = list_to_string[:-1]
        return "(" + str(self.operator) + " " + list_to_string + ")"

    def __eq__(self, other):
        if isinstance(other, LogicalConstraint):
            if self.operator == other.operator and len(self.constraints) == len(other.constraints):
                for constraint in self.constraints:
                    if constraint not in other.constraints:
                        return False
                for constraint in other.constraints:
                    if constraint not in self.constraints:
                        return False
                return True
        return False

    def check_constraint(self, value):
        if self.operator == 'or':
            return any(constraint.check_constraint(None, value) for constraint in self.constraints)
        elif self.operator == 'xone':
            return sum(constraint.check_constraint(None, value) for constraint in self.constraints) == 1
        elif self.operator == 'and':
            return all(constraint.check_constraint(None, value) for constraint in self.constraints)
        elif self.operator == 'andSequence':
            results = [constraint.check_constraint(None, value) for constraint in self.constraints]
            return all(results) and results == sorted(results, reverse=True)
        else:
            return False

    def normalise(self):
        sub_constraints = []
        if self.operator == 'or':
            for constraint in self.constraints:
                normal_constraint = constraint.normalise()
                if isinstance(normal_constraint, ArithmeticConstraint):
                    sub_constraints.append(normal_constraint)
                elif isinstance(normal_constraint, LogicalConstraint):
                    if normal_constraint.operator == 'or':
                        for c in normal_constraint.constraints:
                            sub_constraints.append(c)
                    elif normal_constraint.operator == 'and':
                        sub_constraints.append(normal_constraint)
            return LogicalConstraint(operator=self.operator, constraints=sub_constraints)
        elif self.operator == 'and':
            union_constraints = []
            final_constraints = []
            for constraint in self.constraints:
                normal_constraint = constraint.normalise()
                if isinstance(normal_constraint, LogicalConstraint):
                    if normal_constraint.operator == 'or':
                        union_constraints.append(normal_constraint.constraints)
                    elif normal_constraint.operator == 'and':
                        for c in normal_constraint.constraints:
                            sub_constraints.append(c)
                else:
                    sub_constraints.append(normal_constraint)
            if len(union_constraints) == 0:
                return LogicalConstraint(operator=self.operator, constraints=sub_constraints)
            cartesian_product = itertools.product(*union_constraints)
            for e in cartesian_product:
                temp_constraint = list(e)
                for sub_constraint in sub_constraints:
                    temp_constraint.append(sub_constraint)
                final_constraint = LogicalConstraint("and", temp_constraint)
                final_constraints.append(final_constraint.normalise())
            return LogicalConstraint(operator="or", constraints=final_constraints)

    def get_values_per_left_operand(self):
        ans = dict()
        for constraint in self.constraints:
            sub_ans = constraint.get_values_per_left_operand()
            for key in sub_ans.keys():
                if key in ans:
                    ans[key] += sub_ans[key]
                else:
                    ans[key] = sub_ans[key]
        return ans

    def simplify_intervals(self):
        if self.operator == "and":
            simplified_intervals = []
            key_map = dict()
            for constraint in self.constraints:
                if constraint.operator == ODRL_IRI + "lt" or constraint.operator == ODRL_IRI + "gt" or constraint.operator == ODRL_IRI + "eq":
                    if constraint.leftOperand not in key_map:
                        key_map[constraint.leftOperand] = []
                    key_map[constraint.leftOperand].append(constraint)
                else:
                    simplified_intervals.append(constraint)
            for key in key_map.keys():
                min_value = -math.inf
                max_value = math.inf
                exact_value = None
                for constraint in key_map[key]:
                    if isinstance(constraint.rightOperand, str):
                        try:
                            constraint.rightOperand = datetime.datetime.fromisoformat(constraint.rightOperand).timestamp()
                        except ValueError:
                            constraint.rightOperand = constraint.rightOperand
                    if constraint.operator == ODRL_IRI + "eq":
                        if exact_value is None:
                            exact_value = constraint.rightOperand
                        elif exact_value != constraint.rightOperand:
                            # raise ValueError("More than one equality per left operand.")
                            return None
                    elif constraint.operator == ODRL_IRI + "gt":
                        if min_value == -math.inf:
                            min_value = constraint.rightOperand
                        else:
                            min_value = max(constraint.rightOperand, min_value)
                    elif constraint.operator == ODRL_IRI + "lt":
                        if max_value == math.inf:
                            max_value = constraint.rightOperand
                        else:
                            max_value = min(constraint.rightOperand, max_value)
                if exact_value is not None:
                    if max_value == math.inf and min_value == -math.inf:
                        simplified_intervals.append(
                            Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=exact_value))
                    elif max_value > exact_value > min_value:
                        simplified_intervals.append(
                            Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=exact_value))
                elif min_value < max_value:
                    if min_value != -math.inf:
                        interval_1 = ArithmeticConstraint(key, ODRL_IRI + "gt", min_value)
                        simplified_intervals.append(interval_1)
                    if max_value != math.inf:
                        interval_2 = ArithmeticConstraint(key, ODRL_IRI + "lt", max_value)
                        simplified_intervals.append(interval_2)
                else:
                    # raise ValueError("Invalid interval. Minimum value is greater than maximum value.")
                    return None
            return LogicalConstraint(operator="and", constraints=simplified_intervals)
        elif self.operator == "or":
            simplified_intervals = []
            for constraint in self.constraints:
                if isinstance(constraint, LogicalConstraint):
                    if constraint.simplify_intervals() is not None:
                        simplified_intervals.append(constraint.simplify_intervals())
                else:
                    simplified_intervals.append(constraint)
            return LogicalConstraint(operator="or", constraints=simplified_intervals)
        
    def to_triples(self, subject):
        triples = []
        for constraint in self.constraints:
            constraint_bnode = rdflib.BNode()
            triples.append((subject, ODRL.operator, constraint_bnode))
            triples.extend(constraint.to_triples(constraint_bnode))
        return triples

    # def split_intervals(self, value_map):
    #     #Note that this will only work correctly if this is a CQ.
    #     if self.operator == "and":
    #         replaced_constraints = set()
    #         final_constraints = []
    #         for key in value_map.keys():  # For each left operand:
    #             key_intervals = value_map[key]
    #             min_value = -math.inf
    #             max_value = math.inf
    #             or_intervals = []
    #             contains_key = False
    #             is_interval = False
    #             for c in self.constraints:  # For each constraint in this list of constraints.
    #                 if c.leftOperand == key:  # Does it contain the current left operand?
    #                     if c.operator == ODRL_IRI + "gt":
    #                         min_value = max(min_value, c.rightOperand)
    #                         contains_key = True
    #                         is_interval = True
    #                     elif c.operator == ODRL_IRI + "lt":
    #                         max_value = min(max_value, c.rightOperand)
    #                         contains_key = True
    #                         is_interval = True
    #                     elif c.operator == ODRL_IRI + "eq":
    #                         min_value = c.rightOperand
    #                         max_value = c.rightOperand
    #                         contains_key = True
    #                     else:
    #                         replaced_constraints.add(c)
    #             if is_interval:  # If this contains an inequality, this defines an interval.
    #                 if len(key_intervals) == 1:  # Only one inequality, so it must be < or >.
    #                     if not min_value == -math.inf:
    #                         or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
    #                                                                rightOperand=min_value)])
    #                     elif not max_value == math.inf:
    #                         or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
    #                                                                rightOperand=max_value)])
    #                 elif len(key_intervals) > 1:  # Two or more inequalities, so we can reduce it to an interval.
    #                     for i in range(len(key_intervals) - 1):
    #                         and_intervals = []
    #                         if key_intervals[i] < min_value:
    #                             continue
    #                         if key_intervals[i] >= max_value:  # Left the interval.
    #                             if not max_value == math.inf:
    #                                 and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
    #                                                                        rightOperand=key_intervals[i]))
    #                             break
    #                         else:
    #                             if i == 0:  # If it's the first value.
    #                                 if min_value == -math.inf:
    #                                     or_intervals.append(
    #                                         [Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
    #                                                            rightOperand=key_intervals[i])])
    #                             and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
    #                                                                    rightOperand=key_intervals[i]))
    #                             and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
    #                                                                    rightOperand=key_intervals[i + 1]))
    #                             or_intervals.append(and_intervals)
    #                             if i == len(key_intervals) - 2:
    #                                 if max_value == math.inf:
    #                                     or_intervals.append(
    #                                         [Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
    #                                                            rightOperand=key_intervals[i + 1])])
    #                                 break
    #                 if len(final_constraints) == 0:
    #                     for interval in or_intervals:
    #                         final_constraints.append(interval)
    #                 else:
    #                     new_final_constraints = []
    #                     for c in final_constraints:
    #                         for or_interval in or_intervals:
    #                             new_final_constraints.append(c + or_interval)
    #                     final_constraints = new_final_constraints
    #             else:  # Unless we do this part, overlap can happen.
    #                 for value in key_intervals:
    #                     any_constraint = Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=value)
    #                     not_any_constraint = Constraint.create(leftOperand=key, operator=ODRL_IRI + "neq", rightOperand=value)
    #                     or_intervals.append(Constraint.create(operator="or", constraints=[any_constraint, not_any_constraint]))
    #                     if len(final_constraints) == 0:
    #                         final_constraints.append([any_constraint])
    #                         final_constraints.append([not_any_constraint])
    #                     else:
    #                         new_final_constraints = []
    #                         for c in final_constraints:
    #                             c1 = c.copy()
    #                             c1.append(any_constraint)
    #                             c2 = c.copy()
    #                             c2.append(not_any_constraint)
    #                             new_final_constraints.append(c1)
    #                             new_final_constraints.append(c2)
    #                         final_constraints = new_final_constraints
    #         split_constraints = []
    #         for sub_constraints in final_constraints:
    #             sub_constraints.extend(replaced_constraints)
    #             split_constraints.append(LogicalConstraint(operator="and", constraints=sub_constraints))
    #         return LogicalConstraint(operator="or", constraints=split_constraints)
    #     return self

    def split_intervals(self, value_map):
        #Note that this will only work correctly if this is a CQ.
        if self.operator == "and":
            left_operand_map = dict()
            for key in value_map.keys():  # For each left operand:
                min_value = -math.inf
                max_value = math.inf
                for c in self.constraints:  # For each constraint in this list of constraints.
                    if c.leftOperand == key:  # Does it contain the current left operand?
                        if c.operator == ODRL_IRI + "gt":
                            min_value = max(min_value, c.rightOperand)
                        elif c.operator == ODRL_IRI + "lt":
                            max_value = min(max_value, c.rightOperand)
                        elif c.operator == ODRL_IRI + "eq":
                            min_value = c.rightOperand
                            max_value = c.rightOperand
                if min_value == max_value:
                    left_operand_map[key] = [min_value]
                elif min_value == -math.inf and max_value == math.inf:
                    left_operand_map[key] = []
                else:
                    left_operand_map[key] = [min_value, max_value]
            final_intervals = []
            for key in left_operand_map.keys():
                interval = left_operand_map[key]
                if len(interval) == 1:
                    if len(final_intervals) == 0:
                        final_intervals.append(
                            [Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=interval[0])])
                    else:
                        new_final_constraints = []
                        for c in final_intervals:
                            c_copy = c.copy()
                            c_copy.append(
                                Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq", rightOperand=interval[0]))
                            new_final_constraints.append(c_copy)
                        final_intervals = new_final_constraints
                else:
                    min_value = -math.inf
                    max_value = math.inf
                    if len(interval) == 2:
                        min_value = interval[0]
                        max_value = interval[1]
                    key_intervals = value_map[key]
                    valid_interval = [min_value] + [x for x in key_intervals if min_value < x < max_value] + [max_value]
                    or_intervals = []
                    if len(valid_interval) == 2:  #  No values between min value and max value.
                        and_intervals = []
                        if not min_value == -math.inf:
                            and_intervals.append(
                                Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt", rightOperand=min_value))
                        if not max_value == math.inf:
                            and_intervals.append(
                                Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt", rightOperand=max_value))
                        or_intervals.append(and_intervals)
                    elif len(valid_interval) > 2:
                        for i in range(len(valid_interval) - 1):
                            and_intervals = []
                            if i == 0:
                                if valid_interval[i] == -math.inf:
                                    or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                           rightOperand=valid_interval[i + 1])])
                                else:
                                    and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                           rightOperand=valid_interval[i]))
                                    and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                           rightOperand=valid_interval[i + 1]))
                                    or_intervals.append(and_intervals)

                            elif i == len(valid_interval) - 2:
                                if valid_interval[i + 1] == math.inf:
                                    or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                           rightOperand=valid_interval[i])])
                                else:
                                    and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                           rightOperand=valid_interval[i]))
                                    and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                           rightOperand=valid_interval[i + 1]))
                                    or_intervals.append(and_intervals)
                                or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq",
                                                                       rightOperand=valid_interval[i])])

                                break
                            else:
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "gt",
                                                                       rightOperand=valid_interval[i]))
                                and_intervals.append(Constraint.create(leftOperand=key, operator=ODRL_IRI + "lt",
                                                                       rightOperand=valid_interval[i + 1]))
                                or_intervals.append(and_intervals)
                                or_intervals.append([Constraint.create(leftOperand=key, operator=ODRL_IRI + "eq",
                                                                       rightOperand=valid_interval[i])])
                    if len(final_intervals) == 0:
                        for interval in or_intervals:
                            final_intervals.append(interval)
                    else:
                        new_final_constraints = []
                        for c in final_intervals:
                            for or_interval in or_intervals:
                                new_final_constraints.append(c + or_interval)
                        final_intervals = new_final_constraints
            return Constraint.create(operator="or", constraints=final_intervals)
        return self
