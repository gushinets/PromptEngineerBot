"""
Prompt loading and management.
"""
import os
from typing import Dict

class PromptLoader:
    """Loads and manages system prompts for different optimization methods."""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        self.prompts_dir = prompts_dir
        self._prompts: Dict[str, str] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Load all prompt files."""
        prompt_files = {
            'craft': 'CRAFT_prompt.txt',
            'lyra': 'LYRA_prompt.txt',
            'ggl': 'GGL_prompt.txt'
        }
        
        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._prompts[key] = f.read().strip()
            except FileNotFoundError:
                raise FileNotFoundError(f"Prompt file not found: {filepath}")
            except Exception as e:
                raise Exception(f"Error loading prompt file {filepath}: {e}")
    
    @property
    def craft_prompt(self) -> str:
        """Get the CRAFT optimization prompt."""
        return self._prompts['craft']
    
    @property
    def lyra_prompt(self) -> str:
        """Get the LYRA optimization prompt."""
        return self._prompts['lyra']
    
    @property
    def ggl_prompt(self) -> str:
        """Get the GGL optimization prompt."""
        return self._prompts['ggl']
    
    def get_prompt(self, method: str) -> str:
        """
        Get a prompt by method name.
        
        Args:
            method: Method name ('craft', 'lyra', 'ggl')
            
        Returns:
            The prompt text
            
        Raises:
            KeyError: If method is not found
        """
        if method.lower() not in self._prompts:
            raise KeyError(f"Unknown prompt method: {method}")
        return self._prompts[method.lower()]