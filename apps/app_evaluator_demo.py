import streamlit as st
import tempfile
import os
import pandas as pd
from io import StringIO

# Import evaluator
import ODRL_Evaluator as Evaluator

# ------------------------------
# Page setup
# ------------------------------

st.set_page_config(
    page_title="ODRL Policy Evaluator",
    layout="wide"
)

st.title("ODRL Policy Evaluator DEMO")

st.markdown(
    "This is a DEMO of the [DIPS ODRL Policy Evaluator](https://github.com/paolo7/ODRL-Engine) from the University of Southampton."
)

st.markdown(
    "Paste or upload an **ODRL Policy** and a **State of the World**, then evaluate."
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

        content = uploaded_sotw.read().decode("utf-8")

        if content != st.session_state.sotw_text:
            st.session_state.sotw_text = content
            st.session_state.raw_toggle = False
            st.rerun()

    # Detect multiline manual input
    if (
        st.session_state.raw_toggle
        and st.session_state.sotw_text.count("\n") >= 1
    ):
        st.session_state.raw_toggle = False
        st.rerun()

    # ------------------------------
    # Raw Toggle (fixed behavior)
    # ------------------------------

    raw_toggle = st.toggle(
        "Raw Text",
        key="raw_toggle"
    )

    # ------------------------------
    # Display
    # ------------------------------

    if raw_toggle:

        sotw_text = st.text_area(
            label="CSV Text",
            height=450,
            key="sotw_text"
        )

    else:

        try:

            if st.session_state.sotw_text.strip():

                df = pd.read_csv(
                    StringIO(st.session_state.sotw_text)
                )

                st.dataframe(
                    df,
                    use_container_width=True,
                    height=450
                )

            else:

                st.text_area(
                    label="CSV Text",
                    height=450,
                    key="sotw_text"
                )

        except Exception:

            st.warning(
                "⚠️ CSV could not be parsed — enable Raw Text mode to edit."
            )

            st.text_area(
                label="CSV Text",
                height=450,
                key="sotw_text"
            )

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

            is_valid, violations, message = (
                Evaluator.evaluate_ODRL_from_files_merge_policies(
                    [policy_path],
                    sotw_path
                )
            )

        st.divider()

        if is_valid:
            st.success("✅ YES — State of the World is VALID")
        else:
            st.error("❌ NO — State of the World is NOT VALID")

        st.text_area(
            label="Evaluation Details",
            value=message,
            height=250
        )

    except Exception as e:

        st.error(f"⚠️ Evaluation error: {e}")

    finally:

        if "policy_path" in locals():
            if os.path.exists(policy_path):
                os.remove(policy_path)

        if "sotw_path" in locals():
            if os.path.exists(sotw_path):
                os.remove(sotw_path)