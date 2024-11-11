"""
Plotting functions.


NOTE:

- Signal quality in plot_ecg_segment() should be interpreted with extra caution due to 
the limitations mentioned in the function signal_quality on the neurokit2 site:
https://neuropsychology.github.io/NeuroKit/functions/ecg.html
"""

# fmt: off
from typing import Dict, Tuple, Union, List, Optional, Any
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
# fmt: on



############################
#### PLOTTING FUNCTIONS ####
############################

def plot_ecg_segment(df: pd.DataFrame, output_file: Union[Path, str], figure_title:str="") -> plt.Figure:
    """
    Plots an ECG segment showing the raw and the preprocessed ECG signal with marked R-peaks, and saves the plot as a PNG file.

    Args:
        df (pd.DataFrame): A DataFrame containing the ECG data. It must include the following columns:
            - 'ECG_Raw': The raw ECG signal.
            - 'ECG_Clean': The cleaned ECG signal.
            - 'ECG_R_Peaks': R-peak annotations (1 where peaks are detected, 0 otherwise).
        output_file (Union[Path, str]): The file path where the plot image will be saved.

    Raises:
        ValueError: If the required columns are missing from the input DataFrame.

    Returns:
        plt.Figure: The matplotlib figure object for the created plot.
    """
    expected_columns = ['ECG_Raw', 'ECG_Clean', 'ECG_R_Peaks']
    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' is missing from the DataFrame.")
        
    sample_start_index = df.index.min()
    sample_stop_index = df.index.max()
    fig, axes = plt.subplots(2, 1, figsize=(13, 6), constrained_layout=True)
    
    plt.suptitle(f'{figure_title}: ECG Segment from {sample_start_index} to {sample_stop_index} seconds', fontsize=16, x = 0.2)
    
    axes[0].set_title(f'Raw ECG')
    axes[0].plot(df['ECG_Raw'], color = 'k')
    axes[0].set_xlabel('Time in seconds')
    axes[0].set_ylabel('mV')

    axes[1].set_title(f'Cleaned ECG')
    axes[1].plot(df['ECG_Clean'], color = 'k')
    axes[1].set_xlabel('Time in seconds')
    axes[1].set_ylabel('mV')
    for index, row_series in df.iterrows():
        if row_series['ECG_R_Peaks'] == 1:
            axes[1].scatter(row_series.name, row_series['ECG_Clean'], color='red', marker='v', zorder=3)
   
    # Save the plot
    plt.savefig(output_file, dpi=135, bbox_inches='tight')
    plt.close()

    return fig
