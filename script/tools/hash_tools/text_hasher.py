import hashlib

def hash_text(text, algorithm):
    """
    Hashes the given text using the specified algorithm.
    """
    try:
        hasher = hashlib.new(algorithm)
        hasher.update(text.encode('utf-8'))
        return hasher.hexdigest()
    except ValueError:
        return f"Unsupported hash algorithm: {algorithm}"

def text_hasher_tool(data=None):
    """
    Tool function to be called from the GUI.
    It will take input for the text and algorithm.
    """
    if data:
        text = data.get("text", "")
        algorithm = data.get("algorithm", "sha256").lower().strip()
    else:
        print("=== Text Hasher Tool ===")
        print("This tool allows you to hash any text using various cryptographic algorithms.")
        print("Available algorithms include MD5, SHA1, SHA256, SHA512, and many others.")
        print("Note: MD5 and SHA1 are considered insecure for cryptographic purposes.")
        print("Use stronger algorithms like SHA256 or SHA512 for security.")
        print()
        print("Available algorithms: " + ", ".join(sorted(hashlib.algorithms_available)))
        print()
        text = input("Enter the text you want to hash (can be any string): ")
        algorithm = input("Enter the hash algorithm (e.g., md5, sha256, sha512): ").lower().strip()

    if not text:
        print("Text cannot be empty.")
        return

    if algorithm not in hashlib.algorithms_available:
        print(f"Error: Unsupported or unknown hash algorithm '{algorithm}'.")
        print("Please choose from the available algorithms.")
        return

    hashed_text = hash_text(text, algorithm)
    print(f"Algorithm: {algorithm}")
    print(f"Original Text: {text}")
    print(f"Hashed Text: {hashed_text}")

if __name__ == '__main__':
    text_hasher_tool()
