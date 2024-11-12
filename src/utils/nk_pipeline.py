"""
This module contains functions for processing ECG signals and computing HRV metrics using NeuroKit2. 
It essentially wraps NeuroKit2 functions
"""

# fmt: off
from typing import Dict, Tuple, Union, List, Optional
import neurokit2 as nk
import pandas as pd
import numpy as np
from pathlib import Path
import utils.plot_utils as plot_utils
# fmt: on


####################################################
##### ECG PREPROCESSING AND ANALSYSIS FUNCTIONS ####
####################################################

def clean_ecg(ecg_raw_series: pd.Series, parameters: Dict, **kwargs) -> pd.Series:
    """
    Cleans the ECG signal using NeuroKit2's `ecg_clean` function based on the provided parameters.

    Args:
        ecg_raw_series (pd.Series): The raw ECG signal as a pandas Series.
        parameters (dict): A dictionary containing the cleaning parameters. Expected keys:
            - 'sampling_frequency' (int): The sampling frequency of the ECG data.
            - 'cleaning' (dict): A dictionary with the cleaning method and powerline frequency.
                - 'method' (str): The cleaning method to use (e.g., 'neurokit', 'biosppy', 'elgendi', etc.).
                - 'powerline' (float): The powerline frequency to be removed during cleaning (only applicable for some methods).
        **kwargs: Additional method-specific parameters for `ecg_clean`.

    Returns:
        pd.Series: The cleaned ECG signal as a pandas Series.
    """
    if not isinstance(ecg_raw_series, pd.Series):
        raise ValueError("The 'ecg_raw_series' argument must be a pandas Series.")
    
    cleaned_series = pd.Series(
        nk.ecg_clean(
            ecg_raw_series, 
            sampling_rate=parameters['general'].get('sampling_frequency', 500), 
            method=parameters['cleaning'].get('method', 'neurokit'),
            powerline=parameters['cleaning'].get('powerline', 50),  # Optional powerline filtering
            **kwargs  # additional method-specific parameters
        )
    )
    cleaned_series.name = 'ECG_Clean'
    return cleaned_series

def find_peaks(ecg_cleaned_series: pd.Series, parameters: Dict, **kwargs) -> Tuple[pd.DataFrame, dict]:
    """
    Detects R-peaks in a cleaned ECG signal using NeuroKit2's `ecg_peaks` function based on the provided parameters.

    Args:
        ecg_cleaned_series (pd.Series): The cleaned ECG signal as a pandas Series.
        parameters (dict): A dictionary containing the peak detection parameters. Expected keys:
            - 'sampling_frequency' (int): The sampling frequency of the ECG data.
            - 'peak_detection' (dict): A dictionary with the peak detection method and artifact correction settings.
                - 'method' (str): The peak detection method to use.
                - 'correct_artifacts' (bool): Whether to apply artifact correction during peak detection.
        **kwargs: Additional method-specific parameters for `ecg_peaks`.

    Returns:
        Tuple[pd.DataFrame, dict]:
            - pd.DataFrame: A DataFrame of the same length as the input ECG signal, with occurrences of R-peaks marked as 1 in a list of zeros.
              Accessible with the key "ECG_R_Peaks".
            - dict: A dictionary containing additional information:
              - "ECG_R_Peaks": The samples at which R-peaks occur.
              - "sampling_rate": The sampling rate of the signal.
              - "method" etc...
    """
    signal_df, peaks_dict = nk.ecg_peaks(
        ecg_cleaned=ecg_cleaned_series,
        sampling_rate=parameters['general'].get('sampling_frequency', 500),
        method=parameters['peak_detection'].get('method', 'neurokit'),
        correct_artifacts=parameters['peak_detection'].get('correct_artifacts', False),
        **kwargs
    )
    
    return signal_df, peaks_dict

def calculate_heartrate(peak_df: pd.DataFrame, parameters: Dict) -> float:
    """
    Calculate the average heart rate in beats per minute (BPM) based on detected R-peaks.
    
    Args:
        signal_df (pd.DataFrame): DataFrame containing R-peak information with a column named 'ECG_R_Peaks'.
            This DataFrame should be the output of the `find_peaks` function (i.e., signal_df).
        parameters (Dict): A dictionary containing relevant parameters for the calculation.
            - 'sampling_frequency' (int): The sampling frequency of the ECG signal in Hz. Defaults to 500 Hz.
    
    Returns:
        float: The average heart rate in beats per minute (BPM).
    
    Example:
        >>> heart_rate = calculate_heartrate(peaks_df, parameters)
    """
    assert isinstance(peak_df, pd.DataFrame), "The 'peaks_df' argument must be a pandas DataFrame."
    assert 'ECG_R_Peaks' in peak_df.columns, "The 'peaks_df' DataFrame must contain a column named 'ECG_R_Peaks'."

    sampling_frequency = parameters['general'].get('sampling_frequency', 500)
    signal_length_seconds = len(peak_df) / sampling_frequency
    peak_count = peak_df['ECG_R_Peaks'].sum()
    
    # Calculate the average heart rate in beats per minute (BPM)
    return (60 / signal_length_seconds) * peak_count

def calculate_signal_quality(ecg_cleaned_series: pd.Series, rpeaks: Optional[Union[Tuple, List]], parameters: Dict) -> Union[np.array, str]:
    """
    Calculates the quality of the ECG signal using NeuroKit2's `ecg_quality` function based on the provided parameters.

    This function allows you to assess the quality of the ECG signal using various methods:
    
    - "averageQRS": Computes a continuous quality index by comparing the distance of each QRS segment from the average QRS segment in the data.
      A value of 1 indicates heartbeats that are closest to the average QRS, while 0 indicates the most distant. This index is relative and should be used with caution.
    - "zhao2018": Extracts several signal quality indices (SQIs) and classifies the signal into one of three categories: 
      Unacceptable, Barely acceptable, or Excellent. The indices include pSQI (QRS wave power spectrum distribution), kSQI (kurtosis), and basSQI (baseline relative power).

    Args:
        ecg_cleaned_series (pd.Series): The cleaned ECG signal as a pandas Series.
        rpeaks (Optional[Union[Tuple, List]]): The list or tuple of R-peak samples as returned by `ecg_peaks()`. If None, R-peaks will be computed from the signal.
        parameters (Dict): A dictionary of settings for the ECG quality calculation. Expected keys:
            - 'sampling_frequency' (int): The sampling frequency of the signal in Hz (samples per second). Defaults to 500 Hz.
            - 'signal_quality_index' (dict): Contains the signal quality index calculation parameters.
                - 'method' (str): The method to use for signal quality calculation. Can be "averageQRS" (default) or "zhao2018".
                - 'approach' (str, optional): The data fusion approach to use with the "zhao2018" method. Can be "simple" or "fuzzy". Defaults to "simple".

    Returns:
        Union[np.array, str]: 
            - If the "averageQRS" method is used, returns a vector of quality indices ranging from 0 to 1.
            - If the "zhao2018" method is used, returns a string classification of the signal quality: "Unacceptable", "Barely acceptable", or "Excellent".
    """
    signal_quality_array = nk.ecg_quality(
        ecg_cleaned=ecg_cleaned_series,
        rpeaks=rpeaks,
        sampling_rate=parameters['general'].get('sampling_frequency', 500),
        method=parameters['signal_quality_index'].get('method', 'averageQRS'),
        approach=parameters['signal_quality_index'].get('approach', 'simple')
    )
    
    return signal_quality_array

def calculate_hrv_indices(peak_df: pd.DataFrame, parameters: Dict) -> pd.DataFrame:
    """
    Calculates heart rate variability (HRV) indices from R-peak data using NeuroKit2's `hrv` functions.

    This function computes multiple HRV metrics across time, frequency, and non-linear domains based on
    provided R-peak data. It serves as a flexible wrapper for NeuroKit2's HRV analysis functions, allowing
    for customized sampling frequency and optional computation of frequency-domain metrics.

    Args:
        peak_df (pd.DataFrame): A DataFrame containing R-peak information, such as indices of peaks or
            results from functions like `ecg_peaks()` or `ppg_peaks()`. It may also include R-R intervals
            (RRI) and timestamps (RRI_Time).
        parameters (Dict): A dictionary specifying calculation settings. Expected keys include:
            - 'sampling_frequency' (int): Sampling frequency of the signal in Hz. Defaults to 500 Hz.
            - 'compute_hrv_frequency_metrics' (bool): Flag indicating whether to compute frequency-domain metrics.
              Defaults to False.
            - 'hrv_frequency_settings' (Dict): Settings for frequency-domain calculations if enabled, including:
                - 'ulf' (List[float]): Range for ultra-low-frequency (ULF) in Hz, e.g., [0, 0.0033].
                - 'vlf' (List[float]): Range for very-low-frequency (VLF) in Hz, e.g., [0.0033, 0.04].
                - 'lf' (List[float]): Range for low-frequency (LF) in Hz, e.g., [0.04, 0.15].
                - 'hf' (List[float]): Range for high-frequency (HF) in Hz, e.g., [0.15, 0.4].
                - 'vhf' (List[float]): Range for very-high-frequency (VHF) in Hz, e.g., [0.4, 0.5].
                - 'psd_method' (str): Method for power spectral density estimation (e.g., 'welch').
                - 'normalize' (bool): Flag to normalize LF and HF components. Defaults to True.

    Returns:
        pd.DataFrame: A DataFrame containing HRV indices. If respiratory data is included (e.g., output
        from `bio_process()`), respiratory sinus arrhythmia (RSA) indices are also added.

    Example:
        >>> parameters = {'general': {'sampling_frequency': 500, 'compute_hrv_frequency_metrics': True},
                          'hrv_frequency_settings': {'ulf': [0, 0.0033], 'vlf': [0.0033, 0.04],
                                                     'lf': [0.04, 0.15], 'hf': [0.15, 0.4],
                                                     'vhf': [0.4, 0.5], 'psd_method': 'welch'}}
        >>> peak_df = pd.DataFrame(...)  # R-peak indices
        >>> hrv_indices = calculate_hrv_indices(peak_df, parameters)

    Notes:
        - For accurate frequency-domain analysis, the sampling rate should be at least twice the highest
          frequency in the VHF domain.
        - To display plots, set `show=True` within `nk.hrv()` or `nk.hrv_frequency()` calls.

    References:
        - Pham et al. (2021). "HRV indices in cardiovascular and respiratory studies."
        - Frasch (2022). "Advanced HRV analysis in signal processing."

    """
    hrv_time = nk.hrv_time(
        peak_df,
        sampling_rate=parameters['general'].get('sampling_frequency', 500),
        show=False
    )
    
    if parameters['general'].get("compute_hrv_frequency_metrics", False):
        hrv_frequency = nk.hrv_frequency(
            peak_df,
            sampling_rate=parameters['general'].get('sampling_frequency', 500),
            ulf=parameters['hrv_frequency_settings'].get('ulf', [0, 0.0033]),
            vlf=parameters['hrv_frequency_settings'].get('vlf', [0.0033, 0.04]),
            lf=parameters['hrv_frequency_settings'].get('lf', [0.04, 0.15]),
            hf=parameters['hrv_frequency_settings'].get('hf', [0.15, 0.4]),
            vhf=parameters['hrv_frequency_settings'].get('vhf', [0.4, 0.5]),
            psd_method=parameters['hrv_frequency_settings'].get('psd_method', 'welch'),
            normalize=parameters['hrv_frequency_settings'].get('normalize', True),
            show=False
        )
        return pd.concat([hrv_time, hrv_frequency], axis=1)
    
    return hrv_time

def calculate_windowed_HRV_metrics(
    signals_df: pd.DataFrame, 
    parameters: Dict, 
    export_segment_plot: bool = False, 
    figure_output_dir: Union[Path, str] = Path().cwd()/"segment_figures",
    segment_name: str = ""
) -> pd.DataFrame:
    """
    Calculates Heart Rate Variability (HRV) metrics over specified analysis windows (e.g., non-overlapping windods of 30s), optionally plotting and saving ECG segments.

    Args:
        signals_df (pd.DataFrame): A DataFrame containing ECG signal data. It must include the following columns:
            - 'ECG_Raw': The raw ECG signal.
            - 'ECG_Clean': The cleaned ECG signal.
            - 'ECG_Quality': The quality of the ECG signal.
            - 'ECG_R_Peaks': R-peak annotations (1 where peaks are detected, 0 otherwise).
        parameters (Dict): A dictionary containing the analysis parameters, including:
            - 'general': A dictionary with general parameters like:
                - 'analysis_window_seconds': Duration of the analysis window in seconds.
                - 'sampling_frequency': Sampling frequency of the ECG signal.
        export_segment_plot (bool, optional): If True, will save a plot of each ECG segment. Default is False.
        figure_output_dir (Union[Path, str], optional): Directory where segment plots will be saved if `export_segment_plot` is True. Default is 'segment_figures' in the current working directory.

    Raises:
        ValueError: If the required columns are missing from the input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing HRV metrics for each analysis window. The DataFrame includes:
            - 'start_index': Start index of the analysis window.
            - 'stop_index': Stop index of the analysis window.
            - 'analysis_window': Window count (integer).
            - 'heart_rate_bpm': Calculated heart rate in beats per minute.
            - Other calculated HRV metrics depending on the implementation of `calculate_hrv_indices`.

    """
    # Check if expected columns are present
    expected_columns = ['ECG_Raw', 'ECG_Clean', 'ECG_R_Peaks']
    for col in expected_columns:
        if col not in signals_df.columns:
            raise ValueError(f"Column '{col}' is missing from the DataFrame.")
        
    # Setup window size
    window_size = int(parameters['general']['analysis_window_seconds'] * parameters['general']['sampling_frequency'])
    hrv_indices_df = pd.DataFrame()
    
    # Calculate metrics per analysis window
    for window_count, peaks_analysis_window_df in enumerate(iterate_batches(signals_df, window_size)):
        # Define window start and end based on the df's index, which should be in relative time (i.e., starting from 0)
        sample_start_index = peaks_analysis_window_df.index.min()
        sample_stop_index = peaks_analysis_window_df.index.max()
        
        # Calculate metrics
        try:
            heart_rate = calculate_heartrate(peaks_analysis_window_df, parameters)
            hrv_indices_tmp_df = calculate_hrv_indices(peaks_analysis_window_df, parameters)
            hrv_indices_tmp_df = (
                hrv_indices_tmp_df
                .assign(
                    start_index=sample_start_index, 
                    stop_index=sample_stop_index, 
                    analysis_window=window_count,
                    heart_rate_bpm=heart_rate
                )
            )
            
            # concatenate the metrics
            hrv_indices_df = pd.concat([hrv_indices_df, hrv_indices_tmp_df])
        except Exception as e:
            print(f"Error calculating HRV metrics for window {window_count}: {e}")
        
        # Visualize the segment if required
        if export_segment_plot:
            segment_name = segment_name.replace("/", "_")
            output_file = str(figure_output_dir / f"{segment_name}_{window_count}.png")
            Path(figure_output_dir).mkdir(parents=False, exist_ok=True)
            plot_utils.plot_ecg_segment(peaks_analysis_window_df, 
                             output_file,
                             figure_title=segment_name)
    # Return HRV metrics DataFrame
    return hrv_indices_df

def ecg_preprocess(raw_ecg_series: pd.Series, parameters: Dict) -> pd.DataFrame:
    """
    Preprocesses a raw ECG signal by cleaning it, detecting R-peaks, calculating signal quality, and returning a DataFrame containing
    the processed ECG data.

    The preprocessing involves the following steps:
    1. Cleaning the raw ECG signal using the `clean_ecg` function.
    2. Detecting R-peaks using the `find_peaks` function.
    3. Calculating the ECG signal quality using the `calculate_signal_quality` function.

    Args:
        raw_ecg_series (pd.Series): A pandas Series containing the raw ECG signal.
        parameters (Dict): A dictionary of parameters for the various preprocessing functions, including:
            - 'sampling_frequency' (int): The sampling frequency of the ECG data in Hz.
            - 'cleaning' (dict): Parameters for the `clean_ecg` function, such as cleaning method and powerline frequency.
            - 'peak_detection' (dict): Parameters for the `find_peaks` function, including peak detection method and artifact correction.
            - 'signal_quality_index' (dict): Parameters for the `calculate_signal_quality` function, such as the quality calculation method.

    Returns:
        pd.DataFrame: A DataFrame containing the following columns:
            - 'ECG_Raw': The original raw ECG signal.
            - 'ECG_Clean': The cleaned ECG signal.
            - 'ECG_R_Peaks': Detected R-peaks in the signal (marked with 1).
            - 'ECG_Quality': The calculated signal quality.

    Example:
        >>> parameters = {
                'general': {'sampling_frequency': 500},
                'cleaning': {'method': 'neurokit', 'powerline': 50},
                'peak_detection': {'method': 'neurokit', 'correct_artifacts': True},
                'signal_quality_index': {'method': 'averageQRS', 'approach': 'simple'}
            }
        >>> raw_ecg = pd.Series([...])  # A Series containing raw ECG data
        >>> processed_ecg_df = ecg_preprocess(raw_ecg, parameters)

    Raises:
        ValueError: If the input ECG series is not of type `pd.Series`.
    """
    raw_ecg_series.name = 'ECG_Raw'
    time_index = raw_ecg_series.index # if a dedicated time index is given, it probably arrives via the raw data. Since it will be lost in the other calculations, we store it here and re-assign it later
    raw_ecg_series = raw_ecg_series.reset_index(drop=True)
    
    ecg_cleaned_series = clean_ecg(raw_ecg_series, parameters)
    peak_df, rpeaks = find_peaks(ecg_cleaned_series, parameters)
    # signal_quality = calculate_signal_quality(ecg_cleaned_series, rpeaks['ECG_R_Peaks'], parameters)
    
    # Create a composite dataframe containing the entire signal and peak information
    signals_df = pd.concat([
            ecg_cleaned_series.to_frame(),
            raw_ecg_series.to_frame(),
            peak_df
        ], axis=1)
    # signals_df = signals_df.assign(ECG_Quality=signal_quality)
    signals_df.index = time_index
    
    return signals_df


##############
#### Misc ####
##############


def iterate_batches(df: pd.DataFrame, batch_size: int):
    """Iterates over a DataFrame in batches of a specific size.

    Args:
        df (pd.DataFrame): The DataFrame to iterate over.
        batch_size (int): The number of rows per batch.

    Yields:
        pd.DataFrame: A DataFrame representing the current batch.
    """
    for start in range(0, len(df), batch_size):
        yield df.iloc[start:start + batch_size]
