#fmt:off
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent)) # the dir containing utils
import utils.parameters as params
import utils.nk_pipeline as nk_pipeline
import utils.data_utils as data_utils
import numpy as np
import matplotlib.pyplot as plt
plt.ioff()  # Turn off interactive mode

#fmt:on

def main():
    # Set up Parameters
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent.parent
    DATA_DIR = ROOT_DIR / 'data'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    PROCESSED_DATA_DIR.mkdir(parents=False, exist_ok=True)
    REPORTS_DIR = ROOT_DIR / 'reports'
    REPORTS_DIR.mkdir(parents=False, exist_ok=True) 
    QA_REPORTS_DIR = REPORTS_DIR / 'QA'
    QA_REPORTS_DIR.mkdir(parents=False, exist_ok=True) 
    
    # Some checks
    assert RAW_DATA_DIR.is_dir(), f"Data directory in {DATA_DIR} does not exist."

    # Get ECG filenames
    ecg_filepaths = np.sort(list(RAW_DATA_DIR.glob('*mc.txt')))

    # Get Event filenames
    event_filepaths = np.sort(list(RAW_DATA_DIR.glob('*event.txt')))

    # check whether we have the same number of ECG and Event files
    assert len(ecg_filepaths) == len(event_filepaths)

    ### Calculate
    for index in range(len(ecg_filepaths)):
        try:
            dyad_number, condition, wave = data_utils.extract_subject_id_condition_from_filepath(ecg_filepaths[index])
            print(f"Processing recording {index+1}/{len(ecg_filepaths)}. Dyad number: {dyad_number}. Condition: {condition}. Wave: {wave}")
            nk_pipeline.process_dyad(
                ecg_filepath = ecg_filepaths[index],
                event_filepath = event_filepaths[index],
                parameters=params.base_params,
                data_output_dir=PROCESSED_DATA_DIR,
                figure_output_dir=QA_REPORTS_DIR,
                create_qa_plots=False
            );
        except Exception as e:
            print(f"Error processing {ecg_filepaths[index]}: {e}")



if __name__ == "__main__":
    main()