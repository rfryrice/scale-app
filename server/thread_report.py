import os
import sys
import subprocess
import threading

def report_gpiochip0_users():
    """
    Prints a list of processes and threads currently using /dev/gpiochip0.
    """
    gpiochip_path = "/dev/gpiochip0"
    print(f"[*] Checking for processes using {gpiochip_path} ...\n")

    # Use lsof to list open files for gpiochip0
    try:
        output = subprocess.check_output(['lsof', gpiochip_path], text=True)
    except subprocess.CalledProcessError as e:
        print(f"No processes are currently using {gpiochip_path}.")
        return

    print("Processes using /dev/gpiochip0:")
    print(output)

    # Optional: show threads in this process that might be related to GPIO use
    print("[*] Python threads in this process:")
    for thread in threading.enumerate():
        print(f"  Thread name: {thread.name} (ident={thread.ident})")

if __name__ == "__main__":
    report_gpiochip0_users()