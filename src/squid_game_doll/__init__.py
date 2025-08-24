import os
import warnings

# Suppress NumPy subnormal value warnings that occur on some systems during initialization
warnings.filterwarnings("ignore", message="The value of the smallest subnormal.*is zero", category=UserWarning)

os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

DEBUG_LASER_FIND = True
