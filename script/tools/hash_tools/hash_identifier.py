"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

from hashid import HashID


def identify_hash(hash_string):
    hashid = HashID()
    results = hashid.identifyHash(hash_string)
    return results


def hash_identifier_tool(data=None):
    if data:
        hash_input = data.get("hash", "").strip()
    else:
        print("=== Hash Identifier Tool ===")
        print("This tool identifies the possible types of a given hash string.")
        print("It uses the hashid library to analyze the hash format and length.")
        print("Common hash types include MD5, SHA1, SHA256, bcrypt, etc.")
        print("Note: This tool provides possible matches, not definitive identification.")
        print()
        hash_input = input(
            "Enter the hash string you want to identify (e.g., a long string of letters/numbers): ").strip()

    if not hash_input:
        print("Hash input cannot be empty.")
        return

    possible_hashes = identify_hash(hash_input)

    if not possible_hashes:
        print("Could not identify the hash type. It may be an unknown format or have an incorrect length.")
    else:
        print(f"Possible hash types for '{hash_input}':")
        for p_hash in possible_hashes:
            print(f"- {p_hash.name}")


if __name__ == '__main__':
    hash_identifier_tool()
