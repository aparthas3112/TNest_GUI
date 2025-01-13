import os
import uuid
import zipfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import libstempo.toasim as lsim
import streamlit as st
import gc

class ResidualSimulator:
    def __init__(self):
        self.psr_combined = None

    def simulate_residuals_freq(self, X_days, freq, totaltime, avg_sn):
        """
        This injects white noise at a single frequency and returns a dataframe.
        """
        start_mjd = 56658  # MJD start time (2014)
        end_mjd = start_mjd + 365.25 * totaltime  # Total time span in years
        n_toas = int((end_mjd - start_mjd) / X_days)  # Number of TOAs

        mjds = np.linspace(start_mjd, end_mjd, n_toas)
        freqs = np.full(n_toas, freq)
        
        sn_ratios = np.clip(np.random.normal(loc=avg_sn, scale=5.0, size=n_toas), a_min=1e-3, a_max=None)
        toa_errors = (1.0 / sn_ratios)

        # Here fakepulsar is used because whitening is required.
        psr = lsim.fakepulsar(parfile="fake.par", obstimes=mjds, toaerr=toa_errors, freq=freqs)

        # Extract residuals, errors, and frequencies
        psr_toas = psr.toas()
        psr_residuals = psr.residuals() / 1e-6  # Convert to microseconds
        psr_errs = psr.toaerrs
        psr_freqs = psr.freqs

        # Create DataFrame
        data = pd.DataFrame({
            'Date': psr_toas,
            'Residual': psr_residuals,
            'Uncertainty': psr_errs,
            'Frequency': psr_freqs
        })

        return data

    def combine_residuals(self, data_list):
        """
        Combine residuals from different frequencies ensuring consistent data types.
        """
        for df in data_list:
            df['Date'] = df['Date'].astype(np.float64)
            df['Residual'] = df['Residual'].astype(np.float64)
            df['Uncertainty'] = df['Uncertainty'].astype(np.float64)
            df['Frequency'] = df['Frequency'].astype(np.float64)

        combined_data = pd.concat(data_list, ignore_index=True)
        combined_data = combined_data.sort_values(by=['Date', 'Frequency']).reset_index(drop=True)
        return combined_data

    def inject_dm_noise_on_combined(self, psr_combined, dm_noise_params, red_noise_params, efac_value):
        lsim.add_rednoise(psr_combined, *red_noise_params)  # Add red noise
        lsim.add_dm(psr_combined, *dm_noise_params)  # Add DM noise (freq-dependent)
        lsim.add_efac(psr_combined, efac=efac_value)  # Apply EFAC to combined residuals
        combined_residuals = psr_combined.residuals()
        combined_toaerrs = psr_combined.toaerrs
        return combined_residuals, combined_toaerrs

    def simulate_residuals(self, cadence_days, observing_freqs, red_noise_params, dm_noise_params, totaltime, efac_value):
        all_data = []
        for freq in observing_freqs:
            freq_data = self.simulate_residuals_freq(cadence_days, freq, totaltime, avg_sn)
            all_data.append(freq_data)

        combined_data = self.combine_residuals(all_data)

        self.psr_combined = lsim.fakepulsar(parfile="fake.par", obstimes=combined_data['Date'].values,
                                            toaerr=combined_data['Uncertainty'].values, freq=combined_data['Frequency'].values)

        combined_residuals, combined_toaerrs = self.inject_dm_noise_on_combined(self.psr_combined, dm_noise_params, red_noise_params, efac_value)

        combined_data['Residual'] = combined_residuals / 1e-6  # Convert to microseconds
        combined_data['Uncertainty'] = combined_toaerrs

        return combined_data

    @staticmethod
    def plot_residuals_by_frequency(data, frequency=None, legend=True):
        """
        Plots timing residuals with uncertainties colored by frequency for Streamlit.
        """
        unique_freqs = sorted(data['Frequency'].unique())
        markers = ['o', 's', '^', 'D', 'v', '*', 'P', 'X']  # Add more markers if needed
        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_freqs)))

        fig, ax = plt.subplots(figsize=(12, 6))

        if frequency is not None:
            if frequency in unique_freqs:
                freq_data = data[data['Frequency'] == frequency]
                ax.errorbar(freq_data['Date'], freq_data['Residual'], yerr=freq_data['Uncertainty'], 
                             fmt=markers[0], markersize=4, label=f'{frequency} MHz', 
                             color=colors[0], alpha=0.7)
            else:
                print(f"Frequency {frequency} MHz not found in the data.")
                return
        else:
            for i, (freq, color) in enumerate(zip(unique_freqs, colors)):
                freq_data = data[data['Frequency'] == freq]
                ax.errorbar(freq_data['Date'], freq_data['Residual'], yerr=freq_data['Uncertainty'], 
                             fmt=markers[i % len(markers)], markersize=4, label=f'{freq} MHz', 
                             color=color, alpha=0.7)

        ax.set_title('Timing Residuals with Uncertainties Colored by Frequency')
        ax.set_xlabel('Date (MJD)')
        ax.set_ylabel('Residuals (microseconds)')
        ax.grid(True)
        if legend:
            ax.legend(title="Frequency (MHz)", bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
        plt.tight_layout()
        return fig

# Cleanup existing files
for file in os.listdir():
    if file.endswith(('.zip', '.par', '.tim', '.txt', '.png')) and file != 'fake.par':
        os.remove(file)

# Streamlit App Setup
st.title("Pulsar Timing Residual Simulator")
st.sidebar.header("Simulation Parameters")

# Input Parameters
cadence_days = st.sidebar.slider("Cadence (days)", 5, 30, 10, step=1)
frequencies = st.sidebar.multiselect("Observing Frequencies (MHz)", [400, 600, 800, 1400, 1600], default=[1400, 800])
total_time = st.sidebar.slider("Total Time (years)", 1, 10, 5, step=1)
avg_sn = st.sidebar.slider("Average S/N Value", 5, 50, 20, step=1)
efec_value = st.sidebar.slider("EFAC Value", 1.0, 2.0, 1.2, step=0.1)

red_noise_amplitude_log = st.sidebar.slider("Red Noise Amplitude (log scale)", -18.0, -10.0, -14.0, step=1.0)
red_noise_amplitude = 10 ** red_noise_amplitude_log
red_noise_spectral_index = st.sidebar.slider("Red Noise Spectral Index", 0.0, 8.0, 4.0, step=0.1)

dm_noise_amplitude_log = st.sidebar.slider("DM Noise Amplitude (log scale)", -18.0, -10.0, -14.0, step=1.0)
dm_noise_amplitude = 10 ** dm_noise_amplitude_log
dm_noise_spectral_index = st.sidebar.slider("DM Noise Spectral Index", 0.0, 8.0, 4.0, step=0.1)

# File names for saving
par_file_name = st.sidebar.text_input("PAR File Name", value="temponest_sim.par")
tim_file_name = st.sidebar.text_input("TIM File Name", value="temponest_sim.tim")

# Persistent Simulator Instance
if "simulator" not in st.session_state:
    st.session_state.simulator = ResidualSimulator()
simulator = st.session_state.simulator

# Run Simulation Button
if st.sidebar.button("Run Simulation"):
    uid = str(uuid.uuid4())[:4]
    summary_file_name = f"simulation_summary_{uid}.txt"

    red_noise_params = (
        red_noise_amplitude,
        red_noise_spectral_index
    )

    dm_noise_params = (
        dm_noise_amplitude,
        dm_noise_spectral_index
    )

    simulated_data = simulator.simulate_residuals(
        cadence_days=cadence_days,
        observing_freqs=frequencies,
        red_noise_params=red_noise_params,
        dm_noise_params=dm_noise_params,
        totaltime=total_time,
        efac_value=efec_value
    )

    # Plot Results
    st.subheader("Timing Residuals")
    fig = simulator.plot_residuals_by_frequency(simulated_data)
    st.pyplot(fig)

    # Save Files as ZIP
    par_file_with_uid = f"{os.path.splitext(par_file_name)[0]}_{uid}.par"
    tim_file_with_uid = f"{os.path.splitext(tim_file_name)[0]}_{uid}.tim"
    residual_plot_file = f"residual_plot_{uid}.png"
    fig.savefig(residual_plot_file)

    # Save .par and .tim files
    if simulator.psr_combined is not None:
        simulator.psr_combined.savepar(par_file_with_uid)
        simulator.psr_combined.savetim(tim_file_with_uid)
    else:
        st.error("Pulsar data not available. Run the simulation first.")

    # Write summary file
    with open(summary_file_name, 'w') as summary_file:
        summary_file.write(f"Parameter\tValue\n")
        summary_file.write(f"Cadence (days)\t{cadence_days}\n")
        summary_file.write(f"Frequencies (MHz)\t{', '.join(map(str, frequencies))}\n")
        summary_file.write(f"Total Time (years)\t{total_time}\n")
        summary_file.write(f"Average S/N Value\t{avg_sn}\n")
        summary_file.write(f"EFAC Value\t{efec_value}\n")
        summary_file.write(f"Red Noise Amplitude\t{red_noise_amplitude} (log: {red_noise_amplitude_log})\n")
        summary_file.write(f"Red Noise Spectral Index\t{red_noise_spectral_index}\n")
        summary_file.write(f"DM Noise Amplitude\t{dm_noise_amplitude} (log: {dm_noise_amplitude_log})\n")
        summary_file.write(f"DM Noise Spectral Index\t{dm_noise_spectral_index}\n")

    zip_file_name = f"temponest_simulation_{uid}.zip"
    with zipfile.ZipFile(zip_file_name, 'w') as zipf:
        zipf.write(par_file_with_uid)
        zipf.write(tim_file_with_uid)
        zipf.write(residual_plot_file)
        zipf.write(summary_file_name)

    with open(zip_file_name, 'rb') as f:
        st.download_button(
            label="Download Simulation ZIP",
            data=f.read(),
            file_name=zip_file_name,
            mime="application/zip"
        )

    # Cleanup
    os.remove(par_file_with_uid)
    os.remove(tim_file_with_uid)
    os.remove(residual_plot_file)
    os.remove(summary_file_name)
    os.remove(zip_file_name)
