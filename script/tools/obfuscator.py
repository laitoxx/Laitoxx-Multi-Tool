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

import base64
import marshal
import os
import zlib

from ..shared_utils import Color


def obfuscate_code(original_code, method):
    """
    Applies a specific obfuscation method to the given code string.
    """
    try:
        if method == 1:
            # Marshal compilation
            compiled_code = compile(original_code, '<string>', 'exec')
            dumped_code = marshal.dumps(compiled_code)
            return f"import marshal; exec(marshal.loads({repr(dumped_code)}))"
        elif method == 2:
            # Zlib compression
            compressed_code = zlib.compress(original_code.encode('utf-8'))
            return f"import zlib; exec(zlib.decompress({repr(compressed_code)}).decode('utf-8'))"
        elif method == 3:
            # Marshal + Zlib + Base64
            compiled_code = compile(original_code, '<string>', 'exec')
            marshaled_code = marshal.dumps(compiled_code)
            compressed_code = zlib.compress(marshaled_code)
            encoded_code = base64.b64encode(compressed_code)
            return f"import marshal, zlib, base64; exec(marshal.loads(zlib.decompress(base64.b64decode({repr(encoded_code)}))))"
        else:
            return None
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error during obfuscation: {e}")
        return None


def obfuscate_tool():
    """
    Provides a user interface for obfuscating Python files.
    """
    while True:
        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Python File Obfuscation Tool")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Marshal")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Zlib")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Marshal + Zlib + Base64")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using all methods")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}0{Color.DARK_GRAY}]{Color.LIGHT_RED} Back to Main Menu")

        choice = input(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Select an option: {Color.RESET}").strip()

        if choice == "0":
            return

        if choice not in ['1', '2', '3', '4']:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid option. Please select a valid choice.")
            continue

        file_path = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter the path to the Python file (.py): {Color.RESET}").strip()

        if not os.path.isfile(file_path) or not file_path.endswith('.py'):
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} File does not exist or is not a .py file.")
            continue

        try:
            with open(file_path, encoding='utf-8') as f:
                original_code = f.read()
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error reading file: {e}")
            continue

        methods_to_run = []
        if choice == '4':
            methods_to_run = [1, 2, 3]
        else:
            methods_to_run.append(int(choice))

        for method in methods_to_run:
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Applying obfuscation method {method}...")
            obfuscated_code = obfuscate_code(original_code, method)

            if obfuscated_code:
                output_filename = file_path.replace(
                    '.py', f'_obf_method{method}.py')
                try:
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        f.write(obfuscated_code)
                    print(
                        f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscation successful. Saved as {output_filename}")
                except Exception as e:
                    print(
                        f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error saving file {output_filename}: {e}")
        break  # Exit the loop after processing a file
