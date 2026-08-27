import subprocess

def run_secure_command(command, args):
    return subprocess.run([command] + args, capture_output=True, text=True)