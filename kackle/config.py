import yaml
from openai import OpenAI

def load_configs():
    with open('config.yaml') as f:
        base_config = yaml.safe_load(f)
    
    
    return base_config

config = load_configs()

client = OpenAI(
    api_key=config['openai']['api_key'],
    organization=config['openai']['orginization_id']
)