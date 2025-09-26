import os
import json
import yaml
from glob import glob

class ConfigLoader:
    def __init__(self, env):
        self.env = env
        self.config = {}
        self.load_config()


    def load_from_yaml(self):
        config_files = glob(f"**/config/{self.env}/*.yaml", recursive=True)
        for file_path in config_files:
            with open(file_path, 'r') as file:
                data = yaml.safe_load(file)
                self.config.update(data)

    def load_from_env(self):
        for key, value in os.environ.items():
            config_key = key.upper()  # Convert to upper
            self.config[config_key] = value

    def load_config(self):
        self.load_from_yaml()
        self.load_from_env()

    def get(self, key):
        return self.config.get(key)
