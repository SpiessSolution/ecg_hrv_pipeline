"""
This module contains functions for processing ECG signals using NeuroKit2. It essentially wraps NeuroKit2 functions
"""

# fmt: off
from typing import Dict, Tuple, Union, List, Optional, Any
import neurokit2 as nk
import pandas as pd
import numpy as np
from pathlib import Path
import parameters as params
import common
import data_utils
import plot_utils
# fmt: on

######################################
##### HIGH LEVEL ENTRY FUNCTIONS  ####
######################################

def process_dyad(ecg_filepath: Union[str, Path],
                 event_filepath: Union[str, Path], 
                 parameters: Dict,
                 data_output_dir: Union[str, Path], 
                 figure_output_dir: Optional[Union[str, Path]],
                    ) -> None:
    """
    Main entry function for processing a dyads (mnother and child) ECG data.
    Processes ECG data for a specific subject, applying preprocessing and HRV analysis 
    for both child and mother ECG signals, and saving the results to the specified output 
    directories.

    Args:
        filepath (Union[str, Path]): The path to the file containing ECG data for child and mother.
        child_params (Dict): Parameter dictionary for processing the child ECG data, including
            settings for signal cleaning, peak detection, and HRV metrics.
        mother_params (Dict): Parameter dictionary for processing the mother ECG data, including
            settings for signal cleaning, peak detection, and HRV metrics.
        data_output_dir (Union[str, Path]): Directory where processed data and analysis results
            will be saved.
        qa_output_dir (Optional[Union[str, Path]]): Directory where quality assurance (QA) plots 
            will be saved if export of QA figures is enabled in the parameters.

    Returns:
        None

    Raises:
        KeyError: If required keys are missing from the parameter dictionaries.
        FileNotFoundError: If the specified filepath does not exist.

    Workflow:
        - Initializes output directories based on the subject ID and condition derived from the filepath.
        - Loads ECG data for child and mother, preparing it for analysis.
        - Preprocesses and analyzes ECG signals, generating HRV metrics and saving them to files.
        - Exports the configuration parameters and optionally saves QA figures if enabled.
    """
    # Some basic checks
    subject_id_ecg, condition_ecg = data_utils.extract_subject_id_condition_from_filepath(ecg_filepath)
    subject_id_event, condition_event = data_utils.extract_subject_id_condition_from_filepath(event_filepath)
    assert subject_id_ecg == subject_id_event, "Subject IDs do not match"
    assert condition_ecg == condition_event, "Conditions do not match"
    
    
    # Load and prepare data
    signal_event_df = data_utils.load_dyad_ecg_events(ecg_filepath, event_filepath)
    child_series, mother_series = data_utils.split_in_child_mother_series(signal_event_df)

    # prepare parameters
    segmentation_params = params.configure_segmentation_params(subject_id_ecg, parameters)
    child_params, mother_params = params.configure_ecg_params(subject_id_ecg, segmentation_params.copy())
    
    # Create output directories -> subjects are actually dyads but both go in same folder
    data_output_dir = data_output_dir / f"{condition_ecg}{subject_id_ecg}"
    data_output_dir.mkdir(parents=True, exist_ok=True)
    qa_reports_dir = figure_output_dir / f"{condition_ecg}{subject_id_ecg}"
    qa_reports_dir.mkdir(parents=True, exist_ok=True)

    # Preprocess ECG data
    child_signals_df = ecg_preprocess(child_series, child_params)
    mother_signals_df = ecg_preprocess(mother_series, mother_params)
    
    # Join the preprocessed signals with the events
    child_signal_event_df = child_signals_df.merge(signal_event_df[["event", "event_description"]], left_index=True, right_index=True, how = "left")
    mother_signal_event_df = mother_signals_df.merge(signal_event_df[["event", "event_description"]], left_index=True, right_index=True, how = "left")
    
    # segment the dataframes
    child_segments_df_list = data_utils.segment_df(child_signal_event_df, segmentation_params)
    mother_segments_df_list = data_utils.segment_df(mother_signal_event_df, segmentation_params)
    
    # Compute windowed HRV metrics per segment and subject
    compute_windowed_hrv_across_segments(
        segments_df_list=child_segments_df_list,
        parameters=child_params,
        figure_output_dir=qa_reports_dir,
        data_output_dir=data_output_dir,
        subject_pair="child"
    )
    
    compute_windowed_hrv_across_segments(
        segments_df_list=mother_segments_df_list,
        parameters=mother_params,
        figure_output_dir=qa_reports_dir,
        data_output_dir=data_output_dir,
        subject_pair="mother"
    )

    # Save the parameters
    common.export_to_yaml(child_params, data_output_dir/'child_params.yml')
    common.export_to_yaml(mother_params, data_output_dir/'mother_params.yml')
    
def compute_windowed_hrv_across_segments(segments_df_list: List[pd.DataFrame], 
                                         parameters: Dict, 
                                         figure_output_dir: Union[str, Path],
                                         data_output_dir: Union[str, Path],
                                         subject_pair: str
                                         ) -> None:
    figure_output_dir = Path(figure_output_dir)
    data_output_dir = Path(data_output_dir)
    
    # Compute windowed HRV metrics per segment and subject
    for segment_df in segments_df_list:
        segment_name = segment_df["event_description"].iloc[0]
        hrv_segment_metrics_df = calculate_windowed_HRV_metrics(segment_df, 
                                                                parameters, 
                                                                export_segment_plot = True,
                                                                figure_output_dir = figure_output_dir / subject_pair, 
                                                                segment_name=segment_name
                                                                )
        # save HRV metrics
        hrv_segment_metrics_df.to_excel(data_output_dir / f'{subject_pair}_{segment_name}_metrics.xlsx', index=False)
        # save preprocessed data
        segment_df.to_csv(data_output_dir / f'{subject_pair}_{segment_name}_signals.csv')


######################################
##### ECG PREPROCESSING FUNCTIONS ####
######################################

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
    Calculates Heart Rate Variability (HRV) metrics over specified analysis windows, optionally plotting and saving ECG segments.

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
    expected_columns = ['ECG_Raw', 'ECG_Clean', 'ECG_Quality', 'ECG_R_Peaks']
    for col in expected_columns:
        if col not in signals_df.columns:
            raise ValueError(f"Column '{col}' is missing from the DataFrame.")
        
    # Setup window size
    window_size = int(parameters['general']['analysis_window_seconds'] * parameters['general']['sampling_frequency'])
    hrv_indices_df = pd.DataFrame()
    
    # Calculate metrics per analysis window
    for window_count, peaks_analysis_window_df in enumerate(data_utils.iterate_batches(signals_df, window_size)):
        # Some segment info
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
            Path(figure_output_dir).mkdir(parents=False, exist_ok=True)
            plot_utils.plot_ecg_segment(peaks_analysis_window_df, 
                             figure_output_dir / f"{segment_name}_segment_{window_count}.png",
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
    signal_quality = calculate_signal_quality(ecg_cleaned_series, rpeaks['ECG_R_Peaks'], parameters)
    
    # Create a composite dataframe containing the entire signal and peak information
    signals_df = pd.concat([
            ecg_cleaned_series.to_frame(),
            raw_ecg_series.to_frame(),
            peak_df
        ], axis=1)
    signals_df = signals_df.assign(ECG_Quality=signal_quality)
    signals_df.index = time_index
    
    return signals_df


