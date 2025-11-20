"""
Rules Loader - Dynamic Rules Loading System
Author: Leo Ji

Load agent rules from markdown files instead of hardcoded SYSTEM_PROMPT.
Inspired by Claude Skills architecture.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any


class RulesLoader:
    """
    Load and manage agent rules from markdown files.
    
    Features:
    - Dynamic loading from files
    - Multiple rule sets support
    - Hot reload capability
    - Version tracking
    """
    
    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize rules loader.
        
        Args:
            rules_dir: Directory containing rules files
        """
        self.rules_dir = Path(rules_dir)
        self.loaded_rules: Dict[str, str] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def load_rules(self, filename: str = "agent_rules.md") -> str:
        """
        Load rules from a markdown file.
        
        Args:
            filename: Name of the rules file
            
        Returns:
            Rules content as string
        """
        filepath = self.rules_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Rules file not found: {filepath}")
        
        # Load content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata (version, author, etc.)
        metadata = self._extract_metadata(content)
        
        # Cache
        self.loaded_rules[filename] = content
        self.metadata[filename] = metadata
        
        print(f"✅ Loaded rules: {filename}")
        if metadata.get('version'):
            print(f"   Version: {metadata['version']}")
        if metadata.get('last_updated'):
            print(f"   Last Updated: {metadata['last_updated']}")
        
        return content
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract metadata from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        lines = content.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            if line.startswith('**Version:**'):
                metadata['version'] = line.split('**Version:**')[1].strip()
            elif line.startswith('**Author:**'):
                metadata['author'] = line.split('**Author:**')[1].strip()
            elif line.startswith('**Last Updated:**'):
                metadata['last_updated'] = line.split('**Last Updated:**')[1].strip()
        
        return metadata
    
    def convert_to_system_prompt(
        self, 
        rules_content: str,
        include_metadata: bool = False
    ) -> str:
        """
        Convert rules markdown to system prompt format.
        
        Args:
            rules_content: Raw rules content
            include_metadata: Whether to include metadata in prompt
            
        Returns:
            Formatted system prompt
        """
        # Build prompt
        prompt_parts = []
        
        if include_metadata:
            prompt_parts.append("# Agent Configuration\n")
            prompt_parts.append("*Loaded from: rules/agent_rules.md*\n")
            prompt_parts.append("*This configuration is externalized and version-controlled*\n\n")
        
        prompt_parts.append(rules_content)
        
        return '\n'.join(prompt_parts)
    
    def get_skill(self, skill_name: str, rules_content: Optional[str] = None) -> Optional[str]:
        """
        Extract a specific skill from rules.
        
        Args:
            skill_name: Name of the skill (e.g., "Options Search")
            rules_content: Rules content (if None, uses last loaded)
            
        Returns:
            Skill content or None if not found
        """
        if rules_content is None:
            if not self.loaded_rules:
                raise ValueError("No rules loaded. Call load_rules() first.")
            rules_content = list(self.loaded_rules.values())[0]
        
        # Find skill section
        marker = f"## 📚 Skill: {skill_name}"
        if marker not in rules_content:
            marker = f"## Skill: {skill_name}"  # Fallback without emoji
        
        if marker not in rules_content:
            return None
        
        # Extract skill content
        start_idx = rules_content.index(marker)
        remaining = rules_content[start_idx:]
        
        # Find next skill section
        next_skill = remaining.find('\n## ', 1)
        if next_skill != -1:
            skill_content = remaining[:next_skill]
        else:
            skill_content = remaining
        
        return skill_content.strip()
    
    def list_skills(self, rules_content: Optional[str] = None) -> list[str]:
        """
        List all available skills in rules.
        
        Args:
            rules_content: Rules content (if None, uses last loaded)
            
        Returns:
            List of skill names
        """
        if rules_content is None:
            if not self.loaded_rules:
                raise ValueError("No rules loaded. Call load_rules() first.")
            rules_content = list(self.loaded_rules.values())[0]
        
        import re
        
        # Find all skill headers
        pattern = r'## (?:📚 )?Skill: ([^\n]+)'
        matches = re.findall(pattern, rules_content)
        
        return matches
    
    def reload(self, filename: str = "agent_rules.md") -> str:
        """
        Reload rules from file (hot reload).
        
        Args:
            filename: Name of the rules file
            
        Returns:
            Reloaded rules content
        """
        print(f"🔄 Reloading rules: {filename}")
        return self.load_rules(filename)


# Convenience function for quick loading
def load_agent_rules(
    rules_file: str = "agent_rules.md",
    as_system_prompt: bool = True
) -> str:
    """
    Quick function to load agent rules.
    
    Args:
        rules_file: Rules file name
        as_system_prompt: Whether to format as system prompt
        
    Returns:
        Rules content (formatted if as_system_prompt=True)
    """
    loader = RulesLoader()
    content = loader.load_rules(rules_file)
    
    if as_system_prompt:
        return loader.convert_to_system_prompt(content)
    else:
        return content


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("Rules Loader Demo")
    print("=" * 70)
    print()
    
    # Load rules
    loader = RulesLoader()
    rules = loader.load_rules("agent_rules.md")
    
    print()
    print("=" * 70)
    print("Available Skills:")
    print("=" * 70)
    
    # List skills
    skills = loader.list_skills()
    for i, skill in enumerate(skills, 1):
        print(f"{i}. {skill}")
    
    print()
    print("=" * 70)
    print("Sample Skill Content:")
    print("=" * 70)
    
    # Get a specific skill
    if skills:
        sample_skill = loader.get_skill(skills[0])
        print(sample_skill[:500] + "...")
    
    print()
    print("=" * 70)
    print("System Prompt Preview:")
    print("=" * 70)
    
    # Convert to system prompt
    system_prompt = loader.convert_to_system_prompt(rules, include_metadata=True)
    print(system_prompt[:500] + "...")
    print(f"\nTotal length: {len(system_prompt)} characters")

