import re
import os
import sys

# Deterministic Preflight for GenLayer Contracts
# Focus: Missing Guards, Unsafe Inputs, State Integrity

def check_source(content):
    results = []
    lines = content.splitlines()

    # 1. Check for missing Access Control in @gl.public.write
    matches = re.finditer(r'@gl\.public\.write\s+def\s+(\w+)\(self,', content)
    for match in matches:
        func_name = match.group(1)
        # Find the line number
        line_num = content.count('\n', 0, match.start()) + 1
        # Check the next few lines for 'assert' or 'gl.message.sender_address'
        is_guarded = False
        for i in range(line_num, min(line_num + 5, len(lines))):
            if 'assert' in lines[i] or 'gl.message.sender_address' in lines[i] or 'if' in lines[i]:
                is_guarded = True
                break
        if not is_guarded:
            results.append(f"L{line_num}: [ACCESS] Potential unguarded public write method: {func_name}")

    # 2. Check for unsafe Python functions (eval, exec)
    for i, line in enumerate(lines):
        if re.search(r'\beval\(|\bexec\(', line):
            results.append(f"L{i+1}: [PYTHON] Unsafe arbitrary code execution attempt (eval/exec)")

    # 3. Check for SSRF in web render URLs
    for i, line in enumerate(lines):
        if 'gl.nondet.web.render' in line and '+' in line:
            results.append(f"L{i+1}: [ORACLE] Dynamic URL concatenation found in web render. Check for SSRF.")

    # 4. Check for state persistence integrity
    if '@allow_storage' in content and 'TreeMap' not in content:
         results.append(f"L1: [STORAGE] @allow_storage used but no TreeMap found. Verify state persistence.")

    return results

def check_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return check_source(f.read())

def main():
    target_dir = "./contracts"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]

    print(f"Scanning contracts in: {target_dir}")
    if not os.path.isdir(target_dir):
        print(f"Target directory not found: {target_dir}")
        print("Pass a contracts directory explicitly, for example: python scripts/preflight.py ./path/to/contracts")
        return 1

    found_any = False
    for root, _, filenames in os.walk(target_dir):
        for filename in sorted(filenames):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            found_any = True
            path = os.path.join(root, filename)
            findings = check_file(path)
            if findings:
                print(f"--- {os.path.relpath(path, target_dir)} ---")
                for f in findings:
                    print(f)
    if not found_any:
        print("No Python contracts found in target directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
