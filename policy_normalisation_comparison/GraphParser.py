import rdflib
from rdflib import Graph, RDF

import Refinables
import Utils
from Refinables import Refinable
from Constraint import Constraint, LogicalConstraint
from Policy import Policy, Permission, Prohibition, Obligation

ODRL = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")
ODRL_AND = rdflib.URIRef("http://www.w3.org/ns/odrl/2/and")
ODRL_OR = rdflib.URIRef("http://www.w3.org/ns/odrl/2/or")
ID_NODE = rdflib.URIRef("@id")


class GraphParser:
    def __init__(self, graph=Graph()):
        self.graph = graph

    def parse(self) -> Policy:
        policy = self.graph.value(RDF.type, ODRL.Policy)
        profiles = []
        inherits_from_list = []
        permissions = []
        prohibitions = []
        obligations = []
        uid = self.graph.value(policy, ID_NODE) if (policy, ID_NODE, None) in self.graph else None
        policy_type = self.graph.value(policy, RDF.type) if (policy, RDF.type, None) in self.graph else None
        conflict = self.graph.value(policy, ODRL.conflict) if (policy, ODRL.conflict, None) in self.graph else None

        for permission in self.graph.objects(policy, ODRL.permission):
            permissions.append(self.parse_permission(permission))
        for prohibition in self.graph.objects(policy, ODRL.prohibition):
            prohibitions.append(self.parse_prohibition(prohibition))
        for obligation in self.graph.objects(policy, ODRL.obligation):
            obligations.append(self.parse_obligation(obligation))
        return Policy(uid=uid, type=policy_type, profiles=profiles, conflict=conflict, inherit_from=inherits_from_list,
                      permission=permissions, prohibition=prohibitions, obligation=obligations)

    def parse_permission(self, permission) -> Permission:
        target = self.parse_targets(self.graph.objects(permission, ODRL.target)) if (permission, ODRL.target,
                                                                                     None) in self.graph else None
        duty = self.parse_obligation(self.graph.objects(permission, ODRL.duty)) if (permission, ODRL.duty,
                                                                                    None) in self.graph else None
        action = self.parse_actions(self.graph.objects(permission, ODRL.action)) if (permission, ODRL.action,
                                                                                     None) in self.graph else None
        assigner = self.parse_actors(self.graph.objects(permission, ODRL.assigner)) if (permission, ODRL.assigner,
                                                                                        None) in self.graph else None
        assignee = self.parse_actors(self.graph.objects(permission, ODRL.assignee)) if (permission, ODRL.assignee,
                                                                                        None) in self.graph else None
        constraints = self.parse_constraints(self.graph.objects(permission, ODRL.constraint)) if (permission,
                                                                                                  ODRL.constraint,
                                                                                                  None) in self.graph else None
        return Permission(target=target, duty=duty, action=action, assigner=assigner, assignee=assignee,
                          constraint=constraints)

    def parse_prohibition(self, prohibition) -> Prohibition:
        target = self.parse_targets(self.graph.objects(prohibition, ODRL.target)) if (prohibition, ODRL.target,
                                                                                      None) in self.graph else None
        remedy = self.parse_obligation(self.graph.objects(prohibition, ODRL.remedy)) if (prohibition, ODRL.remedy,
                                                                                         None) in self.graph else None
        action = self.parse_actions(self.graph.objects(prohibition, ODRL.action)) if (prohibition, ODRL.action,
                                                                                      None) in self.graph else None
        assigner = self.parse_actors(self.graph.objects(prohibition, ODRL.assigner)) if (prohibition, ODRL.assigner,
                                                                                         None) in self.graph else None
        assignee = self.parse_actors(self.graph.objects(prohibition, ODRL.assignee)) if (prohibition, ODRL.assignee,
                                                                                         None) in self.graph else None
        constraints = self.parse_constraints(self.graph.objects(prohibition, ODRL.constraint)) if (prohibition,
                                                                                                   ODRL.constraint,
                                                                                                   None) in self.graph else None
        return Prohibition(target=target, remedy=remedy, action=action, assigner=assigner, assignee=assignee,
                           constraint=constraints)

    def parse_obligation(self, obligation) -> Obligation:
        target = self.parse_targets(self.graph.objects(obligation, ODRL.target)) if (obligation, ODRL.target,
                                                                                     None) in self.graph else None
        consequence = self.parse_obligation(self.graph.objects(obligation, ODRL.consequence)) if (obligation,
                                                                                                  ODRL.consequence,
                                                                                                  None) in self.graph else None
        action = self.parse_actions(self.graph.objects(obligation, ODRL.action)) if (obligation, ODRL.action,
                                                                                     None) in self.graph else None
        assigner = self.parse_actors(self.graph.objects(obligation, ODRL.assigner)) if (obligation, ODRL.assigner,
                                                                                        None) in self.graph else None
        assignee = self.parse_actors(self.graph.objects(obligation, ODRL.assignee)) if (obligation, ODRL.assignee,
                                                                                        None) in self.graph else None
        constraints = self.parse_constraints(self.graph.objects(obligation, ODRL.constraint)) if (obligation,
                                                                                                  ODRL.constraint,
                                                                                                  None) in self.graph else None
        return Obligation(target=target, consequence=consequence, action=action, assigner=assigner, assignee=assignee,
                          constraint=constraints)

    def parse_targets(self, targets) -> list[Refinable]:
        target_list = []
        for target in targets:
            if isinstance(target, rdflib.BNode):
                target_value = self.graph.value(target, RDF.value)
                target_source = self.graph.value(target, ODRL.source)
                target_refinables = []
                if (target, ODRL.refinement, None) in self.graph:
                    target_refinables = self.parse_constraints(self.graph.objects(target, ODRL.refinement))
                target_list.append(Refinable(value=target_value, source=target_source, refinement=target_refinables))
            else:
                target_list.append(Refinable(value=target))
        return target_list

    def parse_actions(self, actions) -> list[Refinables.Action]:
        action_list = []
        for action in actions:
            if isinstance(action, rdflib.BNode):
                action_value = self.graph.value(action, RDF.value)
                action_refinables = self.parse_constraints(self.graph.objects(action, ODRL.refinable))
                action_list.append(Refinables.Action(value=action_value, refinement=action_refinables))
            else:
                action_list.append(Refinables.Action(value=action))
        return action_list

    def parse_actors(self, actors) -> list[Refinable]:
        actors_list = []
        for actor in actors:
            if isinstance(actor, rdflib.BNode):
                actor_value = self.graph.value(actor, RDF.value)
                actor_source = self.graph.value(actor, ODRL.source)
                actor_refinables = []
                if (actor, ODRL.refinement, None) in self.graph:
                    actor_refinables = self.parse_constraints(self.graph.objects(actor, ODRL.refinement))
                actors_list.append(Refinable(value=actor_value, source=actor_source, refinement=actor_refinables))
            else:
                actors_list.append(Refinable(value=actor))
        return actors_list

    def parse_constraints(self, constraints) -> list[Refinables.Constraint]:
        constraint_list = []
        for constraint in constraints:
            if (constraint, ODRL.leftOperand, None) in self.graph:
                left_operand = str(self.graph.value(constraint, ODRL.leftOperand))
                operator = str(self.graph.value(constraint, ODRL.operator))
                if (constraint, ODRL.rightOperand, None) in self.graph:
                    right_operand = Utils.string_to_element(str(self.graph.value(constraint, ODRL.rightOperand)))
                else:
                    right_operand = self.graph.value(constraint, ODRL.rightOperandReference)
                constraint_list.append(Constraint.create(left_operand, operator, right_operand))
            elif (constraint, ODRL_AND, None) in self.graph:
                sub_constraints = self.parse_constraints(self.graph.objects(constraint, ODRL_AND))
                constraint_list.append(LogicalConstraint(operator="and", constraints=sub_constraints))
            elif (constraint, ODRL_OR, None) in self.graph:
                sub_constraints = self.parse_constraints(self.graph.objects(constraint, ODRL_OR))
                constraint_list.append(LogicalConstraint(operator="or", constraints=sub_constraints))
            elif (constraint, ODRL.xor, None) in self.graph:
                sub_constraints = self.parse_constraints(self.graph.objects(constraint, ODRL.xor))
                constraint_list.append(LogicalConstraint(operator="xor", constraints=sub_constraints))
        return constraint_list
