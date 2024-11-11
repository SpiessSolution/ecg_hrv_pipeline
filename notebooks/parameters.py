"""
Default Parameters and functions related to changing parameters 
"""


from typing import Dict, List
from copy import deepcopy

# Default parameters
# Visit Neurokit website for parameters: https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/signal/signal_filter.html#signal_filter
# 

base_params = {
    'general': {
        'sampling_frequency': 500,
        'analysis_window_seconds': 30, # 
        'compute_hrv_frequency_metrics': False
    },
    'cleaning': {
        'method': 'neurokit',
        'powerline': 50  # or 60 or None
    },
    'peak_detection': {
        'method': 'neurokit',
        'correct_artifacts': True
    },
    'signal_quality_index': {
        'method': 'averageQRS',
        'approach': 'simple'
    },
    'hrv_frequency_settings': {
        'ulf': [0, 0.0033], # The spectral power of ultra low frequencies
        'vlf': [0.0033, 0.04], # The spectral power of very low frequencies
        'lf': [0.04, 0.15], # The spectral power of low frequencies
        'hf': [0.15, 0.4],
        'vhf': [0.4, 0.5], # The spectral power of very high frequencie
        'psd_method': 'welch',
        'normalize': True
    },
    'segmentation': {
        'baseline': { # name of the segment
            'event_onset':'baseline resting start', # put here either event description (e.g., baseline resting start)
            'duration': 300, # put here the duration (in seconds)
            },
        'stroop_mother_start': {
            'event_onset': "Book start",
            'duration': 300,
        }
    }
}

########################################################################################


# Only configure here the parameters to be updated for a given subject if they
# differ from the default parameters specfied above.
def configure_ecg_params(subject_id: int, pipeline_params: Dict) -> List[Dict]:
    """
    Configures child and mother parameters based on the subject ID.
    

    Args:
        subject_id (str): The ID of the subject being processed.
        pipeline_params (Dict): The base dictionary containing default pipeline parameters.

    Returns:
        Tuple[Dict, Dict]: A tuple containing customized dictionaries for child_params and mother_params.
    """
    child_params = deepcopy(pipeline_params)
    mother_params = deepcopy(pipeline_params)
    
    # Customize parameters based on subject_id
    # if subject_id == 8:
    #     child_params['cleaning'].update({"powerline": 40})

    # elif subject_id == "4":
    #     mother_params['general'].update({"key2": "value2"})
    
    # Add more conditions for other subject IDs as needed

    return child_params, mother_params



def configure_segmentation_params(subject_id: int, pipeline_params: Dict) -> Dict:
    """
   ation parameters, you have to do this separately for mother and child paramneters.

    Args:
        subject_id (str): The ID of the subject being processed.
        pipeline_params (Dict): The base dictionary containing default pipeline parameters.

    Returns:
        Tuple[Dict, Dict]: A tuple containing customized dictionaries for child_params and mother_params.
    """
    parameters = deepcopy(pipeline_params)
    
    # Customize parameters based on subject_id
    # if subject_id == 8:
    #     parameters['segmentation']['baseline'].update({"event_onset": 0.02})
    
    # elif subject_id == "4":
    #     mother_params['general'].update({"key2": "value2"})
    
    # Add more conditions for other subject IDs as needed

    return parameters
