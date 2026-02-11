#  !git clone https://github.com/paolo7/ODRL-Engine.git
#  %cd ODRL-Engine
#  from setup_colab import setup, show_interface
#  setup()
#  show_interface()

import os
import sys
import subprocess
import json
from google.colab import files
import ipywidgets as widgets
from IPython.display import display, clear_output


def run_cmd(cmd):
    print(f"\n[RUNNING] {cmd}")
    result = subprocess.run(cmd, shell=True, check=False, text=True)
    if result.returncode != 0:
        print(f"⚠️ Command failed: {cmd}")
    return result


def setup():
    print("🚀 Setting up ODRL-Engine environment in Google Colab...\n")

    # install dependencies
    run_cmd("pip install -r requirements.txt")
    run_cmd("pip install ipywidgets")

    # add repo to path
    sys.path.append(os.getcwd())

    # test imports
    print("\n✅ Testing imports...")
    global colab_functions
    import ipywidgets
    from IPython.display import display, HTML, clear_output

    print("✅ ODRL-Engine setup complete and all imports successful!")
    clear_output(wait=True)


class UploadState:
    filename = None
    content = None


def upload_file():
    uploaded = files.upload()
    # Enforce single file upload
    if len(uploaded) != 1:
        raise ValueError("Please upload exactly one file.")
    # Extract filename and content
    UploadState.filename = list(uploaded.keys())[0]
    UploadState.content = uploaded[UploadState.filename]
    print(f"✅ Uploaded: {UploadState.filename}")


def show_interface():
    import validate
    import ODRL_generator
    from colab_functions import visualise
    from colab_functions import graph_equality_comparison

    # --- DROPDOWN MENU ---
    dropdown = widgets.Dropdown(
        options=[
            ("Upload ODRL File", "upload"),
            ("File Info", "fileinfo"),
            ("Visualise Policy", "visualise"),
            ("Full ODRL Validation", "validate"),
            ("Graph Diff", "comparetriplebytriple"),
            ("Generate ODRL Policies", "ODRLgeneration"),
            ("Generate State of the World", "SotWgeneration"),
            ("Evaluate State of the World", "SotWevaluation"),
        ],
        description="Select:",
    )

    # --- RUN BUTTON ---
    run_button = widgets.Button(description="Run", button_style="success")
    output_run = widgets.Output()

    def on_run_clicked(b):
        with output_run:
            clear_output()
            selected = dropdown.value
            if selected == "upload":
                upload_file()
            elif selected == "visualise":
                if UploadState.filename and UploadState.content:
                    visualise.explore_policies_html()
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "fileinfo":
                if UploadState.filename and UploadState.content:
                    print(
                        f'User uploaded file "{UploadState.filename}" with length {len(UploadState.content)} bytes'
                    )
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "validate":
                if UploadState.filename:
                    validate.generate_ODRL_diagnostic_report(UploadState.filename)
                else:
                    print("⚠️ No ODRL file uploaded yet.")
            elif selected == "comparetriplebytriple":
                graph_equality_comparison.compare_rdf_files()
            elif selected == "ODRLgeneration":
                clear_output()  # clear output before showing new widgets

                # --- Helper function for labeled input ---
                def labeled_widget(label_text, widget):
                    return widgets.HBox(
                        [
                            widgets.Label(
                                value=label_text, layout=widgets.Layout(width="220px")
                            ),
                            widget,
                        ]
                    )

                # --- Input widgets ---
                policy_number_widget = widgets.IntText(value=1)
                p_rule_n_widget = widgets.IntText(value=2)
                f_rule_n_widget = widgets.IntText(value=2)
                o_rule_n_widget = widgets.IntText(value=1)
                constants_per_feature_widget = widgets.IntText(value=4)
                constraint_number_min_widget = widgets.IntText(value=0)
                constraint_number_max_widget = widgets.IntText(value=4)
                chance_feature_null_widget = widgets.FloatText(value=0.5)
                constraint_right_operand_min_widget = widgets.IntText(value=0)
                constraint_right_operand_max_widget = widgets.IntText(value=100)
                ontology_path_widget = widgets.Text(
                    value="sample_ontologies/ODRL_DPV.ttl"
                )

                # Wrap with labels
                widgets_list = [
                    labeled_widget("Number of Policies:", policy_number_widget),
                    labeled_widget("Number of Permission Rules:", p_rule_n_widget),
                    labeled_widget("Number of Prohibition Rules:", f_rule_n_widget),
                    labeled_widget("Number of Obligation Rules:", o_rule_n_widget),
                    labeled_widget(
                        "Constants per Feature (Actions/Parties/Targets):",
                        constants_per_feature_widget,
                    ),
                    labeled_widget(
                        "Minimum Constraints per Rule:", constraint_number_min_widget
                    ),
                    labeled_widget(
                        "Maximum Constraints per Rule:", constraint_number_max_widget
                    ),
                    labeled_widget(
                        "Chance Feature is Null (0-1):", chance_feature_null_widget
                    ),
                    labeled_widget(
                        "Constraint Right Operand Min:",
                        constraint_right_operand_min_widget,
                    ),
                    labeled_widget(
                        "Constraint Right Operand Max:",
                        constraint_right_operand_max_widget,
                    ),
                    labeled_widget("Ontology Path:", ontology_path_widget),
                ]

                # --- Buttons and outputs ---
                generate_button = widgets.Button(
                    description="Generate", button_style="success"
                )
                download_button = widgets.Button(
                    description="Download TTL", button_style="info"
                )
                download_button.disabled = True
                download_button.layout.opacity = "0.5"
                info_button = widgets.ToggleButton(
                    description="INFO", value=False, button_style="warning"
                )
                info_textarea = widgets.HTML(
                    value="""
                    <div style="font-family:Arial, sans-serif; line-height:1.6; max-width:700px;">
                        <h3>Policy Generation Parameters</h3>
                        <p><b>Number of Policies:</b> Number of policies to generate.<br>
                        Each policy will have its own set of rules and constraints but share the same sampled constants.</p>

                        <p><b>Number of Permission Rules:</b> How many permission rules each policy contains.<br>
                        Permissions specify allowed actions within the policy. Higher numbers create more permission nodes.</p>

                        <p><b>Number of Prohibition Rules:</b> How many prohibition rules each policy contains.<br>
                        Prohibitions restrict actions. Increasing this number makes policies more restrictive.</p>

                        <p><b>Number of Obligation Rules:</b> How many duty (obligation) rules each policy imposes.<br>
                        Duties define actions that must be performed.</p>

                        <p><b>Constants per Feature:</b> Number of actions, parties, targets and left operands (for constraints) sampled for all policies.<br>
                        Controls the diversity of IRIs used across rules. All policies share the same sampled constants for consistency while allowing randomness in rule assignment.</p>

                        <p><b>Minimum/Maximum Constraints per Rule:</b> Lower/Upper bound on the number of constraints per rule.<br>
                        Constraints refine rules using leftOperand, operator, and rightOperand, adding conditions to permissions, prohibitions, or obligations.</p>

                        <p><b>Chance Feature is Null (0-1):</b> Probability that a non-required feature (assignee or target) is omitted.<br>
                        A value closer to 1 means more features will be left empty, producing sparser and less specific rules.</p>

                        <p><b>Constraint Right Operand Min/Max:</b> Minimum/Maximum numeric value for randomly generated constraint rightOperands.<br>
                        Sets the lower bound for numeric thresholds used in constraints. Currently, all constraints are treated as numerical intervals.</p>

                        <p><b>Ontology Path:</b> Path to the TTL ontology file used for sampling IRIs.<br>
                        Ensures that all actions, parties, targets, and leftOperands come from an ontology and are realistic for policy generation.
                        Actions, parties, targets and leftOperands are currently defined as the subclasses and instances of odrl:Action, odrl:Party, odrl:Asset and odrl:LeftOperand, respectively.</p>
                    </div>
                    """,
                    layout=widgets.Layout(width="750px", height="450px"),
                    disabled=True,
                )

                output_generate = widgets.Output()
                policies_graph = None

                # --- Toggle INFO visibility ---
                def on_info_toggled(change):
                    if info_button.value:
                        display(info_textarea)
                    else:
                        info_textarea.close()  # hides the textarea

                info_button.observe(on_info_toggled, names="value")

                # Display all widgets
                display(
                    widgets.VBox(
                        widgets_list
                        + [
                            generate_button,
                            download_button,
                            info_button,
                            output_generate,
                        ]
                    )
                )

                # --- Generate button ---
                def on_generate_clicked(b):
                    nonlocal policies_graph
                    with output_generate:
                        clear_output()
                        try:
                            policies_graph = ODRL_generator.generate_ODRL(
                                policy_number=policy_number_widget.value,
                                p_rule_n=p_rule_n_widget.value,
                                f_rule_n=f_rule_n_widget.value,
                                o_rule_n=o_rule_n_widget.value,
                                constants_per_feature=constants_per_feature_widget.value,
                                constraint_number_min=constraint_number_min_widget.value,
                                constraint_number_max=constraint_number_max_widget.value,
                                chance_feature_null=chance_feature_null_widget.value,
                                constraint_right_operand_min=constraint_right_operand_min_widget.value,
                                constraint_right_operand_max=constraint_right_operand_max_widget.value,
                                ontology_path=ontology_path_widget.value,
                            )
                            turtle_output = policies_graph.serialize(format="turtle")
                            print(
                                turtle_output.decode("utf-8")
                                if isinstance(turtle_output, bytes)
                                else turtle_output
                            )
                            download_button.disabled = False
                            download_button.layout.opacity = "1.0"
                        except Exception as e:
                            print(f"⚠️ Error during generation: {e}")
                            download_button.disabled = True
                            download_button.layout.opacity = "0.5"

                generate_button.on_click(on_generate_clicked)

                # --- Download button ---
                def on_download_clicked(b):
                    if policies_graph is not None:
                        import tempfile
                        from google.colab import files

                        with tempfile.NamedTemporaryFile(
                            suffix=".ttl", delete=False
                        ) as tmp_file:
                            policies_graph.serialize(
                                destination=tmp_file.name, format="turtle"
                            )
                            tmp_file.flush()
                            files.download(tmp_file.name)

                download_button.on_click(on_download_clicked)
            elif selected == "SotWevaluation":
                clear_output()
                import ODRL_Evaluator as Evaluator
                from ODRL_Evaluator_updated import ODRLEvaluator
                import rdf_utils
                import SotW_generator
                import pandas as pd

                # ----------------------------
                # Local upload state
                # ----------------------------
                class SotWUploadState:
                    filename = None

                # ----------------------------
                # Output areas (DO NOT clear globally)
                # ----------------------------
                odrl_upload_out = widgets.Output()
                sotw_upload_out = widgets.Output()
                eval_out = widgets.Output()
                detail_eval_out = widgets.Output()
                stats_out = widgets.Output()

                result_box = widgets.Textarea(
                    layout=widgets.Layout(width="100%", height="250px"), disabled=True
                )
                detail_result_box = widgets.Textarea(
                    layout=widgets.Layout(width="100%", height="250px"), disabled=True
                )
                stats_box = widgets.Textarea(
                    layout=widgets.Layout(width="100%", height="250px"), disabled=True
                )

                # ----------------------------
                # Upload handlers
                # ----------------------------
                def upload_odrl_clicked(b):
                    with odrl_upload_out:
                        odrl_upload_out.clear_output()
                        uploaded = files.upload()
                        if len(uploaded) != 1:
                            print("⚠️ Please upload exactly one ODRL file.")
                            return
                        UploadState.filename = list(uploaded.keys())[0]
                        UploadState.content = uploaded[UploadState.filename]
                        print(f"✅ ODRL uploaded: {UploadState.filename}")

                def upload_sotw_clicked(b):
                    with sotw_upload_out:
                        sotw_upload_out.clear_output()
                        uploaded = files.upload()
                        if len(uploaded) != 1:
                            print("⚠️ Please upload exactly one CSV file.")
                            return
                        SotWUploadState.filename = list(uploaded.keys())[0]
                        print(f"✅ SotW CSV uploaded: {SotWUploadState.filename}")

                # ----------------------------
                # Evaluate handler
                # ----------------------------
                def on_evaluate_clicked(b):
                    with eval_out:
                        eval_out.clear_output()

                        if not UploadState.filename:
                            print("⚠️ No ODRL policy uploaded.")
                            return
                        if not SotWUploadState.filename:
                            print("⚠️ No SotW CSV uploaded.")
                            return

                        try:
                            # Load policy
                            graph = rdf_utils.load(UploadState.filename)[0]
                            policies = SotW_generator.extract_rule_list_from_policy(graph)
                            features = SotW_generator.extract_features_list_from_policy(graph)
                            feature_type_map = {f["iri"]: f["type"] for f in features}

                            # Load CSV
                            df = pd.read_csv(SotWUploadState.filename)

                            # Create evaluator
                            evaluator = ODRLEvaluator(policies, feature_type_map)

                            results = evaluator.evaluate_dataframe(df)
                            is_valid = all(r["decision"] != "DENY" for r in results)

                            validity_str = "YES" if is_valid else "NO"

                            messages = []
                            for r in results:
                                if r["decision"] == "DENY":
                                    messages.append(f"Row {r['row_index']} is NON-COMPLIANT")
                                else:
                                    messages.append(f"Row {r['row_index']} is COMPLIANT")

                            result_box.value = (
                                f"Is the State of the World valid? {validity_str}\n\n"
                                + "\n".join(messages)
                            )

                            print("✅ Evaluation completed.")

                        except Exception as e:
                            result_box.value = ""
                            print(f"⚠️ Evaluation error: {e}")


                def on_detail_evaluation_clicked(b):
                    with detail_eval_out:
                        detail_eval_out.clear_output()

                        if not UploadState.filename:
                            print("⚠️ No ODRL policy uploaded.")
                            return
                        if not SotWUploadState.filename:
                            print("⚠️ No SotW CSV uploaded.")
                            return

                        try:
                            graph = rdf_utils.load(UploadState.filename)[0]
                            policies = SotW_generator.extract_rule_list_from_policy(graph)
                            features = SotW_generator.extract_features_list_from_policy(graph)
                            feature_type_map = {f["iri"]: f["type"] for f in features}

                            df = pd.read_csv(SotWUploadState.filename)

                            evaluator = ODRLEvaluator(policies, feature_type_map)

                            results = evaluator.evaluate_dataframe(df)

                            overall_compliant = all(r["decision"] != "DENY" for r in results)
                            validity_str = "YES" if overall_compliant else "NO"

                            output_lines = [f"Is the State of the World valid? {validity_str}\n"]

                            deny_results = [r for r in results if r["decision"] == "DENY"]

                            if not deny_results:
                                output_lines.append("✅ No violations detected.")
                            else:
                                output_lines.append(f"⚠️ {len(deny_results)} violation(s) detected:\n")

                                for r in deny_results:
                                    output_lines.append(f"=== Row {r['row_index']} DENIED ===")

                                    for col, val in r["row_data"].items():
                                        output_lines.append(f"  {col}: {val}")

                                    output_lines.append(f"Policy: {r['policy_iri']}")
                                    output_lines.append(f"Reason: {r['reason']}")
                                    output_lines.append("-" * 60)

                            detail_result_box.value = "\n".join(output_lines)
                            print("✅ Detailed evaluation completed.")

                        except Exception as e:
                            detail_result_box.value = ""
                            print(f"⚠️ Evaluation error: {e}")

               
                def format_rowwise_stats(rowwise_stats):
                    lines = []
                    current_row = None

                    for stat in rowwise_stats:
                        if current_row != stat["row_index"]:
                            lines.append(f"\n=== Row {stat['row_index']} ===")
                            current_row = stat["row_index"]

                        lines.append(f"Policy: {stat['policy_iri']}")
                        lines.append(
                            f"  Permission satisfied: {stat['permission_satisfied_percentage']}%"
                        )
                        lines.append(
                            f"  Prohibition violated: {stat['prohibition_violated_percentage']}%"
                        )
                        lines.append(
                            f"  Permissions satisfied indices: {stat['permissions_satisfied_indices']}"
                        )
                        lines.append(
                            f"  Prohibitions violated indices: {stat['prohibitions_violated_indices']}"
                        )

                    return "\n".join(lines)
                def on_stats_evaluation_clicked(b):
                    with stats_out:
                        stats_out.clear_output()

                        if not UploadState.filename:
                            print("⚠️ No ODRL policy uploaded.")
                            return
                        if not SotWUploadState.filename:
                            print("⚠️ No SotW CSV uploaded.")
                            return

                        try:
                            graph = rdf_utils.load(UploadState.filename)[0]
                            policies = SotW_generator.extract_rule_list_from_policy(graph)
                            features = SotW_generator.extract_features_list_from_policy(graph)
                            feature_type_map = {f["iri"]: f["type"] for f in features}

                            df = pd.read_csv(SotWUploadState.filename)

                            evaluator = ODRLEvaluator(policies, feature_type_map)

                            rowwise_stats = evaluator.compute_statistics(df)

                            output = ["=== Policy Evaluation (Row-wise Statistics) ==="]
                            output.append(format_rowwise_stats(rowwise_stats))

                            stats_box.value = "\n".join(output)
                            print("✅ Statistics computed successfully.")

                        except Exception as e:
                            stats_box.value = ""
                            print(f"⚠️ Statistics computation error: {e}")


                # ----------------------------
                # Widgets
                # ----------------------------
                odrl_btn = widgets.Button(
                    description="Upload ODRL Policy", button_style="success"
                )
                sotw_btn = widgets.Button(
                    description="Upload SotW CSV", button_style="success"
                )
                eval_btn = widgets.Button(
                    description="Evaluate", button_style="warning"
                )
                detail_eval_btn = widgets.Button(
                    description="Detail", button_style="warning"
                )
                stats_eval_btn = widgets.Button(
                    description="Statistics", button_style="info"
                )

                odrl_btn.on_click(upload_odrl_clicked)
                sotw_btn.on_click(upload_sotw_clicked)
                eval_btn.on_click(on_evaluate_clicked)
                detail_eval_btn.on_click(on_detail_evaluation_clicked)
                stats_eval_btn.on_click(on_stats_evaluation_clicked)

                # ----------------------------
                # Layout (upload widget appears RIGHT BELOW button)
                # ----------------------------
                display(
                    widgets.VBox(
                        [
                            widgets.HTML(
                                "<b>Please upload an ODRL policy (if you haven't already)</b>"
                            ),
                            odrl_btn,
                            odrl_upload_out,
                            widgets.HTML(
                                "<br><b>Please upload a State of the World (SotW) file in CSV format.</b>"
                            ),
                            sotw_btn,
                            sotw_upload_out,
                            widgets.HTML("<br>"),
                            eval_btn,
                            eval_out,
                            widgets.HTML("<b>Evaluation Result:</b>"),
                            result_box,
                            widgets.HTML("<br>"),
                            detail_eval_btn,
                            detail_eval_out,
                            widgets.HTML("<b>Details of Non Compliance SoTWs:</b>"),
                            detail_result_box,
                            widgets.HTML("<br>"),
                            stats_eval_btn,
                            stats_out,
                            stats_box
                        ]
                    )
                )
            elif selected == "SotWgeneration":
                clear_output()  # clear output before showing new widgets
                import SotW_generator

                # --- Helper function for labeled input ---
                def labeled_widget(label_text, widget):
                    return widgets.HBox(
                        [
                            widgets.Label(
                                value=label_text, layout=widgets.Layout(width="220px")
                            ),
                            widget,
                        ]
                    )

                # --- Input widgets with DEFAULT values ---
                number_of_records_widget = widgets.IntText(value=100)
                valid_widget = widgets.Checkbox(value=True)
                chance_feature_empty_widget = widgets.FloatText(value=0.5)
                csv_file_widget = widgets.Text(value="sotw.csv")

                # Wrap widgets with labels
                widgets_list = [
                    labeled_widget("Number of Records:", number_of_records_widget),
                    labeled_widget("Valid:", valid_widget),
                    labeled_widget(
                        "Chance Feature Empty (0-1):", chance_feature_empty_widget
                    ),
                    labeled_widget("CSV Output Filename:", csv_file_widget),
                ]

                # Buttons
                generate_button = widgets.Button(
                    description="Generate", button_style="success"
                )
                download_button = widgets.Button(
                    description="Download CSV", button_style="info"
                )
                download_button.disabled = True
                download_button.layout.opacity = "0.5"

                # NEW: Show Rule Conditions toggle button
                show_rules_button = widgets.ToggleButton(
                    value=False,
                    description="Show Rule Conditions",
                    button_style="warning",
                )

                # Output areas
                output_generate = widgets.Output()
                rules_output_box = widgets.Output()  # shows rule conditions
                rules_output_box.layout.display = "none"  # initially hidden

                generated_csv_path = None

                # Display everything
                display(
                    widgets.VBox(
                        widgets_list
                        + [
                            generate_button,
                            download_button,
                            show_rules_button,
                            output_generate,
                            rules_output_box,
                        ]
                    )
                )

                # --- Generate button handler ---
                def on_generate_clicked(b):
                    nonlocal generated_csv_path
                    with output_generate:
                        clear_output()
                        if not UploadState.filename:
                            print("⚠️ No ODRL file uploaded yet.")
                            return
                        try:
                            SotW_generator.generate_state_of_the_world_from_policies_from_file(
                                file_path=UploadState.filename,
                                number_of_records=number_of_records_widget.value,
                                valid=valid_widget.value,
                                chance_feature_empty=chance_feature_empty_widget.value,
                                csv_file=csv_file_widget.value,
                            )
                            generated_csv_path = csv_file_widget.value
                            print(
                                f"✅ State of the World generated successfully: {generated_csv_path}"
                            )

                            download_button.disabled = False
                            download_button.layout.opacity = "1.0"

                        except Exception as e:
                            print(f"⚠️ Error during SotW generation: {e}")
                            download_button.disabled = True
                            download_button.layout.opacity = "0.5"

                generate_button.on_click(on_generate_clicked)

                # --- Download button handler ---
                def on_download_clicked(b):
                    if generated_csv_path:
                        try:
                            files.download(generated_csv_path)
                        except Exception as e:
                            with output_generate:
                                print(f"⚠️ Error downloading file: {e}")

                download_button.on_click(on_download_clicked)

                # --- Show Rule Conditions toggle handler ---
                def on_show_rules_clicked(change):
                    if show_rules_button.value:
                        # Show the box
                        rules_output_box.layout.display = "block"
                        with rules_output_box:
                            clear_output()

                            if not UploadState.filename:
                                print("⚠️ No ODRL file uploaded yet.")
                                return

                            try:
                                rules = SotW_generator.extract_rule_list_from_policy_from_file(
                                    UploadState.filename
                                )

                                print("\n Pretty Printed Rule Conditions\n")

                                def pretty_print_rules(rule_list):
                                    out_lines = []
                                    for rule in rule_list:
                                        out_lines.append(
                                            f"Policy IRI: {rule['policy_iri']}\n"
                                        )

                                        # permissions
                                        out_lines.append("    Permissions:")
                                        if rule["permissions"]:
                                            for cond_group in rule["permissions"]:
                                                out_lines.append(
                                                    "        Rule conditions:"
                                                )
                                                for cond in cond_group:
                                                    subj, op, obj = cond
                                                    out_lines.append(
                                                        f"            {subj} {op} {obj}"
                                                    )
                                        else:
                                            out_lines.append("        (none)")
                                        out_lines.append("")  # blank line

                                        # prohibitions
                                        out_lines.append("    Prohibitions:")
                                        if rule["prohibitions"]:
                                            for cond_group in rule["prohibitions"]:
                                                out_lines.append(
                                                    "        Rule conditions:"
                                                )
                                                for cond in cond_group:
                                                    subj, op, obj = cond
                                                    out_lines.append(
                                                        f"            {subj} {op} {obj}"
                                                    )
                                        else:
                                            out_lines.append("        (none)")
                                        out_lines.append("")  # blank line

                                        # obligations
                                        out_lines.append("    Obligations:")
                                        if rule["obligations"]:
                                            for cond_group in rule["obligations"]:
                                                out_lines.append(
                                                    "        Rule conditions:"
                                                )
                                                for cond in cond_group:
                                                    subj, op, obj = cond
                                                    out_lines.append(
                                                        f"            {subj} {op} {obj}"
                                                    )
                                        else:
                                            out_lines.append("        (none)")
                                        out_lines.append("")  # blank line

                                    return "\n".join(out_lines)

                                print(pretty_print_rules(rules))

                                print("\n Rule Conditions as JSON object\n")
                                print(json.dumps(rules, indent=4, ensure_ascii=False))
                                print("\n")

                            except Exception as e:
                                print(f"⚠️ Error extracting rule list: {e}")

                    else:
                        # Hide the rules
                        rules_output_box.layout.display = "none"

                show_rules_button.observe(on_show_rules_clicked, names="value")

    run_button.on_click(on_run_clicked)

    # --- DISPLAY EVERYTHING ---
    display(dropdown, run_button, output_run)


if __name__ == "__main__":
    setup()
    show_interface()
