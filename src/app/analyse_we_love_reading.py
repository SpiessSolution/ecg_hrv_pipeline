#fmt:off
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent)) # the dir containing utils
import utils.parameters as params
import utils.common as common
import utils.nk_pipeline as nk_pipeline
import utils.data_utils as data_utils
import numpy as np
import pandas as pd
from datetime import datetime
import traceback
from typing import Dict, Union, Optional, List, Tuple
#fmt:on

def process_all_dyads(
    raw_data_dir: Union[str, Path] = Path(__file__).resolve().parent.parent.parent / 'data' / 'raw',
    processed_data_dir: Union[str, Path] = Path(__file__).resolve().parent.parent.parent / 'data' / 'processed',
    reports_dir: Union[str, Path] = Path(__file__).resolve().parent.parent.parent / 'reports',
    create_qa_plots: bool=True
    ) -> None:
    """
    Processes all ECG and event data files for multiple dyads (mother-child pairs) in a specified raw data directory. 
    For each dyad, the function preprocesses the ECG data, performs HRV analysis, and saves the results (both data and plots) 
    to the specified directories. The function also logs the processing status and errors during execution.

    Args:
        raw_data_dir (Union[str, Path], optional): Directory containing the raw ECG and event data files. 
            Defaults to the 'raw' folder in the 'data' directory located at the root level.
        processed_data_dir (Union[str, Path], optional): Directory where the processed data will be saved. 
            Defaults to the 'processed' folder in the 'data' directory located at the root level.
        reports_dir (Union[str, Path], optional): Directory where the QA plots will be saved. 
            Defaults to the 'reports' folder located at the root level.
        create_qa_plots (bool, optional): Whether or not to generate and save Quality Assurance plots. 
            Defaults to True.

    Returns:
        None

    Raises:
        AssertionError: If the raw data directory does not exist or if the number of ECG and event files do not match.

    Workflow:
        - Initializes the required directories (logs, processed data, and QA reports).
        - Sets up logging for tracking the progress of the processing and any errors.
        - Iterates through the raw ECG and event files, ensuring that there are matching pairs.
        - For each pair, preprocesses and segments the ECG data, performs HRV analysis, and saves the results.
        - Logs information about the processing steps and any errors encountered.
        - Optionally generates and saves QA plots for each dyad.
    
    Notes:
        - Uses the base parameters defined in the 'parameters.py' file for processing the ECG data.
        - Parameters can be specified on a dyad by dyad basis for the segmentation by modifying the 'configure_segmentation_params' function in utils/parameters.py.
        - Parameters can be specified on a dyad by dyad basis and separately for mother and child for the ECG preprocessing by modifying the 'configure_ecg_params' function in utils/parameters.py.
    
    """
    # Set up Parameters
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent.parent
    DATA_DIR = ROOT_DIR / 'data'
    LOGGING_DIR = ROOT_DIR / 'logs'
    LOGGING_DIR.mkdir(parents=False, exist_ok=True)
    RAW_DATA_DIR = Path(raw_data_dir)
    PROCESSED_DATA_DIR = Path(processed_data_dir)
    PROCESSED_DATA_DIR.mkdir(parents=False, exist_ok=True)
    QA_REPORTS_DIR = Path(reports_dir) / 'QA'
    QA_REPORTS_DIR.mkdir(parents=True, exist_ok=True) 
    
    # Set up logger
    TIMESTAMP = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")

    LOGGING_FILEPATH = LOGGING_DIR / \
        f"{TIMESTAMP}_logs.log"
    logger = common.Logger(name='ECG_HRV_LOGGER',
                                      log_file=LOGGING_FILEPATH).get_logger()
    
    # Log some parameters
    logger.info(f"RAW_DATA_DIR: {RAW_DATA_DIR}")
    logger.info(f"PROCESSED_DATA_DIR: {PROCESSED_DATA_DIR}")
    logger.info(f"QA_REPORTS_DIR: {QA_REPORTS_DIR}")
    logger.info(f"LOGGING_DIR: {LOGGING_DIR}")
    logger.info(f"create_qa_plots: {create_qa_plots}")
    
    # Some checks
    assert RAW_DATA_DIR.is_dir(), f"Data directory in {DATA_DIR} does not exist."

    # Get ECG filenames
    ecg_filepaths = np.sort(list(RAW_DATA_DIR.glob('*mc.txt')))
    logger.info(ecg_filepaths)

    # Get Event filenames
    event_filepaths = np.sort(list(RAW_DATA_DIR.glob('*event.txt')))
    logger.info(event_filepaths)

    # check whether we have the same number of ECG and Event files
    assert len(ecg_filepaths) == len(event_filepaths)

    ### Calculate
    for index in range(len(ecg_filepaths)):
        try:
            dyad_number, condition, wave = data_utils.extract_subject_id_condition_from_filepath(ecg_filepaths[index])
            logger.info(f"Processing recording {index+1}/{len(ecg_filepaths)}. Dyad number: {dyad_number}. Condition: {condition}. Wave: {wave}")
            
            process_dyad(
                ecg_filepath = ecg_filepaths[index],
                event_filepath = event_filepaths[index],
                parameters=params.base_params,
                data_output_dir=PROCESSED_DATA_DIR,
                figure_output_dir=QA_REPORTS_DIR,
                create_qa_plots=create_qa_plots
            );
        except Exception as e:
            logger.error(f"Error processing {ecg_filepaths[index]}:{e}")
            logger.debug("Traceback:\n" + traceback.format_exc())
            traceback.print_exc()

def process_dyad(ecg_filepath: Union[str, Path],
                 event_filepath: Union[str, Path], 
                 parameters: Dict,
                 data_output_dir: Union[str, Path], 
                 figure_output_dir: Optional[Union[str, Path]],
                 create_qa_plots: bool=True,
                    ) -> None:
    """
    Main function for processing ECG data of a dyad (mother and child). 
    This function performs preprocessing and HRV analysis for both child and mother ECG signals 
    and saves the results to the specified output directories.

    Args:
        ecg_filepath (Union[str, Path]): The path to the file containing ECG data for both child and mother.
        event_filepath (Union[str, Path]): The path to the file containing event data corresponding to the ECG data.
        parameters (Dict): Dictionary of parameters for processing the ECG data, including settings for segmentation,
            signal cleaning, peak detection, and HRV analysis.
        data_output_dir (Union[str, Path]): Directory where the processed data and HRV analysis results will be saved.
        figure_output_dir (Optional[Union[str, Path]]): Directory where Quality Assurance (QA) plots will be saved 
            if `create_qa_plots` is set to True.
        create_qa_plots (bool): Whether to create and save Quality Assurance plots during the processing.

    Returns:
        None

    Raises:
        KeyError: If required keys are missing from the parameter dictionaries.
        FileNotFoundError: If the specified file paths do not exist.

    Workflow:
        - Extracts subject ID, condition, and wave from the provided file paths.
        - Loads and prepares ECG and event data.
        - Applies preprocessing to the raw ECG data
        - Segments the preprocessed ECG signals for both mother and child.
        - Computes various HRV metrics for all analysis windows within a segment.
        - Saves the HRV metrics and processed signal data as Excel and CSV files.
        - Optionally saves QA plots if `create_qa_plots` is enabled.
        - Exports parameter settings to YAML files.

    Notes:
        The function assumes that the subject ID, condition, and wave are consistent across both ECG and event files.
    """
    
    # Some basic checks
    subject_id_ecg, condition_ecg, wave_ecg = data_utils.extract_subject_id_condition_from_filepath(ecg_filepath)
    subject_id_event, condition_event, wave_event = data_utils.extract_subject_id_condition_from_filepath(event_filepath)
    assert subject_id_ecg == subject_id_event, f"Subject IDs do not match. Got {subject_id_ecg} = {subject_id_event}"
    assert condition_ecg == condition_event, f"Conditions do not match. Got {condition_ecg} = {condition_event}"
    assert wave_ecg == wave_event, f"Waves do not match. Got {wave_ecg} = {wave_event}"
    
    # Load and prepare data
    signal_event_df = data_utils.load_dyad_ecg_events(ecg_filepath, event_filepath)
    child_series, mother_series = data_utils.split_in_child_mother_series(signal_event_df)

    # prepare parameters
    segmentation_params = params.configure_segmentation_params(subject_id_ecg, parameters)
    child_params, mother_params = params.configure_ecg_params(subject_id_ecg, segmentation_params.copy())
    
    # Create output directories -> subjects are actually dyads but both go in same folder
    data_output_dir = data_output_dir / f"{condition_ecg}_{subject_id_ecg}_{wave_ecg}"
    data_output_dir.mkdir(parents=True, exist_ok=True)
    qa_reports_dir = figure_output_dir / f"{condition_ecg}_{subject_id_ecg}_{wave_ecg}"
    qa_reports_dir.mkdir(parents=True, exist_ok=True)

    # Preprocess ECG data
    child_signals_df = nk_pipeline.ecg_preprocess(child_series, child_params)
    mother_signals_df = nk_pipeline.ecg_preprocess(mother_series, mother_params)
    
    # Join the preprocessed signals with the events
    child_signal_event_df = child_signals_df.merge(signal_event_df[["event", "event_description"]], left_index=True, right_index=True, how = "left")
    mother_signal_event_df = mother_signals_df.merge(signal_event_df[["event", "event_description"]], left_index=True, right_index=True, how = "left")
    
    # segment the dataframes
    child_segments_df_list = data_utils.segment_df(child_signal_event_df, segmentation_params)
    mother_segments_df_list = data_utils.segment_df(mother_signal_event_df, segmentation_params)
    
    # Compute windowed HRV metrics per segment and subject
    hrv_child_df, ecg_child_df = compute_windowed_hrv_across_segments(
        segments_df_list=child_segments_df_list,
        parameters=child_params,
        figure_output_dir=qa_reports_dir,
        data_output_dir=data_output_dir,
        subject_pair="child",
        create_qa_plots=create_qa_plots
    )
    
    hrv_mother_df, ecg_mother_df = compute_windowed_hrv_across_segments(
        segments_df_list=mother_segments_df_list,
        parameters=mother_params,
        figure_output_dir=qa_reports_dir,
        data_output_dir=data_output_dir,
        subject_pair="mother",
        create_qa_plots=create_qa_plots
    )
    
    # Add extra info and save the HRV metrics
    hrv_child_df = hrv_child_df.assign(subject_type = "child", condition = condition_ecg, wave = wave_ecg, subject_id=subject_id_ecg)
    hrv_child_df.to_excel(data_output_dir / f'{condition_ecg}{subject_id_ecg}_{wave_ecg}_child_hrv.xlsx', index=False)
    
    hrv_mother_df = hrv_mother_df.assign(subject_type = "mother", condition = condition_ecg, wave = wave_ecg,subject_id=subject_id_ecg)
    hrv_mother_df.to_excel(data_output_dir / f'{condition_ecg}{subject_id_ecg}_{wave_ecg}_mother_hrv.xlsx', index=False)

    # Add extra info and save the processed signal data
    ecg_child_df = ecg_child_df.assign(subject_type = "child", condition = condition_ecg, wave = wave_ecg,subject_id=subject_id_ecg)
    ecg_child_df.to_csv(data_output_dir / f'{condition_ecg}{subject_id_ecg}_{wave_ecg}_child_signal.csv', index=False)
    
    ecg_mother_df = ecg_mother_df.assign(subject_type = "mother", condition = condition_ecg, wave = wave_ecg,subject_id=subject_id_ecg)
    ecg_mother_df.to_csv(data_output_dir / f'{condition_ecg}{subject_id_ecg}_{wave_ecg}_mother_signal.csv', index=False)
    
    # Save the parameters
    common.export_to_yaml(child_params, data_output_dir/'child_params.yml')
    common.export_to_yaml(mother_params, data_output_dir/'mother_params.yml')
    
def compute_windowed_hrv_across_segments(
    segments_df_list: List[pd.DataFrame], 
    parameters: Dict, 
    figure_output_dir: Union[str, Path], 
    data_output_dir: Union[str, Path], 
    subject_pair: str,
    create_qa_plots:bool=True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute windowed heart rate variability (HRV) metrics for each segment and return concatenated results.

    This function processes a list of data segments, computes HRV metrics for each analysis window within a segment using 
    the specified parameters, and returns two DataFrames:
    1. Concatenated HRV metrics across all segments.
    2. Concatenated preprocessed segment data across all segments.

    Args:
        segments_df_list (List[pd.DataFrame]): 
            A list of pandas DataFrames, each representing a data segment.
            Each DataFrame must contain an 'event_description' column for naming purposes.
            
        parameters (Dict): 
            A dictionary containing parameters for HRV calculation.
            
        figure_output_dir (Union[str, Path]): 
            Path to the directory where HRV figures will be saved. 
            A subdirectory for the specific `subject_pair` will be created.
            
        data_output_dir (Union[str, Path]): 
            Path to the directory where HRV metrics and preprocessed data will be saved.
            
        subject_pair (str): 
            Identifier for the subject pair being analyzed, used in output filenames.
            
        create_qa_plots (bool):
            Whether or not to generate QA plots and save them.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: 
            - A DataFrame containing concatenated HRV metrics across all segments.
            - A DataFrame containing concatenated preprocessed data across all segments.
    """
    figure_output_dir = Path(figure_output_dir)
    data_output_dir = Path(data_output_dir)
    
    all_hrv_metrics = []
    all_preprocessed_data = []

    for segment_df in segments_df_list:
        segment_name = segment_df["event_description"].iloc[0]
        hrv_segment_metrics_df = nk_pipeline.calculate_windowed_HRV_metrics(
            segment_df, 
            parameters, 
            export_segment_plot=create_qa_plots,
            figure_output_dir=figure_output_dir / subject_pair, 
            segment_name=segment_name
        )
        
        # Add HRV metrics and preprocessed data to lists
        hrv_segment_metrics_df = hrv_segment_metrics_df.assign(segment_name = segment_name)
        all_hrv_metrics.append(hrv_segment_metrics_df)
        segment_df = segment_df.assign(segment_name = segment_name)
        all_preprocessed_data.append(segment_df)

    # Concatenate all HRV metrics and preprocessed data
    concatenated_hrv_metrics = pd.concat(all_hrv_metrics, ignore_index=True)
    concatenated_preprocessed_data = pd.concat(all_preprocessed_data, ignore_index=True)

    return concatenated_hrv_metrics, concatenated_preprocessed_data
        


if __name__ == "__main__":
    process_all_dyads(
        )