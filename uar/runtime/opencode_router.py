import json
from pathlib import Path
import subprocess

CONFIG_PATH = Path(".opencode/agents.json")

def load_config():
    return json.loads(CONFIG_PATH.read_text())

def load_role_prompt(role):
    config = load_config()
    path = Path(config[role]["file"])
    return path.read_text()

def run_agent(role, task):
    config = load_config()

    role_config = config[role]
    system_prompt = load_role_prompt(role)

    model = role_config["model"]

    prompt = f"""
{system_prompt}

---

TASK:
{task}
"""

    print(f"\n[UAR] Running {role} with {model}")

    subprocess.run([
        "ollama", "run", model, prompt
    ])

if __name__ == "__main__":
    import sys
    role = sys.argv[1]
    task = " ".join(sys.argv[2:])
    run_agent(role, task)
