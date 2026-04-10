import re
import os
import sys

# Deterministic Preflight for GenLayer Contracts
# Focus: Missing Guards, Unsafe Inputs, State Integrity

def check_file(filepath):
    results = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
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

def main():
    target_dir = "./contracts"
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]

    print(f"Scanning contracts in: {target_dir}")
    found_any = False
    for filename in os.listdir(target_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            found_any = True
            path = os.path.join(target_dir, filename)
            findings = check_file(path)
            if findings:
                print(f"--- {filename} ---")
                for f in findings:
                    print(f)
    if not found_any:
        print("No Python contracts found in target directory.")

if __name__ == "__main__":
    main()
