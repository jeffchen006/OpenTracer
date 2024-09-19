import tomlkit


settings = None
with open("settings.toml", "r") as f:
    toml_content = f.read()
    settings = tomlkit.parse(toml_content)

import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
import time

def changeSettings(category: str, key: str, value):
    settings[category][key] = value
    with open("settings.toml", "w") as f:
        f.write(tomlkit.dumps(settings))

def changeLoggingUpperBound(value):
    changeSettings("runtime", "LoggingUpperBound", value)
    time.sleep(1)

if __name__ == "__main__":
    # changeSettings("runtime", "LoggingUpperBound", 5)
    changeLoggingUpperBound(6)
