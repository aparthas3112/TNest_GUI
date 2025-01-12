import streamlit as st
import json

# Recommended values for standard setup
RECOMMENDED_VALUES = {
    "Power Law Red Noise": {
        "amplitude": {"min_value": -18, "max_value": -10},
        "spectral_index": {"min_value": 0, "max_value": 7},
    },
    "Power Law DM Noise": {
        "amplitude": {"min_value": -18, "max_value": -10},
        "spectral_index": {"min_value": 0, "max_value": 7},
    },
    "EFAC": {
        "global": {"min_value": -1, "max_value": 0.7},
        "per_flag": {"min_value": -1, "max_value": 0.7},
    },
    "EQUAD": {
        "global": {"min_value": -9, "max_value": -3},
        "per_flag": {"min_value": -9, "max_value": -3},
    },
}

st.title("TempoNest JSON Configuration File Generator")

# Globals
st.header("Globals")
col1, col2 = st.columns(2)
with col1:
    root = st.text_input("Root", value="results/TNest-")
    use_original_errors = st.checkbox("Use Original Errors", value=True)
with col2:
    num_tempo2_its = st.number_input("Number of Tempo2 Iterations", value=1, min_value=1, step=1)

# Sampler
st.header("Sampler")
col1, col2 = st.columns(2)
with col1:
    sampler_id = st.selectbox("Sampler ID", ["multinest", "polychord"], index=0)
    sample = st.checkbox("Sample", value=True)
with col2:
    importance_sampling = st.number_input("Importance Sampling", value=0, min_value=0, step=1)
    constant_efficiency = st.checkbox("Constant Efficiency", value=False)

col1, col2 = st.columns(2)
with col1:
    efficiency = st.number_input("Efficiency", value=0.1, min_value=0.0, max_value=1.0, step=0.01)
with col2:
    live_points = st.number_input("Live Points", value=4000, min_value=1, step=1)

# Elements
st.header("Elements")
elements = []
element_types = ["Timing Model", "Power Law Red Noise", "Power Law DM Noise", "EFAC", "EQUAD"]

num_elements = st.number_input("Number of Elements", value=1, min_value=1, step=1)

for i in range(num_elements):
    st.subheader(f"Element {i + 1}")
    col1, col2 = st.columns(2)
    with col1:
        element_name = st.selectbox(f"Element Name {i + 1}", element_types, key=f"element_name_{i}")

    parameters = []
    if element_name in ["EFAC", "EQUAD"]:
        selected_model = st.radio(
            f"Select Model Type for {element_name}",
            ("Global", "Per Flag"),
            key=f"model_type_{i}"
        )

        if selected_model == "Global":
            col1, col2 = st.columns(2)
            with col1:
                min_value = st.number_input(f"Global Min Value for {element_name}", value=RECOMMENDED_VALUES[element_name]["global"]["min_value"], key=f"global_min_{i}")
            with col2:
                max_value = st.number_input(f"Global Max Value for {element_name}", value=RECOMMENDED_VALUES[element_name]["global"]["max_value"], key=f"global_max_{i}")

            parameters.append({
                "name": "global",
                "description": f"global scaling for {element_name.lower()} error bars",
                "prior_type": "uniform" if element_name == "EFAC" else "log_uniform",
                "include": True,
                "fit": True,
                "min_value": min_value,
                "max_value": max_value,
            })

        elif selected_model == "Per Flag":
            col1, col2, col3 = st.columns(3)
            with col1:
                min_value = st.number_input(f"Per Flag Min Value for {element_name}", value=RECOMMENDED_VALUES[element_name]["per_flag"]["min_value"], key=f"per_flag_min_{i}")
            with col2:
                max_value = st.number_input(f"Per Flag Max Value for {element_name}", value=RECOMMENDED_VALUES[element_name]["per_flag"]["max_value"], key=f"per_flag_max_{i}")
            with col3:
                flag = st.text_input(f"Flag for {element_name}", value="-fe", key=f"per_flag_flag_{i}")

            parameters.append({
                "name": "per_flag",
                "description": f"per flag model for {element_name.lower()} error bars",
                "prior_type": "uniform" if element_name == "EFAC" else "log_uniform",
                "include": True,
                "fit": True,
                "min_value": min_value,
                "max_value": max_value,
                "flag": flag,
            })

    elif element_name in RECOMMENDED_VALUES:
        for param_name, param_vals in RECOMMENDED_VALUES[element_name].items():
            col1, col2 = st.columns(2)
            with col1:
                include = st.checkbox(f"Include {param_name}", value=True, key=f"include_{i}_{param_name}")
                fit = st.checkbox(f"Fit {param_name}", value=True, key=f"fit_{i}_{param_name}")
            with col2:
                min_value = st.number_input(f"{param_name} Min Value", 
                                            value=param_vals["min_value"], 
                                            key=f"min_{i}_{param_name}")
                max_value = st.number_input(f"{param_name} Max Value", 
                                            value=param_vals["max_value"], 
                                            key=f"max_{i}_{param_name}")
            parameters.append({
                "name": param_name,
                "prior_type": "log_uniform" if param_name in ["amplitude", "global", "per_flag"] else "uniform",
                "include": include,
                "fit": fit,
                "min_value": min_value,
                "max_value": max_value,
            })
    elements.append({"name": element_name, "parameters": parameters})

# Generate JSON
if st.button("Generate JSON"):
    config = {
        "globals": {
            "root": root,
            "use_original_errors": use_original_errors,
            "num_tempo2_its": num_tempo2_its,
        },
        "sampler": {
            "id": sampler_id,
            "sample": sample,
            "importance_sampling": importance_sampling,
            "constant_efficiency": constant_efficiency,
            "efficiency": efficiency,
            "live_points": live_points,
        },
        "elements": elements,
    }
    st.session_state.generated_json = json.dumps(config, indent=4)

# Input for the filename
file_name = st.text_input("Specify the name of the config file to save as", value="temponest_config.json")

# Display the generated JSON if available
if "generated_json" in st.session_state:
    st.subheader("Generated JSON")
    st.json(json.loads(st.session_state.generated_json))
    st.download_button(
        label="Download JSON File",
        data=st.session_state.generated_json,
        file_name=file_name,
        mime="application/json"
    )
