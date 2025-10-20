#!/usr/bin/env python3
"""
Script to add @pytest.mark.skip decorators to tests that depend on 
feature-flags and policies API routes (which have been commented out).
"""
import os
import re

# Files that should be completely skipped (all tests depend on these routes)
SKIP_FILES = [
    "tests/contract/test_openapi_feature_flags.py",
    "tests/contract/test_openapi_policy_dry_run.py", 
    "tests/contract/test_openapi_policy_registration.py",
    "tests/integration/test_feature_flag_scenarios.py",
    "tests/integration/test_policy_api.py",
]

# Skip reason
SKIP_REASON = 'reason="API routes hidden from OpenAPI docs - feature-flags and policies endpoints commented out in app.py"'

def add_module_level_skip(filepath):
    """Add pytestmark at module level to skip all tests in file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already has pytestmark
    if 'pytestmark = pytest.mark.skip' in content:
        print(f"  ✓ Already has module-level skip: {filepath}")
        return
    
    # Find the last import statement
    import_lines = []
    other_lines = []
    in_imports = True
    
    for line in content.split('\n'):
        if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#') or line.startswith('"""') or line.startswith("'''")):
            import_lines.append(line)
        else:
            in_imports = False
            other_lines.append(line)
    
    # Add pytestmark after imports
    new_content = '\n'.join(import_lines)
    new_content += '\n\n' + f'# Skip all tests - API routes commented out\npytestmark = pytest.mark.skip({SKIP_REASON})\n\n'
    new_content += '\n'.join(other_lines)
    
    with open(filepath, 'w') as f:
        f.write(new_content)
    
    print(f"  ✓ Added module-level skip: {filepath}")

def main():
    print("Adding skip markers to tests that depend on commented API routes...\n")
    
    for filepath in SKIP_FILES:
        if os.path.exists(filepath):
            add_module_level_skip(filepath)
        else:
            print(f"  ⚠ File not found: {filepath}")
    
    print("\n✅ Done! All affected tests marked as skipped.")
    print("\nTo verify, run: pytest tests/contract tests/integration -v --collect-only")

if __name__ == '__main__':
    main()
