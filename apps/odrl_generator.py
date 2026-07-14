import streamlit as st

from pathlib import Path
import sys


# ============================================================
# Add project root to Python path
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.streamlit_style import apply_style
import ODRL_generator


# ============================================================
# Streamlit configuration
# ============================================================

st.set_page_config(
    page_title="ODRL Policy Generator",
    layout="wide"
)
apply_style()

# ============================================================
# INFO PANEL
# ============================================================

INFO_TEXT = """
### Policy Generation Parameters

**Number of Policies**  
Number of policies to generate.  
Each policy will have its own set of rules and constraints but share the same sampled constants.

---

**Number of Permission Rules**  
How many permission rules each policy contains.  
Permissions specify allowed actions within the policy. Higher numbers create more permission nodes.

---

**Number of Prohibition Rules**  
How many prohibition rules each policy contains.  
Prohibitions restrict actions. Increasing this number makes policies more restrictive.

---

**Number of Obligation Rules**  
How many obligation rules each policy imposes.  
Obligations define actions that must be performed.

---

**Duties per Permission**  
Number of duty rules attached to each permission that includes duties.

---

**Permissions with Duties**  
Number of permissions that will include duties.  
If this number exceeds the number of permissions, all permissions will include duties.

---

**Remedies per Prohibition**  
Number of remedy duties attached to each prohibition that includes remedies.

---

**Prohibitions with Remedies**  
Number of prohibitions that will include remedies.  
If this number exceeds the number of prohibitions, all prohibitions will include remedies.

---

**Constants per Feature**  
Number of actions, parties, targets and left operands sampled for all policies.

Controls the diversity of IRIs used across rules. All policies share the same sampled constants for consistency while allowing randomness in rule assignment.

---

**Minimum / Maximum Constraints per Rule**  
Lower and upper bound on the number of constraints per rule.

Constraints refine rules using:
- leftOperand
- operator
- rightOperand

---

**Chance Feature Null (0-1)**  
Probability that a non-required feature (assignee or target) is omitted.

A value closer to 1 means more features will be left empty, producing sparser and less specific rules.

---

**Constraint Right Operand Min / Max**  
Minimum and maximum numeric value for randomly generated constraint rightOperands.

Sets the lower and upper bounds for numeric thresholds used in constraints.

---

**Ontology Path**  
Path to the ontology TTL file used for sampling IRIs.

Actions, parties, targets and leftOperands are sampled from ontology concepts.
"""


# ============================================================
# Page title
# ============================================================

st.title("ODRL Policy Generator")

st.write(
    """
Generate ODRL policies based on a number of parameters.
The generated RDF/Turtle policy can be viewed and downloaded.
"""
)


# ============================================================
# INFO EXPANDER
# ============================================================

with st.expander("ℹ️ Generation Parameter Information"):
    st.markdown(INFO_TEXT)


# ============================================================
# INPUT PARAMETERS
# ============================================================

st.subheader("Generation Parameters")


col1, col2 = st.columns(2)


with col1:

    policy_number = st.number_input(
        "Number of Policies",
        min_value=1,
        value=1,
        step=1
    )

    p_rule_n = st.number_input(
        "Permission Rules",
        min_value=0,
        value=2,
        step=1
    )

    f_rule_n = st.number_input(
        "Prohibition Rules",
        min_value=0,
        value=2,
        step=1
    )

    o_rule_n = st.number_input(
        "Obligation Rules",
        min_value=0,
        value=1,
        step=1
    )

    duties_per_p_n = st.number_input(
        "Duties per Permission",
        min_value=0,
        value=0,
        step=1
    )

    p_with_duties_n = st.number_input(
        "Permissions with Duties",
        min_value=0,
        value=0,
        step=1
    )

    remedies_per_f_n = st.number_input(
        "Remedies per Prohibition",
        min_value=0,
        value=0,
        step=1
    )

    f_with_remedies_n = st.number_input(
        "Prohibitions with Remedies",
        min_value=0,
        value=0,
        step=1
    )


with col2:

    constants_per_feature = st.number_input(
        "Constants per Feature",
        min_value=1,
        value=4,
        step=1
    )

    constraint_number_min = st.number_input(
        "Minimum Constraints per Rule",
        min_value=0,
        value=0,
        step=1
    )

    constraint_number_max = st.number_input(
        "Maximum Constraints per Rule",
        min_value=0,
        value=4,
        step=1
    )

    chance_feature_null = st.number_input(
        "Chance Feature Null (0-1)",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05
    )

    constraint_right_operand_min = st.number_input(
        "Constraint Right Operand Min",
        value=0,
        step=1
    )

    constraint_right_operand_max = st.number_input(
        "Constraint Right Operand Max",
        value=100,
        step=1
    )

    ontology_path = st.text_input(
        "Ontology Path",
        value="sample_ontologies/ODRL_DPV.ttl"
    )


# ============================================================
# GENERATION
# ============================================================

if "generated_ttl" not in st.session_state:
    st.session_state.generated_ttl = None


if st.button(
    "Generate ODRL Policy",
    type="primary"
):

    try:

        policies_graph = ODRL_generator.generate_ODRL(

            policy_number=policy_number,

            p_rule_n=p_rule_n,

            f_rule_n=f_rule_n,

            o_rule_n=o_rule_n,

            duties_per_p_n=duties_per_p_n,

            p_with_duties_n=p_with_duties_n,

            remedies_per_f_n=remedies_per_f_n,

            f_with_remedies_n=f_with_remedies_n,

            constants_per_feature=constants_per_feature,

            constraint_number_min=constraint_number_min,

            constraint_number_max=constraint_number_max,

            chance_feature_null=chance_feature_null,

            constraint_right_operand_min=constraint_right_operand_min,

            constraint_right_operand_max=constraint_right_operand_max,

            ontology_path=ontology_path
        )


        turtle_output = policies_graph.serialize(
            format="turtle"
        )


        if isinstance(turtle_output, bytes):
            turtle_output = turtle_output.decode("utf-8")


        st.session_state.generated_ttl = turtle_output


        st.success(
            "ODRL policy generated successfully!"
        )


    except Exception as e:

        st.error(
            f"Error during generation: {e}"
        )



# ============================================================
# OUTPUT TTL
# ============================================================

if st.session_state.generated_ttl:

    st.subheader("Generated TTL")


    st.text_area(
        "Turtle Output",
        value=st.session_state.generated_ttl,
        height=500
    )


    st.download_button(
        label="Download TTL",
        data=st.session_state.generated_ttl,
        file_name="generated_policy.ttl",
        mime="text/turtle"
    )