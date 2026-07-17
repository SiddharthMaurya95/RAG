from core.decorators import with_logging_and_exceptions
import os
import glob
import sys

@with_logging_and_exceptions
def init_cuda_dlls():
    if os.name == 'nt':
        paths = sys.path
        for sp in paths:
            nvidia_path = os.path.join(sp, 'nvidia')
            if os.path.exists(nvidia_path):
                for p in glob.glob(os.path.join(nvidia_path, '*', 'bin')):
                    if os.path.exists(p):
                        # Add to DLL directory for Python 3.8+
                        if sys.version_info >= (3, 8):
                            try:
                                os.add_dll_directory(p)
                            except:
                                pass
                        # Also add to PATH to ensure libraries loaded by other libraries find them
                        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

init_cuda_dlls()
