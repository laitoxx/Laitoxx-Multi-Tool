import hashlib
import csv
import os
import secrets

def hash_function(text, algorithm, salt=None):
    """Hashes the text using the specified algorithm, optionally with salt."""
    h = hashlib.new(algorithm)
    if salt:
        h.update((text + salt).encode('utf-8'))
    else:
        h.update(text.encode('utf-8'))
    return h.hexdigest()

def reduce_function(hashed_text, charset, max_len, step=0):
    """Reduces a hash to a new plaintext using a family of reduction functions."""
    # Use the hash and step to create different reduction functions
    # This creates a family of reduction functions to avoid collisions
    hash_bytes = bytes.fromhex(hashed_text)
    combined = hash_bytes + step.to_bytes(4, 'big')

    # Use SHA256 to mix the hash and step for better distribution
    mixer = hashlib.sha256(combined).digest()

    new_plaintext = ""
    for i in range(max_len):
        # Use different parts of the mixer for each position
        index = mixer[i % len(mixer)] % len(charset)
        new_plaintext += charset[index]

    return new_plaintext

def generate_rainbow_table(charset, algorithm, chain_length, num_chains, password_len, output_file, use_salt=False, salt_length=8):
    """Generates and stores a rainbow table with optional salt support."""
    table = []
    salt_used = None

    if use_salt:
        # Generate a random salt for all hashes in this table
        salt_used = secrets.token_hex(salt_length // 2)[:salt_length]  # Ensure exact length
        print(f"Using salt: {salt_used}")

    print(f"Generating {num_chains} chains of length {chain_length}...")

    # Generate initial plaintexts more randomly
    initial_plaintexts = []
    for i in range(num_chains):
        # Use a more sophisticated approach to generate diverse starting points
        seed = hashlib.sha256(f"seed_{i}_{charset}".encode()).digest()
        plaintext = ""
        for j in range(password_len):
            index = seed[j % len(seed)] % len(charset)
            plaintext += charset[index]
        initial_plaintexts.append(plaintext)

    for i in range(num_chains):
        start_plaintext = initial_plaintexts[i]
        current_plaintext = start_plaintext

        for j in range(chain_length):
            hashed = hash_function(current_plaintext, algorithm, salt_used)
            current_plaintext = reduce_function(hashed, charset, password_len, j)

        end_plaintext = current_plaintext
        table.append((start_plaintext, end_plaintext))

        if (i + 1) % 100 == 0:
            print(f"  ...generated {i + 1}/{num_chains} chains.")

    # Save the table to a CSV file
    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            if use_salt:
                writer.writerow(['salt', 'start_plaintext', 'end_plaintext'])
                writer.writerow([salt_used, '', ''])  # Store salt in first row
                writer.writerows(table)
            else:
                writer.writerow(['start_plaintext', 'end_plaintext'])
                writer.writerows(table)
        print(f"Rainbow table successfully saved to '{output_file}'")
        return True
    except IOError as e:
        print(f"Error saving table to file: {e}")
        return False

def rainbow_table_tool(data=None):
    """Tool function to be called from the GUI for generating a rainbow table."""
    if data:
        charset = data.get("charset", "").strip()
        algorithm = data.get("algorithm", "md5").lower().strip()
        chain_length = data.get("chain_length", 1000)
        num_chains = data.get("num_chains", 10000)
        password_len = data.get("password_len", 6)
        output_file = data.get("output_file", "").strip()
        use_salt = data.get("use_salt", False)
        salt_length = data.get("salt_length", 8)
    else:
        print("=== Rainbow Table Generator Tool ===")
        print("This tool generates a rainbow table for password cracking.")
        print("A rainbow table is a precomputed table of hash chains used to crack passwords.")
        print("WARNING: This can be a very slow and resource-intensive process!")
        print("Generation time depends on chain length, number of chains, and password length.")
        print()
        print("Parameters explanation:")
        print("- Charset: Characters to use (e.g., 'abc123' for lowercase + digits)")
        print("- Algorithm: Hash algorithm (md5, sha256, etc.)")
        print("- Chain length: How many hash/reduce operations per chain (higher = better coverage but slower)")
        print("- Number of chains: How many starting points (higher = better coverage but larger file)")
        print("- Password length: Maximum length of passwords to generate")
        print("- Use salt: Whether to add salt to hashes (makes cracking harder but table specific)")
        print("- Salt length: Length of salt in characters (only used if salt is enabled)")
        print()
        print("Example: charset='abc123', algorithm='md5', chain_length=1000, chains=10000, length=4")
        print("This would generate a table for 4-character passwords using a,b,c,1,2,3")
        print()

        charset = input("Enter the character set (e.g., 'abcdefghijklmnopqrstuvwxyz0123456789'): ").strip()
        algorithm = input("Enter the hash algorithm (e.g., 'md5', 'sha256'): ").lower().strip()

        try:
            chain_length = int(input("Enter the chain length (recommended: 1000-10000): ").strip())
            num_chains = int(input("Enter the number of chains (recommended: 10000-100000): ").strip())
            password_len = int(input("Enter the password length (e.g., 6-8): ").strip())
        except ValueError:
            print("Invalid number entered. Please enter valid integers.")
            return

        use_salt_input = input("Use salt for hashes? (y/n): ").lower().strip()
        use_salt = use_salt_input in ['y', 'yes', 'true', '1']

        salt_length = 8  # Default
        if use_salt:
            try:
                salt_length = int(input("Enter salt length (default 8): ").strip() or "8")
            except ValueError:
                print("Invalid salt length, using default of 8.")
                salt_length = 8

        output_file = input("Enter the output CSV file name (e.g., 'rainbow_table.csv'): ").strip()

    if not all([charset, algorithm, output_file]):
        print("All fields are required.")
        return

    if algorithm not in hashlib.algorithms_available:
        print(f"Error: Unsupported hash algorithm '{algorithm}'.")
        return

    generate_rainbow_table(charset, algorithm, chain_length, num_chains, password_len, output_file, use_salt, salt_length)

if __name__ == '__main__':
    rainbow_table_tool()
