"""
Configuration settings for the LLama model and system behavior.
"""

# Ollama API Configuration
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "timeout": 120,  # Increased for complex operations
    "retry_attempts": 3,
    "retry_delay": 2
}

# Model Configuration
MODEL_CONFIG = {
    "model": "mannix/llama3.1-8b-abliterated:tools-q4_0",  # Base model
    "temperature": 0.7,  # Higher for more creative responses
    "top_p": 0.95,      # Higher for more diverse outputs
    "top_k": 50,        # More options in token selection
    "num_ctx": 4096,    # Maximum context length
    "num_predict": -1,  # No limit on generation length
    "repeat_penalty": 1.1,  # Slightly penalize repetition
    "repeat_last_n": 64,    # Look back window for repetition
    "seed": -1,  # Random seed for reproducibility
}

# System Behavior
SYSTEM_CONFIG = {
    "stream_output": True,     # Stream responses
    "show_thinking": True,     # Show processing status
    "debug_mode": False,       # Debug information
    "log_commands": True,      # Log executed commands
    "max_retries": 3,         # Maximum retry attempts
    "timeout_multiplier": 1.5  # Timeout increase per retry
}

# Response Configuration
RESPONSE_CONFIG = {
    "max_length": 2000,        # Maximum response length
    "min_length": 50,         # Minimum response length
    "length_penalty": 1.0,    # Length penalty factor
    "early_stopping": False,  # Don't stop early
    "no_repeat_ngram_size": 3  # Avoid repeating 3-grams
}

# Advanced Settings
ADVANCED_CONFIG = {
    "mirostat": 2,            # Adaptive sampling
    "mirostat_tau": 5.0,      # Target entropy
    "mirostat_eta": 0.1,      # Learning rate
    "typical_p": 0.95,        # Typical sampling probability
    "tfs_z": 1.0,            # Tail-free sampling
    "grammar_file": None      # Custom grammar file
}

def get_model_settings():
    """Get complete model settings"""
    return {
        "model": MODEL_CONFIG["model"],
        "temperature": MODEL_CONFIG["temperature"],
        "top_p": MODEL_CONFIG["top_p"],
        "top_k": MODEL_CONFIG["top_k"],
        "num_ctx": MODEL_CONFIG["num_ctx"],
        "num_predict": MODEL_CONFIG["num_predict"],
        "repeat_penalty": MODEL_CONFIG["repeat_penalty"],
        "repeat_last_n": MODEL_CONFIG["repeat_last_n"],
        "seed": MODEL_CONFIG["seed"],
        "mirostat": ADVANCED_CONFIG["mirostat"],
        "mirostat_tau": ADVANCED_CONFIG["mirostat_tau"],
        "mirostat_eta": ADVANCED_CONFIG["mirostat_eta"],
        "typical_p": ADVANCED_CONFIG["typical_p"],
        "tfs_z": ADVANCED_CONFIG["tfs_z"]
    }

def get_api_settings():
    """Get API connection settings"""
    return {
        "base_url": OLLAMA_CONFIG["base_url"],
        "timeout": OLLAMA_CONFIG["timeout"],
        "retry": {
            "attempts": OLLAMA_CONFIG["retry_attempts"],
            "delay": OLLAMA_CONFIG["retry_delay"],
            "multiplier": SYSTEM_CONFIG["timeout_multiplier"]
        }
    }

def get_response_settings():
    """Get response generation settings"""
    return {
        "max_length": RESPONSE_CONFIG["max_length"],
        "min_length": RESPONSE_CONFIG["min_length"],
        "length_penalty": RESPONSE_CONFIG["length_penalty"],
        "early_stopping": RESPONSE_CONFIG["early_stopping"],
        "no_repeat_ngram_size": RESPONSE_CONFIG["no_repeat_ngram_size"]
    } 