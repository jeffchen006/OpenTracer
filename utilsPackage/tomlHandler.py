import toml
settings = toml.load("settings.toml")
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import time

def changeSettings(category: str, key: str, value):
    settings[category][key] = value
    with open("settings.toml", "w") as f:
        toml.dump(settings, f)

def changeLoggingUpperBound(value):
    changeSettings("runtime", "LoggingUpperBound", value)
    time.sleep(1)

if __name__ == "__main__":
    # changeSettings("runtime", "LoggingUpperBound", 5)
    changeLoggingUpperBound(6)
