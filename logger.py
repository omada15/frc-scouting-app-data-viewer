import os
import inspect

def log(message):
    filename = os.path.splitext(os.path.basename(inspect.stack()[1].filename))[0]
    with open(f"{filename}.log", "a") as log_file:
        log_file.write(str(message) + "\n")

def clear():
    filename = os.path.splitext(os.path.basename(inspect.stack()[1].filename))[0]
    open(f"{filename}.log", "w").close()
