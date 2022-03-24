import shlex
import subprocess


def test_independent_controls():
    cmd = "python examples/independent_control_demo.py"
    subprocess.check_call(shlex.split(cmd))
