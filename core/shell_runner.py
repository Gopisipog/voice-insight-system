import subprocess
import os

class ShellRunner:
    def __init__(self, working_dir=None):
        self.working_dir = working_dir or os.getcwd()

    def run_command(self, command, input_text):
        """
        Runs a command. Data is passed as a pure string (no prefix).
        Uses Environment Injection for safety.
        """
        print(f"Executing: {command}")
        
        # 1. Prepare Environment (The safest way to pass clean text)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["INPUT_DATA"] = input_text 

        # 3. Handle Placeholder Replacement
        # We replace $input in your command with a shell-safe reference to the variable
        if "$input" in command:
            # If it's PowerShell (detected by keywords), use $env:INPUT_DATA
            if "powershell" in command.lower() or "|" in command:
                prepared_command = command.replace("$input", "$env:INPUT_DATA")
            else:
                # Fallback for CMD
                prepared_command = command.replace("$input", "%INPUT_DATA%")
        else:
            # Auto-append mode
            if "powershell" in command.lower():
                prepared_command = f"{command} $env:INPUT_DATA"
            else:
                prepared_command = f"{command} %INPUT_DATA%"

        try:
            # Use shell=True to support the environment variable expansion
            process = subprocess.Popen(
                prepared_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                cwd=self.working_dir,
                encoding='utf-8',
                env=env
            )
            
            # Still pipe to stdin for dual-compatibility
            stdout, stderr = process.communicate(input=input_text)
            
            if process.returncode != 0:
                return f"Error ({process.returncode}): {stderr}"
            
            return stdout
        except Exception as e:
            return f"Exception while running command: {str(e)}"

    def run_powershell(self, script_path, input_text):
        command = f"powershell -ExecutionPolicy Bypass -File {script_path}"
        return self.run_command(command, input_text)
