#!/usr/bin/env python3
"""
Sensitive Columns Checker
Detects potentially unencrypted PII columns (email, phone, SSN patterns).
"""

import re
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class SensitiveColumn:
    """Represents a potentially sensitive column."""
    table: str
    column: str
    reason: str
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'


def get_sensitive_patterns() -> Dict[str, tuple]:
    """
    Returns patterns for detecting sensitive columns.
    Format: {pattern: (reason, severity)}
    """
    return {
        # High sensitivity - direct PII
        r'ssn|social_security': ('Social Security Number', 'HIGH'),
        r'tax_id|tin': ('Tax ID', 'HIGH'),
        r'credit_card|card_number|cvv': ('Credit Card Info', 'HIGH'),
        r'bank_account|routing_number': ('Banking Info', 'HIGH'),
        r'passport|license_number': ('ID Document', 'HIGH'),
        
        # Medium sensitivity - contact info
        r'^phone|phone_number|mobile': ('Phone Number', 'MEDIUM'),
        r'^email(?!.*token)': ('Email Address', 'MEDIUM'),
        r'address|street|postal|zip_code': ('Physical Address', 'MEDIUM'),
        
        # Low sensitivity - demographic
        r'date_of_birth|dob|birth_date': ('Date of Birth', 'LOW'),
        r'age': ('Age', 'LOW'),
        r'gender|sex': ('Gender', 'LOW'),
    }


def is_likely_encrypted(column_name: str, column_type: str) -> bool:
    """
    Check if a column is likely encrypted based on naming and type.
    """
    encrypted_indicators = [
        'encrypted',
        'hashed',
        'hash',
        '_enc',
        'cipher',
    ]
    
    # Check column name
    lower_name = column_name.lower()
    if any(indicator in lower_name for indicator in encrypted_indicators):
        return True
    
    # Check if it's a binary/blob type (common for encrypted data)
    if column_type and any(t in column_type.lower() for t in ['binary', 'blob', 'bytea']):
        return True
    
    return False


def analyze_orm_models() -> List[SensitiveColumn]:
    """
    Analyze ORM models to identify sensitive columns.
    """
    from src.adapters.persistence.models import Base
    
    sensitive_columns: List[SensitiveColumn] = []
    patterns = get_sensitive_patterns()
    
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            col_name = column.name.lower()
            col_type = str(column.type)
            
            # Skip if likely encrypted
            if is_likely_encrypted(col_name, col_type):
                continue
            
            # Skip password fields (assumed to be hashed)
            if 'password' in col_name:
                continue
            
            # Check against sensitive patterns
            for pattern, (reason, severity) in patterns.items():
                if re.search(pattern, col_name, re.IGNORECASE):
                    sensitive_columns.append(SensitiveColumn(
                        table=table_name,
                        column=column.name,
                        reason=reason,
                        severity=severity
                    ))
                    break  # Only match first pattern
    
    return sensitive_columns


def get_known_exceptions() -> Set[str]:
    """
    Returns set of table.column combinations that are known exceptions.
    These are sensitive columns that are intentionally unencrypted.
    """
    return {
        # Example: 'users.email' - Email needs to be searchable
        'users.email',  # Required for login, normalized for uniqueness
        # Add more exceptions as needed
    }


async def main():
    """Main function to check for sensitive columns."""
    print("=" * 60)
    print("Sensitive Columns Check")
    print("=" * 60)
    print()
    
    try:
        print("Scanning ORM models for sensitive columns...")
        sensitive_columns = analyze_orm_models()
        
        # Filter out known exceptions
        exceptions = get_known_exceptions()
        filtered_columns = [
            col for col in sensitive_columns
            if f"{col.table}.{col.column}" not in exceptions
        ]
        
        if not filtered_columns:
            print("✓ No unencrypted sensitive columns found")
            print("  All PII appears to be properly protected")
            return 0
        
        # Group by severity
        by_severity: Dict[str, List[SensitiveColumn]] = {
            'HIGH': [],
            'MEDIUM': [],
            'LOW': []
        }
        
        for col in filtered_columns:
            by_severity[col.severity].append(col)
        
        print(f"⚠️  WARNING: Found {len(filtered_columns)} potentially unencrypted sensitive column(s):")
        print()
        
        for severity in ['HIGH', 'MEDIUM', 'LOW']:
            if by_severity[severity]:
                print(f"  {severity} Severity ({len(by_severity[severity])} columns):")
                for col in sorted(by_severity[severity], key=lambda x: (x.table, x.column)):
                    print(f"    - {col.table}.{col.column} ({col.reason})")
                print()
        
        print("Recommendations:")
        print("  1. Review each column to determine if it contains sensitive data")
        print("  2. For HIGH severity: Implement encryption at rest immediately")
        print("  3. For MEDIUM severity: Consider encryption or tokenization")
        print("  4. For LOW severity: Review data retention and access policies")
        print("  5. Add justified exceptions to get_known_exceptions() if intentional")
        print()
        
        print("Exception Management:")
        print("  If a column is intentionally unencrypted (e.g., for search/indexing),")
        print("  add it to get_known_exceptions() in this script with a comment explaining why.")
        
        return 1
    
    except Exception as e:
        print(f"✗ Error during sensitive columns check: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    exit(exit_code)
