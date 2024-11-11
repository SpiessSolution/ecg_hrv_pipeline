"""

"""

#fmt:off
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent)) # the dir containing utils
import utils.common as common

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



if __name__ == "__main__":
    main()