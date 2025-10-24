#!/usr/bin/env python3
"""
Generate .env.example from config/descriptor.toml

Usage:
    python scripts/generate_env_example.py
"""
import tomli
from pathlib import Path


def generate_env_example():
    """Generate .env.example from descriptor.toml"""
    
    # Load descriptor
    descriptor_path = Path('config/descriptor.toml')
    with open(descriptor_path, 'rb') as f:
        config = tomli.load(f)
    
    # Header
    output_lines = [
        '# Auto-generated from config/descriptor.toml (FR-039)',
        '# Copy to .env and fill in your values',
        '#',
        '# REFERENCE CONFIGURATIONS:',
        '#   - env.dev: Development-focused defaults (SQLite, debug logging, relaxed settings)',
        '#   - env.prod: Production-focused defaults (PostgreSQL, secure settings, metrics enabled)',
        '#   - env.test.postgres: PostgreSQL testing configuration (used by test suite)',
        '#',
        '# Usage:',
        '#   cp .env.example .env              # Start with this template',
        '#   # OR',
        '#   cp env.dev .env                   # Use dev defaults',
        '#   # OR',
        '#   cp env.prod .env                  # Use production defaults (then customize secrets)',
        '#',
        '# These reference files are NOT automatically loaded - they serve as templates.',
        '# The application loads .env (if present) or uses descriptor.toml defaults.',
        '',
    ]
    
    # Process each section
    for section, variables in config.items():
        output_lines.append(f'# {"="*76}')
        output_lines.append(f'# {section.upper()}')
        output_lines.append(f'# {"="*76}')
        output_lines.append('')
        
        for var_name, props in variables.items():
            # Add description as comment
            desc = props.get('description', '')
            if desc:
                output_lines.append(f'# {desc}')
            
            # Add metadata
            meta_parts = []
            meta_parts.append(f"Type: {props.get('type', 'string')}")
            meta_parts.append(f"Required: {props.get('required', False)}")
            meta_parts.append(f"Secret: {props.get('secret', False)}")
            output_lines.append(f'# {" | ".join(meta_parts)}')
            
            # Add variable assignment
            if props.get('required') and not props.get('secret'):
                # Required non-secret: use default if available
                default = props.get('default')
                if default is not None:
                    output_lines.append(f'{var_name}={default}')
                else:
                    output_lines.append(f'{var_name}=<REQUIRED_VALUE>')
            elif props.get('required') and props.get('secret'):
                # Required secret: placeholder
                output_lines.append(f'{var_name}=<SECRET_VALUE>')
            else:
                # Optional: comment out with default if available
                default = props.get('default')
                if default is not None and default != '':
                    if isinstance(default, bool):
                        output_lines.append(f'# {var_name}={str(default)}')
                    else:
                        output_lines.append(f'# {var_name}={default}')
                else:
                    output_lines.append(f'# {var_name}=<{props.get("type", "string").upper()}>')
            
            output_lines.append('')
    
    # Write output
    env_example_path = Path('.env.example')
    env_example_path.write_text('\n'.join(output_lines))
    print(f'✓ Generated {env_example_path} with {len(config)} sections, {sum(len(v) for v in config.values())} variables')
    
    # Verify rate_limiting section is not present
    if 'rate_limiting' in config:
        print('✗ ERROR: rate_limiting section still present in descriptor.toml')
        return False
    else:
        print('✓ Confirmed: rate_limiting section removed from descriptor.toml')
    
    return True


if __name__ == '__main__':
    success = generate_env_example()
    exit(0 if success else 1)
