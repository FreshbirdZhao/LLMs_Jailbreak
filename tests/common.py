import tempfile
from pathlib import Path


def make_temp_project_root():
    temp_ctx = tempfile.TemporaryDirectory()
    return temp_ctx, Path(temp_ctx.name)
