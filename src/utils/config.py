"""Configuration loading utilities."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml_config(config_name: str) -> Dict[str, Any]:
    """
    Load YAML configuration file.
    
    Args:
        config_name: Name of config file (e.g., 'settings', 'models', 'agents')
    
    Returns:
        Dictionary with configuration data
    """
    config_dir = Path(__file__).parent.parent.parent / 'config'
    config_path = config_dir / f'{config_name}.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_database_url() -> str:
    """
    Get database URL from environment or config.
    
    Returns:
        PostgreSQL connection URL
    """
    # Try environment variable first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Fall back to config file
    config = load_yaml_config('settings')
    db_config = config.get('database', {})
    
    return (
        f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
    )


def get_ollama_url() -> str:
    """
    Get Ollama base URL from environment or config.
    
    Returns:
        Ollama API base URL
    """
    # Try environment variable first
    ollama_url = os.getenv('OLLAMA_BASE_URL')
    if ollama_url:
        return ollama_url
    
    # Fall back to config file
    config = load_yaml_config('settings')
    return config.get('llm', {}).get('base_url', 'http://localhost:11434')


def load_all_configs() -> Dict[str, Dict[str, Any]]:
    """
    Load all configuration files.
    
    Returns:
        Dictionary with all configs: settings, models, agents, risk_rules
    """
    return {
        'settings': load_yaml_config('settings'),
        'models': load_yaml_config('models'),
        'agents': load_yaml_config('agents'),
        'risk_rules': load_yaml_config('risk_rules')
    }

if __name__ == "__main__":
    # Example usage
    settings = load_yaml_config('settings')
    print("Loaded settings:", settings)