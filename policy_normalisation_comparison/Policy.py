"""
Author: Semih Yumuşak
Date: July 24, 2024
Description: This is file containing Policy and rule classes.

Contributors:
Jaime Osvaldo Salas
Added normalisation methods.
"""
from typing import Union, Optional

from rdflib import BNode

from . import Utils
from .Refinables import Action, AssetCollection, PartyCollection
from .Constraint import Constraint, LogicalConstraint, ArithmeticConstraint


class Rule:
    def __init__(self, action: Action = None, target: AssetCollection = None,
                 assigner: Union[PartyCollection, None] = None, assignee: Union[PartyCollection, None] = None,
                 constraint: list[Union[Constraint, 'LogicalConstraint', 'ArithmeticConstraint']] = None,
                 uid: str = None):

        """
        Initializes a Rule instance.

        :param action: The action associated with the Rule.
        :param target: Optional; the target AssetCollection associated with the Rule.
        :param assigner: Optional; the assigner PartyCollection associated with the Rule.
        :param assignee: Optional; the assignee PartyCollection associated with the Rule.
        :param constraints: Optional list of Constraint or LogicalConstraint objects associated with the Rule.
        :param uid: Optional; the unique identifier of the Rule.
        """

        if isinstance(action, dict):
            self.action = [Action(**action)]
        elif action is None:
            self.action = []
        else:
            self.action = action

        if isinstance(target, dict):
            self.target = AssetCollection(**target)
        elif target is None:
            self.target = []
        else:
            self.target = target

        if isinstance(assigner, dict):
            self.assigner = PartyCollection(**assigner)
        elif assigner is None:
            self.assigner = []
        else:
            self.assigner = assigner

        if isinstance(assignee, dict):
            self.assignee = PartyCollection(**assignee)
        elif assignee is None:
            self.assignee = []
        else:
            self.assignee = assignee

        self.constraint = []
        if isinstance(constraint, list):
            self.constraint = constraint
        elif isinstance(constraint, dict):
            if "odrl:leftOperand" in constraint:
                left_operand = constraint["odrl:leftOperand"]
                operator = constraint["odrl:operator"]
                right_operand = constraint["odrl:rightOperand"]
                self.constraint.append(
                    Constraint.create(leftOperand=left_operand, operator=operator, rightOperand=right_operand))
            else:
                self.constraint.append(Constraint.create(constraint))

        self.type = type
        self.uid = uid
        self.state = "Inactive"  # Default state is Inactive

    def __str__(self):
        ans = f"""
        action: {"".join(str(action) for action in self.action)}
        target: {"".join(str(target) for target in self.target)}
        assignee: {"".join(str(assignee) for assignee in self.assignee)}
        assigner: {"".join(str(assigner) for assigner in self.assigner)}
        constraints: {"".join(str(constraint) for constraint in self.constraint)}
        """
        return ans

    def equiv(self, other):
        if isinstance(other, Rule):
            for action1 in self.action:
                if action1 not in other.action:
                    return False
            for action2 in other.action:
                if action2 not in self.action:
                    return False
            for target1 in self.target:
                if target1 not in other.target:
                    return False
            for target2 in other.target:
                if target2 not in self.target:
                    return False
            for assigner1 in self.assigner:
                if assigner1 not in other.assigner:
                    return False
            for assigner2 in other.assigner:
                if assigner2 not in self.assigner:
                    return False
            for assignee1 in self.assignee:
                if assignee1 not in other.assignee:
                    return False
            for assignee2 in other.assignee:
                if assignee2 not in self.assignee:
                    return False
            for constraint in self.constraint:
                if constraint not in other.constraint:
                    return False
            for constraint in other.constraint:
                if constraint not in self.constraint:
                    return False
            return True
        else:
            return False

    def add_constraint(self, constraint: Union[Constraint, 'LogicalConstraint']):
        """
        Adds a constraint to the Rule.

        :param constraint: Constraint or LogicalConstraint object to be added.
        """
        if isinstance(constraint, list):
            for c in constraint:
                self.add_constraint(c)
        else:
            self.constraint.append(constraint)

    def remove_constraint(self, constraint: Union[Constraint, 'LogicalConstraint']):
        """
        Removes a constraint from the Rule.

        :param constraint: Constraint or LogicalConstraint object to be removed.
        """
        if constraint in self.constraint:
            self.constraint.remove(constraint)

    def clear_constraint(self):
        """
        Clears all constraints associated with the Rule.
        """
        self.constraint = []

    def activate(self):
        """
        Activates the Rule.
        """
        self.state = "Active"

    def deactivate(self):
        """
        Deactivates the Rule.
        """
        self.state = "Inactive"

    def is_active(self) -> bool:
        """
        Checks if the Rule is active.

        :return: True if the Rule is active, False otherwise.
        """
        return self.state == "Active"

    def type(self):
        return self.__class__

    def normalise(self):
        ans = []
        and_constraint = LogicalConstraint(operator="and", constraints=self.constraint)
        and_constraint = and_constraint.normalise()
        and_constraint = and_constraint.simplify_intervals()
        if and_constraint.operator == "or":
            cqs = and_constraint.constraints
            for c in cqs:
                if isinstance(c, LogicalConstraint) and c.operator == "and":
                    ans.append(c.constraints)
                else:
                    ans.append(c)
        elif and_constraint.operator == "and":
            cqs = [and_constraint.constraints]
            return cqs
        return ans

    def get_values_from_constraints(self):
        ans = dict()
        for c in self.constraint:
            sub_values = c.get_values_per_left_operand()
            ans = Utils.merge_key_multisets(ans, sub_values)
        for target in self.target:
            for c in target.refinement:
                sub_values = c.get_values_per_left_operand()
                ans = Utils.merge_key_multisets(ans, sub_values)
        for action in self.action:
            for c in action.refinement:
                sub_values = c.get_values_per_left_operand()
                ans = Utils.merge_key_multisets(ans, sub_values)
        for assignee in self.assignee:
            for c in assignee.refinement:
                sub_values = c.get_values_per_left_operand()
                ans = Utils.merge_key_multisets(ans, sub_values)
        for assigner in self.assigner:
            for c in assigner.refinement:
                sub_values = c.get_values_per_left_operand()
                ans = Utils.merge_key_multisets(ans, sub_values)
        return ans
    
    def to_triples(self, uri):
        from rdflib import Namespace

        ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
        triples = []
        for action in self.action:
            triples.append((uri, ODRL.action, action.to_node()))
        for target in self.target:
            triples.append((uri, ODRL.target, target.to_node()))
        for assigner in self.assigner:
            triples.append((uri, ODRL.assigner, assigner.to_node()))
        for assignee in self.assignee:
            triples.append((uri, ODRL.assignee, assignee.to_node()))
        for constraint in self.constraint:
            constraint_bnode = BNode()
            triples.append((uri, ODRL.constraint, constraint_bnode))
            triples.extend(constraint.to_triples(constraint_bnode))
        return triples


class Duty(Rule):
    def __init__(self, target=None, action=None, assigner=None, assignee=None, constraint=None, consequence=None,
                 **args):
        """
        Initializes a Duty instance, extending the Rule class with additional properties
        for action, constraints, and a potential consequence.

        :param target: The object or entity the duty applies to.
        :param action: The primary action associated with the duty.
        :param assigner: The entity that imposes the duty.
        :param assignee: The entity obligated to fulfill the duty.
        :param consequence: Optional; another Duty (or Rule) instance representing the consequence of not fulfilling the duty.
        :param action: Optional; a list of additional Action objects associated with the duty.
        :param constraints: Optional; a list of Constraint objects specifying conditions under which the duty applies.
        """
        self.set_consequence(consequence)
        super().__init__(target=target, action=action, assigner=assigner, assignee=assignee, constraint=constraint,
                         **args)

    def add_action(self, action):
        """
        Adds an additional action to the duty.

        :param action: Action object to be added.
        """
        self.action.append(action)

    def remove_action(self, action):
        """
        Remove action from the duty.

        :param action: Action object to be removed.
        """
        if action in self.action:
            self.action.remove(action)

    def add_constraint(self, constraint):
        """
        Adds a constraint to the duty.

        :param constraint: Constraint object to be added.
        """
        self.constraint.append(constraint)

    def set_consequence(self, consequence):
        """
        Sets the consequence of the duty.

        :param consequence: Duty object representing the consequence.
        """
        if consequence is None:
            self.consequence = []
        elif isinstance(consequence, list):
            self.consequence = [Duty(**c) for c in consequence]
        elif isinstance(consequence, dict):
            self.consequence = [Duty(**consequence)]
        else:
            self.consequence = consequence

    def is_fulfilled(self):
        """
        Checks if the duty is fulfilled.

        :return: True if the duty is fulfilled, False otherwise.
        """
        # Implement your logic to check if the duty is fulfilled here
        # For example, if all constraints are satisfied, consider it as fulfilled
        return all(constraint.is_satisfied() for constraint in self.constraint)

    def clear_action(self):
        """
        Clears all additional action associated with the duty.
        """
        self.action = []

    def clear_constraint(self):
        """
        Clears all constraints associated with the duty.
        """
        self.constraint = []

    def clear_consequence(self):
        """
        Clears the consequence associated with the duty.
        """
        self.consequence = None

    def normalise(self):
        clone = super().normalise()
        ans = []
        for c in clone:
            temp = Duty(self.target, self.action, self.assigner, self.assignee)
            temp.add_constraint(c)
            ans.append(temp)
        return ans


class Obligation(Duty):
    def __init__(self, target=None, action=None, assigner=None, assignee=None, constraint=None, consequence=None,
                 **args):
        """
        Initializes a Obligation instance, extending the Rule class with additional properties
        for action, constraints, and a potential consequence.

        :param target: The object or entity the duty applies to.
        :param action: The primary action associated with the duty.
        :param assigner: The entity that imposes the duty.
        :param assignee: The entity obligated to fulfill the duty.
        :param consequence: Optional; another Duty (or Rule) instance representing the consequence of not fulfilling the duty.
        :param action: Optional; a list of additional Action objects associated with the duty.
        :param constraints: Optional; a list of Constraint objects specifying conditions under which the duty applies.
        """
        super().__init__(target=target, action=action, assigner=assigner, assignee=assignee, consequence=consequence,
                         constraint=constraint, **args)

    def is_fulfilled(self):
        """
        Checks if the duty is fulfilled.

        :return: True if the duty is fulfilled, False otherwise.
        """
        # Implement your logic to check if the duty is fulfilled here
        # For example, if all constraints are satisfied, consider it as fulfilled
        return all(constraint.is_satisfied() for constraint in self.constraint)

    def clear_action(self):
        """
        Clears all additional action associated with the duty.
        """
        self.action = []

    def clear_constraint(self):
        """
        Clears all constraints associated with the duty.
        """
        self.constraint = []

    def clear_consequence(self):
        """
        Clears the consequence associated with the duty.
        """
        self.consequence = None

    def normalise(self):
        clone = super().normalise()
        return clone


class Permission(Rule):
    def __init__(self, target=None, action=None, assigner=None, assignee=None, constraint=None, duty: Duty = None,
                 **args):
        """
        Initializes a Permission instance, extending the Rule class with an additional 'duty' property.

        :param target: The object or entity the permission applies to.
        :param action: The action permitted by the permission.
        :param assigner: The entity that grants the permission.
        :param assignee: The entity to whom the permission is granted.
        :param duty: Optional; an Action instance representing the duty associated with the permission.
        """

        self.set_duty(duty)
        super().__init__(target=target, action=action, assigner=assigner, assignee=assignee, constraint=constraint,
                         **args)

    def set_duty(self, duty):
        """
        Sets or updates the duty associated with the permission.

        :param duty: Action instance representing the duty.
        """
        if duty is None:
            self.duty = []
        elif isinstance(duty, list):
            self.duty = [Duty(**c) for c in duty]
        elif isinstance(duty, dict):
            self.duty = [Duty(**duty)]
        else:
            self.duty = duty

    def clear_duty(self):
        """
        Removes the duty associated with the permission.
        """
        self.duty = None

    def is_used(self):
        pass

    def normalise(self):
        clone = super().normalise()
        ans = []
        if len(clone) == 0:
            return [self]
        for c in clone:
            temp = Permission(self.target, self.action, self.assigner, self.assignee)
            temp.add_constraint(c)
            temp.set_duty(self.duty)
            ans.append(temp)
        return ans

    # Note this only works after normalisation.
    def split_intervals(self, value_map) -> list[Rule]:
        unique_constraints = []
        unique_rules = []
        # TODO: What to do if there are no constraints? i.e. everything is allowed.
        if len(self.constraint) == 0:
            c = Constraint.create(operator="and", constraints=[]).split_intervals(value_map)
            if isinstance(c, LogicalConstraint):
                if c.operator == "or":
                    for sub_c in c.constraints:
                        if sub_c not in unique_constraints:
                            unique_constraints.append(sub_c)
                        else:
                            print([str(s) for s in sub_c])
        else:
            for constraint in self.constraint:
                c = constraint.split_intervals(value_map)
                if isinstance(c, LogicalConstraint):
                    if c.operator == "or":
                        for sub_c in c.constraints:
                            if sub_c not in unique_constraints:
                                unique_constraints.append(sub_c)
        for constraint in unique_constraints:
            unique_rules.append(
                Permission(target=self.target, action=self.action, assigner=self.assigner, assignee=self.assignee,
                           constraint=constraint))
        return unique_rules


class Prohibition(Rule):
    def __init__(self, target=None, action=None, assigner=None, assignee=None, constraint=None, remedy: Duty = None,
                 **args):
        """
        Initializes a Prohibition instance, extending the Rule class with an additional 'remedy' property.

        :param target: The object or entity the prohibition applies to.
        :param action: The action permitted by the prohibition.
        :param assigner: The entity that grants the prohibition.
        :param assignee: The entity to whom the prohibition is granted.
        :param remedy: Optional; an Action instance representing the remedy associated with the prohibition.
        """

        self.set_remedy(remedy)
        super().__init__(target=target, action=action, assigner=assigner, assignee=assignee, constraint=constraint,
                         **args)

    def is_violated(self):
        """
        Checks if the prohibition has been violated.

        :return: True if the prohibition has been violated, False otherwise.
        """
        # # TODO: Implement your logic to check if the prohibition is violated here
        # For example, if the remedy is not None, consider it as violated
        return self.remedy is not None

    def set_remedy(self, remedy):
        """
        Sets or updates the remedy associated with the prohibition.

        :param remedy: Action instance representing the remedy.
        """

        if remedy is None:
            self.remedy = []
        elif isinstance(remedy, list):
            self.remedy = [Duty(**c) for c in remedy]
        elif isinstance(remedy, dict):
            self.remedy = [Duty(**remedy)]
        else:
            self.remedy = remedy

    def clear_remedy(self):
        """
        Removes the remedy associated with the prohibition.
        """
        self.remedy = None

    def normalise(self):
        clone = super().normalise()
        ans = []
        if len(clone) == 0:
            return [self]
        for c in clone:
            temp = Prohibition(self.target, self.action, self.assigner, self.assignee)
            temp.add_constraint(c)
            temp.set_remedy(self.remedy)
            ans.append(temp)
        return ans

    # Note this only works after normalisation.
    def split_intervals(self, value_map):
        unique_constraints = []
        unique_rules = []
        if len(self.constraint) == 0:
            c = Constraint.create(operator="and", constraints=[]).split_intervals(value_map)
            if isinstance(c, LogicalConstraint):
                if c.operator == "or":
                    for sub_c in c.constraints:
                        if sub_c not in unique_constraints:
                            unique_constraints.append(sub_c)
                        else:
                            print([str(s) for s in sub_c])
        for constraint in self.constraint:
            c = constraint.split_intervals(value_map)
            if isinstance(c, LogicalConstraint):
                if c.operator == "or":
                    for sub_c in c.constraints:
                        if sub_c not in unique_constraints:
                            unique_constraints.append(sub_c)

        for constraint in unique_constraints:
            unique_rules.append(
                Prohibition(target=self.target, action=self.action, assigner=self.assigner, assignee=self.assignee,
                            constraint=constraint))
        return unique_rules


class Policy:
    def __init__(self, uid, type, profiles=None, inherit_from=None, conflict=None,
                 permission: Optional[list[Permission]] = None, prohibition: Optional[list[Prohibition]] = None,
                 obligation: Optional[list[Obligation]] = None, duty: Optional[list[Duty]] = None):
        self.uid = uid
        self.type = type
        self.profiles = profiles if profiles else []
        self.permission = permission if permission else []
        self.prohibition = prohibition if prohibition else []
        self.obligation = obligation if obligation else []
        self.duty = duty if duty else []
        self.inherit_from = inherit_from if inherit_from else []
        self.conflict = conflict

    def __str__(self):
        ans = f"""
        permission: {"".join(str(permission) for permission in self.permission)}
        prohibition: {"".join(str(prohibition) for prohibition in self.prohibition)}
        obligation: {"".join(str(obligation) for obligation in self.obligation)}
        """
        return ans

    def normalise(self):
        final_permissions = []
        final_prohibitions = []
        final_obligations = []
        for permission in self.permission:
            normal_permissions = permission.normalise()
            for normal_permission in normal_permissions:
                final_permissions.append(normal_permission)
        for prohibition in self.prohibition:
            normal_prohibitions = prohibition.normalise()
            for normal_prohibition in normal_prohibitions:
                final_prohibitions.append(normal_prohibition)
        for obligation in self.obligation:
            normal_obligations = obligation.normalise()
            for normal_obligation in normal_obligations:
                final_obligations.append(normal_obligation)
        return Policy(uid=self.uid, type=self.type, profiles=self.profiles, permission=final_permissions,
                      prohibition=final_prohibitions, obligation=final_obligations)

    def get_values_from_constraints(self):
        ans = dict()
        for permission in self.permission:
            ans = Utils.merge_key_multisets(ans, permission.get_values_from_constraints())
        for prohibition in self.prohibition:
            ans = Utils.merge_key_multisets(ans, prohibition.get_values_from_constraints())
        for obligation in self.obligation:
            ans = Utils.merge_key_multisets(ans, obligation.get_values_from_constraints())
        return ans

    def split_intervals(self, value_map):
        new_permissions = []
        new_prohibitions = []
        for permission in self.permission:
            split_permissions = permission.split_intervals(value_map)
            for split_permission in split_permissions:
                # for new_permission in new_permissions:
                #     if split_permission.equiv(new_permission):
                #         break
                new_permissions.append(split_permission)
        for prohibition in self.prohibition:
            split_prohibitions = prohibition.split_intervals(value_map)
            for split_prohibition in split_prohibitions:
                # for new_prohibition in new_prohibitions:
                #     if split_prohibition.equiv(new_prohibition):
                #         break
                new_prohibitions.append(split_prohibition)
        return Policy(uid=self.uid, type=self.type, profiles=self.profiles, permission=new_permissions,
                      prohibition=new_prohibitions, obligation=self.obligation)
    
    def to_rdflib_graph(self):
        from rdflib import Graph, Namespace, URIRef, Literal
        from rdflib.namespace import RDF

        ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
        graph = Graph()

        policy_uri = URIRef(f"http://example.com/policy/{self.uid}")
        graph.add((policy_uri, RDF.type, ODRL.Policy))

        for permission in self.permission:
            permission_uri = URIRef(f"{policy_uri}/permission/{id(permission)}")
            graph.add((policy_uri, ODRL.permission, permission_uri))
            for triple in permission.to_triples(permission_uri):
                graph.add(triple)

        for prohibition in self.prohibition:
            prohibition_uri = URIRef(f"{policy_uri}/prohibition/{id(prohibition)}")
            graph.add((policy_uri, ODRL.prohibition, prohibition_uri))
            for triple in prohibition.to_triples(prohibition_uri):
                graph.add(triple)

        for obligation in self.obligation:
            obligation_uri = URIRef(f"{policy_uri}/obligation/{id(obligation)}")
            graph.add((policy_uri, ODRL.obligation, obligation_uri))
            for triple in obligation.to_triples(obligation_uri):
                graph.add(triple)

        return graph

