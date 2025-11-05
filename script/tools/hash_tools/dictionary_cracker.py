import hashlib
import os

def dictionary_crack(target_hash, algorithm, wordlist_path):
    """
    Performs a dictionary attack on a hash using a pure Python implementation.
    """
    if not os.path.exists(wordlist_path):
        return f"Error: Wordlist file not found at '{wordlist_path}'"

    try:
        # Check if the algorithm is supported by hashlib
        hashlib.new(algorithm)
    except ValueError:
        return f"Error: Unsupported hash algorithm '{algorithm}' for hashlib. Please use a standard algorithm like 'md5', 'sha1', 'sha256', etc."

    print(f"Starting dictionary attack on '{target_hash[:15]}...' with algorithm '{algorithm}'...")

    try:
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                word = line.strip()

                # Hash the word from the wordlist
                hashed_word = hashlib.new(algorithm)
                hashed_word.update(word.encode('utf-8'))

                if hashed_word.hexdigest() == target_hash:
                    return f"Success! Password found: {word}"

                if (i + 1) % 100000 == 0:
                    print(f"  ...checked {i + 1} passwords.")

    except Exception as e:
        return f"An error occurred while reading the wordlist: {e}"

    return "Attack finished. Password not found in the provided wordlist."

def dictionary_cracker_tool(data=None):
    """
    Tool function to be called from the GUI for the dictionary cracker.
    """
    if data:
        target_hash = data.get("hash", "").lower().strip()
        algorithm = data.get("algorithm", "md5").lower().strip()
        wordlist_path = data.get("wordlist", "").strip()
    else:
        print("=== Dictionary Cracker Tool ===")
        print("This tool performs a dictionary attack on a hash using a wordlist.")
        print("It tries each word from the wordlist against the target hash.")
        print("This is a pure Python implementation and may be slow for large wordlists.")
        print("For better performance, consider using specialized tools like Hashcat.")
        print()
        print("Supported algorithms: md5, sha1, sha224, sha256, sha384, sha512, etc.")
        print("Make sure the wordlist file exists and contains one word per line.")
        print()
        target_hash = input("Enter the hash to crack (lowercase hex string): ").lower().strip()
        algorithm = input("Enter the hash algorithm (e.g., md5, sha256): ").lower().strip()
        wordlist_path = input("Enter the full path to the wordlist file (e.g., C:\\wordlists\\rockyou.txt): ").strip()

    if not all([target_hash, algorithm, wordlist_path]):
        print("All fields are required.")
        return

    result = dictionary_crack(target_hash, algorithm, wordlist_path)
    print(result)

if __name__ == '__main__':
    dictionary_cracker_tool()
