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
element_types = ["Power Law Red Noise", "Power Law DM Noise", "EFAC", "EQUAD", "Timing Model"]

num_elements = st.number_input("Number of Elements", value=1, min_value=1, step=1)

for i in range(num_elements):
    st.subheader(f"Element {i + 1}")
    col1, col2 = st.columns(2)
    with col1:
        element_name = st.selectbox(f"Element Name {i + 1}", element_types, key=f"element_name_{i}")
    
    parameters = []
    if element_name in RECOMMENDED_VALUES:
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
    st.json(config)
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    st.success("JSON configuration file generated and saved as config.json!")
