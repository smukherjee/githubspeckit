#!/usr/bin/env python
"""Debug OpenAPI schema generation."""
import traceback
from adapters.api.app import create_app

app = create_app()
print("App created successfully")

try:
    schema = app.openapi()
    print("OpenAPI schema generated successfully!")
    print("Paths:", list(schema.get("paths", {}).keys())[:10])
except Exception as e:
    print("\n=== ERROR GENERATING OPENAPI SCHEMA ===\n")
    traceback.print_exc()
    print("\n\nError details:", str(e))
