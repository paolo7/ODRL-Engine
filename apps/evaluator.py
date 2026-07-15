import streamlit as st

import tempfile
import os
import pandas as pd
from io import StringIO

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.streamlit_style import apply_style
import ODRL_Evaluator as Evaluator
import rdf_utils
from SotW_generator import extract_features_list_from_policy

# ------------------------------
# Page setup
# ------------------------------

st.set_page_config(
    page_title="ODRL Policy Evaluator",
    layout="wide"
)
apply_style()
st.markdown("## Policy Evaluator")

st.markdown(
    "This is a DEMO of the [OVAL Policy Evaluator for ODRL](https://github.com/DIPS-Tools/ODRL-Engine) from the University of Southampton."
)

st.markdown(
    "Paste or upload an **ODRL Policy** and a **State of the World**, then evaluate. You can see sample files [here](https://github.com/DIPS-Tools/ODRL-Engine/tree/main/test_cases/evaluation/valid)"
)

st.markdown(
    "After uploading an **ODRL Policy** you can press the **Show expected column names** button below to see a list of the column names that should appear in the State of the World. Each column name is listed in a row, note that some of them include a space in the name, which must be preserved. The order of the columns does not matter. If a column does not appear in the State of the World Object, the evaluator will assume all values are null for that feature."
)

# ------------------------------
# Session state initialization
# ------------------------------

if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""

if "sotw_text" not in st.session_state:
    st.session_state.sotw_text = ""

if "raw_toggle" not in st.session_state:
    st.session_state.raw_toggle = True  # start TRUE

if "sotw_editor" not in st.session_state:
    st.session_state.sotw_editor = ""
# ------------------------------
# Layout
# ------------------------------

col1, col2 = st.columns(2)

# ==============================
# POLICY COLUMN
# ==============================

with col1:

    st.subheader("ODRL Policy")

    uploaded_policy = st.file_uploader(
        "Upload Policy File (.ttl or .json)",
        type=["ttl", "json"],
        label_visibility="collapsed",
        key="policy_upload"
    )

    # Handle upload immediately
    if uploaded_policy is not None:

        content = uploaded_policy.read().decode("utf-8")

        if content != st.session_state.policy_text:
            st.session_state.policy_text = content
            st.rerun()

    # Policy text box
    policy_text = st.text_area(
        label="Policy Text",
        height=450,
        key="policy_text"
    )

    # ------------------------------
    # Show expected column names
    # ------------------------------

    if st.button(
        "Show expected column names",
        use_container_width=True
    ):

        if not st.session_state.policy_text.strip():

            st.warning("⚠️ Please paste or upload an ODRL policy first.")

        else:

            try:
                # Save policy temporarily so rdf_utils can load it
                if st.session_state.policy_text.strip().startswith("{"):
                    policy_suffix = ".json"
                else:
                    policy_suffix = ".ttl"

                with tempfile.NamedTemporaryFile(
                    suffix=policy_suffix,
                    delete=False,
                    mode="w",
                    encoding="utf-8"
                ) as policy_file:

                    policy_file.write(
                        st.session_state.policy_text
                    )
                    policy_path = policy_file.name

                # Load RDF graph
                graph = rdf_utils.load(policy_path)[0]

                # Extract features
                features = extract_features_list_from_policy(graph)

                column_names = [
                    feature["iri"]
                    for feature in features
                ]

                st.subheader("Expected column names")

                bullet_list = "\n".join(
                    [f"- `{name}`" for name in column_names]
                )

                st.markdown(bullet_list)

            except Exception:

                st.error(
                    "Error, the policy input field does not contain a valid ODRL policy"
                )

            finally:

                if "policy_path" in locals():
                    if os.path.exists(policy_path):
                        os.remove(policy_path)

# ==============================
# SOTW COLUMN
# ==============================

with col2:

    st.subheader("State of the World")

    uploaded_sotw = st.file_uploader(
        "Upload SotW CSV",
        type=["csv"],
        label_visibility="collapsed",
        key="sotw_upload"
    )

    # Handle CSV upload
    if uploaded_sotw is not None:

        content = uploaded_sotw.getvalue().decode("utf-8")

        if content != st.session_state.sotw_text:
            st.session_state.sotw_text = content
            st.session_state.sotw_editor = content
            st.session_state.raw_toggle = False
            st.rerun()

    # ------------------------------
    # Raw Toggle (fixed behavior)
    # ------------------------------

    raw_toggle = st.toggle(
        "Raw Text",
        key="raw_toggle"
    )

    st.session_state.sotw_text = st.session_state.sotw_editor

    # ------------------------------
    # Display
    # ------------------------------

    if raw_toggle:

        st.text_area(
            "CSV Text",
            height=450,
            key="sotw_editor",
        )

        st.session_state.sotw_text = st.session_state.sotw_editor

    else:

        try:

            if st.session_state.sotw_text.strip():

                df = pd.read_csv(StringIO(st.session_state.sotw_text))

                st.dataframe(
                    df,
                    use_container_width=True,
                    height=450
                )

            else:

                st.text_area(
                    "CSV Text",
                    height=450,
                    key="sotw_editor",
                )

                st.session_state.sotw_text = st.session_state.sotw_editor

        except Exception:

            st.warning(
                "⚠️ CSV could not be parsed — enable Raw Text mode to edit."
            )

            st.text_area(
                "CSV Text",
                height=450,
                key="sotw_editor",
            )

            st.session_state.sotw_text = st.session_state.sotw_editor

# ------------------------------
# Evaluate Button
# ------------------------------

st.divider()

evaluate_button = st.button(
    "Evaluate Policy",
    use_container_width=True
)

# ------------------------------
# Evaluation Logic
# ------------------------------

if evaluate_button:

    policy_text = st.session_state.policy_text
    sotw_text = st.session_state.sotw_text

    if not policy_text.strip():
        st.error("⚠️ Please paste or upload an ODRL policy.")
        st.stop()

    if not sotw_text.strip():
        st.error("⚠️ Please paste or upload a SotW CSV.")
        st.stop()

    try:

        # Detect format
        if policy_text.strip().startswith("{"):
            policy_suffix = ".json"
        else:
            policy_suffix = ".ttl"

        # Save temp files
        with tempfile.NamedTemporaryFile(
            suffix=policy_suffix,
            delete=False,
            mode="w",
            encoding="utf-8"
        ) as policy_file:

            policy_file.write(policy_text)
            policy_path = policy_file.name

        with tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False,
            mode="w",
            encoding="utf-8"
        ) as sotw_file:

            sotw_file.write(sotw_text)
            sotw_path = sotw_file.name

        # Run evaluation
        with st.spinner("Evaluating policy..."):

            (
                evaluation_state,
                is_valid,
                rows_violating_permissions,
                rows_violating_prohibitions,
                obligations_not_satisfied,
                unfulfilled_duties,
                unfulfilled_consequences,
                unfulfilled_remedies,
            ) = Evaluator.evaluate_ODRL_from_files_merge_policies(
                [policy_path],
                sotw_path,
            )

        st.divider()

        if is_valid:
            st.success("✅ YES — State of the World is VALID")
        else:
            st.error("❌ NO — State of the World is NOT VALID")

        st.subheader("Evaluation Summary")

        if rows_violating_permissions:
            st.subheader("Rows violating permissions")
            st.write(rows_violating_permissions)

        if rows_violating_prohibitions:
            st.subheader("Rows violating prohibitions")
            st.write(rows_violating_prohibitions)

        if obligations_not_satisfied:
            st.subheader("Unsatisfied obligations")
            st.json(obligations_not_satisfied)

        if unfulfilled_duties:
            st.subheader("Unfulfilled duties")
            st.json(unfulfilled_duties)

        if unfulfilled_consequences:
            st.subheader("Unfulfilled consequences")
            st.json(unfulfilled_consequences)

        if unfulfilled_remedies:
            st.subheader("Unfulfilled remedies")
            st.json(unfulfilled_remedies)

    except Exception as e:

        st.error(f"⚠️ Evaluation error: {e}")

    finally:

        if "policy_path" in locals():
            if os.path.exists(policy_path):
                os.remove(policy_path)

        if "sotw_path" in locals():
            if os.path.exists(sotw_path):
                os.remove(sotw_path)