#!/usr/bin/env python3
import sys
print(f"Running from: {sys.argv[0]}")
print(f"Python path: {sys.executable}")

# Check if file has the button
with open('main.py', 'r') as f:
    content = f.read()
    if '⚡ Add DNS' in content:
        print("✓ File HAS the 'Add DNS' button code")
    else:
        print("✗ File MISSING the 'Add DNS' button code")
    
    if 'self.add_dns_btn' in content:
        count = content.count('self.add_dns_btn')
        print(f"✓ Found {count} references to 'self.add_dns_btn'")
