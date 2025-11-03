from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF
from rdflib.plugin import Parser
import datetime
import logging
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3.11 or higher is required.")
if sys.version_info[1] < 11:
    raise Exception("Python 3.11 or higher is required.")


class ContractParser:
    IDSA = Namespace("https://w3id.org/idsa/core/")
    UPCAST = Namespace("https://www.upcast-project.eu/upcast-vocab/1.0/")

    def __init__(self):
        self.contract_graph = None

    def load(self, file_path):
        """
        Loads the contract data from the specified file path.
        Tries multiple RDF serializations and encodings until one succeeds, or
        all are exhausted.
        """
        self.contract_graph = Graph()

        rdf_formats = [
            "xml",       # RDF/XML
            "turtle",    # Turtle / TTL
            "nt",        # N-Triples
            "n3",        # Notation3
            "json-ld",   # JSON-LD
            "trig",      # TriG
            "trix",      # TriX
        ]

        # Try parsing with each format
        last_exception = None
        for rdf_format in rdf_formats:
            try:
                self.contract_graph.parse(file_path, format=rdf_format)
                break
            except Exception as e:
                last_exception = e
                self.contract_graph = Graph()  # reset in case of partial parse
        else:
            # If no parser worked, try again by reading file contents with encodings
            encodings = ["utf-8", "utf-16", "latin-1"]
            for enc in encodings:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        data = f.read()
                    for rdf_format in available_formats:
                        try:
                            self.contract_graph.parse(data=data, format=rdf_format)
                            break
                        except Exception:
                            continue
                    else:
                        continue
                    break
                except Exception as e:
                    last_exception = e

        if len(self.contract_graph) == 0 and last_exception:
            raise ValueError(
                f"Failed to parse RDF file {file_path}. Last error: {last_exception}"
            )
        self.contract_graph.bind("idsa-core", ContractParser.IDSA)
        self.contract_graph.bind("upcast", ContractParser.UPCAST)

    def query(self, query_string):
        """
        Query the loaded contract data with the specified SPARQL query string.
        """
        pass

    def get_contract_uri(self):
        """
        Convenience method to get the URI of the contract to use in other methods
        Assumption: A loaded document contains a single contract, hence a single contract URI
        Returns a rdflib Graph node
        """
        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")
        contract_id = self.contract_graph.value(predicate=RDF.type, object=ContractParser.IDSA.Contract)
        return contract_id

    def get_provider(self):
        """
        Convenience method to get the provider of the contract
        """
        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")
        provider = self.contract_graph.value(predicate=ContractParser.IDSA.Provider, subject=self.get_contract_uri())
        return provider

    def get_consumer(self):
        """
        Convenience method to get the provider of the contract
        """
        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")
        consumer = self.contract_graph.value(predicate=ContractParser.IDSA.Consumer, subject=self.get_contract_uri())
        return consumer

    def get_permitted_actions(self):
        """
        Convenience method to get the permitted actions of the contract
        """

        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        # Permitted actions and their IRIs
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?actionValue
        WHERE {
        ?agreement a ?type ;
             odrl:permission ?permission .
        VALUES ?type { odrl:Agreement odrl:Policy odrl:Set odrl:Offer }
         {?permission odrl:action ?actionValue .}
        UNION
        {?permission odrl:action ?actionIRI .
         ?actionIRI rdf:value ?actionValue .}

        }
        """
        query_results = self.contract_graph.query(query)
        permitted_actions = {str(row.actionValue) for row in query_results if isinstance(row.actionValue,URIRef)}


        return permitted_actions

    def get_prohibited_actions(self):
        """
        Convenience method to get the prohibited actions of the contract
        """

        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        # Permitted actions and their IRIs
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?actionValue
        WHERE {
        ?agreement odrl:prohibition ?prohibition .
        {?prohibition odrl:action ?actionValue .}
        UNION
        {?prohibition odrl:action ?actionIRI .
         ?actionIRI rdf:value ?actionValue .}
        }
        """
        query_results = self.contract_graph.query(query)
        prohibited_actions = {str(row.actionValue) for row in query_results if isinstance(row.actionValue,URIRef)}
        return prohibited_actions

    def get_action_container(self,actionValue):
        """
        Input: action Value, i.e. , its name in String format
        Output: URL of the container that implements the input action IRI, None if not specified in the contract
        """

        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?rightOperand
        WHERE {
        ?actionIRI rdf:value ?actionValue .
        ?actionIRI odrl:refinement ?refinement .
        ?refinement odrl:leftOperand upcast:implementedBy ;
                    odrl:operator odrl:eq ;
                    odrl:rightOperand ?rightOperand .
        }
        """
        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        qres_list = list(qres)

        return str(qres_list[0]["rightOperand"]) if len(qres) > 0 else None

    def get_action_execution_command(self,actionValue):
        """
        Input: action Value, i.e. , its name in String format
        Output: URL of the container that implements the input action IRI, None if not specified in the contract
        """

        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?rightOperand
        WHERE {
        ?actionIRI rdf:value ?actionValue .
        ?actionIRI odrl:refinement ?refinement .
        ?refinement odrl:leftOperand upcast:executionCommand ;
                    odrl:operator odrl:eq ;
                    odrl:rightOperand ?rightOperand .
        }
        """
        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        qres_list = list(qres)

        return str(qres_list[0]["rightOperand"]) if len(qres) > 0 else None

    def get_action_execution_limits(self,actionValue):
        """
        input: actionValue, that is the name of the action in string format
        output: list of tuple of the form (operator, rightOperand) where operator is the comparison odrl operator (eq,lteq,gteq,gt) and rightOperand the integer value.
                An empty list is returned if the action does not have any execution limit
        """
        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?operator ?rightOperand
        WHERE {
        ?actionIRI rdf:value ?actionValue .
        ?actionIRI odrl:refinement ?refinement .
        ?refinement odrl:leftOperand odrl:count ;
                    odrl:operator ?operator;
                    odrl:rightOperand ?rightOperand .
        }
        """
        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        limits = []
        for row in qres:
            operator = str(row["operator"]).split("/")[-1]
            value = int(row["rightOperand"])
            limits.append((operator,value))

        return limits

    def get_action_carbon_emission_limit(self,actionValue):
        """
        input: actionValue, that is the name of the action in string format
        output: Float value of maximum carbon emission agreed for this operation (that is, operator less ro equal than is assumed)
          returns None if there is no carbon emission limit defined in the contract
        """
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?rightOperand ?unit
        WHERE {
        ?actionIRI rdf:value ?actionValue .
        ?actionIRI odrl:constraint ?constraint .
        ?constraint odrl:leftOperand upcast:operationCarbonEmission ;
                    odrl:operator odrl:lteq;
                    odrl:rightOperand ?rightOperand;
                    odrl:unit ?unit  .
        }
        """
        qres = list(self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)}))
        if len(qres) == 0:
            return None
        result = qres[0]
        return (result["rightOperand"].toPython(),result["unit"].toPython())

    def get_action_energy_consumption_limit(self,actionValue):
        """
        input: actionValue, that is the name of the action in string format
        output: tuple (value,unit), with value a float of maximum energy consumption agreed for this operation (that is, operator less ro equal than is assumed)
             unit a string with the unit of the value
        """
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?rightOperand ?unit
        WHERE {
        ?actionIRI rdf:value ?actionValue .
        ?actionIRI odrl:constraint ?constraint .
        ?constraint odrl:leftOperand upcast:operationEnergyConsumption ;
                    odrl:operator odrl:lteq;
                    odrl:rightOperand ?rightOperand ;
                    odrl:unit ?unit  .
        }
        """
        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        qres = list(self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)}))
        if len(qres) == 0:
            return None
        result = qres[0]
        return (result["rightOperand"].toPython(),result["unit"].toPython())

    def get_action_datetime_constraints(self,actionValue):
        """
        input: actionValue, that is the name of the action in string format
        output: list of tuple of the form (operator, datetime) where rule is one of {Permission,Prohibition,Duty}, operator is the comparison odrl operator (eq,lt,lteq,gteq,gt) and datetime is the constrained datetime.
                An empty list is returned if the action does not have any datetime constraint.
        """
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?rule ?operator ?rightOperand
        WHERE {
        ?policy a ?type .
        VALUES ?type { odrl:Agreement odrl:Policy odrl:Set odrl:Offer }
        ?policy ?rule ?rulesetBnode .
        ?rulesetBnode odrl:action ?actionIRI .
        ?actionIRI rdf:value ?actionValue .
        ?rulesetBnode odrl:constraint ?constraint .
        ?constraint odrl:leftOperand odrl:dateTime ;
                    odrl:operator ?operator;
                    odrl:rightOperand ?rightOperand .
        }
        """
        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        limits = []
        for row in qres:
            rule = str(row["rule"]).split("/")[-1]
            operator = str(row["operator"]).split("/")[-1]
            value = row["rightOperand"].toPython()
            limits.append((operator,value))
        return limits

    def get_action_dependencies(self,actionValue):
        """
        input: actionValue, that is the name of the action in string format
        output: list of actions that must be executed before the input action according to the loaded contract
        """
        if self.contract_graph is None:
            raise Exception("No contract loaded into this parser")

        # Note the permission and not the action is the one that has a duty
        query = """
        PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX upcast: <https://www.upcast-project.eu/upcast-vocab/1.0/>

        SELECT ?dependencyValue
        WHERE {
        ?agreement a ?type ;
             odrl:permission ?permission .
        VALUES ?type { odrl:Agreement odrl:Policy odrl:Set odrl:Offer }
        ?permission odrl:action ?actionIRI .
        ?actionIRI rdf:value ?actionValue .
        ?permission odrl:duty ?dutyIRI .
        ?dutyIRI odrl:action ?dependencyIRI .
        ?dependencyIRI rdf:value ?dependencyValue .
        }
        """

        qres = self.contract_graph.query(query,initBindings={'actionValue': URIRef(actionValue)})
        dependencies = [str(row["dependencyValue"]) for row in qres]
        return dependencies



####################


from google.colab import files

# Prompt user to upload a file
print("Please upload your ODRL file:")
uploaded = files.upload()

# Get the uploaded filename
file_path = list(uploaded.keys())[0]

# Initialize the parser and load the ODRL file
parser = ContractParser()
parser.load(file_path)

# Fetch and display contract URI
contract_uri = parser.get_contract_uri()
print("Contract URI:", contract_uri)

# Fetch and display provider
provider = parser.get_provider()
print("Provider:", provider)

# Fetch and display consumer
consumer = parser.get_consumer()
print("Consumer:", consumer)

# Fetch and display permitted actions
permitted_actions = parser.get_permitted_actions()
print("\nPermitted Actions:")
for action in permitted_actions:
    print("-", action)

# Fetch and display prohibited actions
prohibited_actions = parser.get_prohibited_actions()
print("\nProhibited Actions:")
for action in prohibited_actions:
    print("-", action)

# For each permitted action, fetch and display further details
for action in permitted_actions:
    print(f"\nDetails for action: {action}")

    container = parser.get_action_container(action)
    print("  Container:", container)

    exec_command = parser.get_action_execution_command(action)
    print("  Execution Command:", exec_command)

    exec_limits = parser.get_action_execution_limits(action)
    print("  Execution Limits:", exec_limits)

    carbon_limit = parser.get_action_carbon_emission_limit(action)
    print("  Carbon Emission Limit:", carbon_limit)

    energy_limit = parser.get_action_energy_consumption_limit(action)
    print("  Energy Consumption Limit:", energy_limit)

    datetime_constraints = parser.get_action_datetime_constraints(action)
    print("  DateTime Constraints:", datetime_constraints)

    dependencies = parser.get_action_dependencies(action)
    print("  Dependencies:", dependencies)

###################

from rdflib import Graph, URIRef


parser = ContractParser()
parser.load(file_path)

provider = parser.get_provider()
print(f'Provider: {provider}')

consumer = parser.get_consumer()
print(f'Consumer: {consumer}')

print('Permitted Actions')
permitted_actions = parser.get_permitted_actions()
#permitted_actions = set(map(lambda x: x[1], permitted_actions))
print(permitted_actions)

print(f'Container for {"http://www.w3.org/ns/odrl/2/anonymize"}: ', end='')
action_container = parser.get_action_container(actionValue="http://www.w3.org/ns/odrl/2/anonymize")
print(action_container)

print(f'Action Execution Limit for {"http://www.w3.org/ns/odrl/2/anonymize"}')
action_execution_limit = parser.get_action_execution_limits(actionValue="http://www.w3.org/ns/odrl/2/anonymize")
print(action_execution_limit)

print(f'Action Execution Limit for {"http://www.w3.org/ns/odrl/2/aggregate"}')
action_execution_limit = parser.get_action_execution_limits(actionValue="http://www.w3.org/ns/odrl/2/aggregate")
print(action_execution_limit)

print(f'Action Execution Limit for {"https://www.upcast-project.eu/upcast-vocab/1.0/Integrate"}')
action_execution_limit = parser.get_action_execution_limits(actionValue="https://www.upcast-project.eu/upcast-vocab/1.0/Integrate")
print(action_execution_limit)

print(f'Datetime Constraint for {"http://www.w3.org/ns/odrl/2/anonymize"}')
action_datetime_constraints = parser.get_action_datetime_constraints(actionValue="http://www.w3.org/ns/odrl/2/anonymize")
print(action_datetime_constraints)

print(f'Datetime Constraint for {"http://www.w3.org/ns/odrl/2/aggregate"}')
action_datetime_constraints = parser.get_action_datetime_constraints(actionValue="http://www.w3.org/ns/odrl/2/aggregate")
print(action_datetime_constraints)

print(f'Datetime Constraint for {"http://www.w3.org/ns/odrl/2/use"}')
action_datetime_constraints = parser.get_action_datetime_constraints(actionValue="http://www.w3.org/ns/odrl/2/use")
print(action_datetime_constraints)

print(f'Datetime Constraint for {"https://www.upcast-project.eu/upcast-vocab/1.0/Integrate"}')
action_datetime_constraints = parser.get_action_datetime_constraints(actionValue="https://www.upcast-project.eu/upcast-vocab/1.0/Integrate")
print(action_datetime_constraints)

print(f'Energy Consumption Limit for {"https://www.upcast-project.eu/upcast-vocab/1.0/Integrate"}')
action_energy_limit = parser.get_action_energy_consumption_limit(actionValue="https://www.upcast-project.eu/upcast-vocab/1.0/Integrate")
print(action_energy_limit)

print(f'Energy Consumption Limit for {"http://www.w3.org/ns/odrl/2/anonymize"}')
action_energy_limit = parser.get_action_energy_consumption_limit(actionValue="http://www.w3.org/ns/odrl/2/anonymize")
print(action_energy_limit)

print(f'Carbon Emission Limit for {"http://www.w3.org/ns/odrl/2/aggregate"}')
action_carbon_limit = parser.get_action_carbon_emission_limit(actionValue="http://www.w3.org/ns/odrl/2/aggregate")
print(action_carbon_limit)

print(f'Carbon Emission Limit for {"http://www.w3.org/ns/odrl/2/anonymize"}')
action_carbon_limit = parser.get_action_carbon_emission_limit(actionValue="http://www.w3.org/ns/odrl/2/anonymize")
print(action_carbon_limit)

print(f'Action Dependencies for {"http://www.w3.org/ns/odrl/2/aggregate"}')
action_dependencies = parser.get_action_dependencies(actionValue="http://www.w3.org/ns/odrl/2/aggregate")
print(action_dependencies)

print(f'Action Dependencies for {"https://www.upcast-project.eu/upcast-vocab/1.0/Integrate"}')
action_dependencies = parser.get_action_dependencies(actionValue="https://www.upcast-project.eu/upcast-vocab/1.0/Integrate")
print(action_dependencies)
