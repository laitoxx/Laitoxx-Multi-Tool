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

import os
from ..shared_utils import Color


def search_database():
    """Searches for data in files located in the 'db' directory."""
    db_dir = 'db/'
    if not os.path.exists(db_dir) or not os.path.isdir(db_dir):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Directory '{db_dir}' does not exist. Please create it and add files for searching.")
        return

    files_in_db = [f for f in os.listdir(
        db_dir) if os.path.isfile(os.path.join(db_dir, f))]

    if not files_in_db:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No database files found in the '{db_dir}' directory.")
        return

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} {len(files_in_db)} databases found.\n")

    data_to_search = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter data to search: ")
    if data_to_search is None:
        return

    if not data_to_search:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No search data provided.")
        return

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Searching...\n")

    found_results = False
    for filename in files_in_db:
        filepath = os.path.join(db_dir, filename)
        try:
            with open(filepath, encoding='UTF-8', errors='ignore') as f:
                header_line = f.readline().strip()
                delimiters = [',', ';', '\t', '|']
                delimiter = next(
                    (d for d in delimiters if d in header_line), None)
                header = header_line.split(delimiter) if delimiter else [
                    header_line]

                for line in f:
                    if data_to_search in line:
                        if not found_results:
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Results:\n")
                            found_results = True

                        formatted_result = f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{filename} {Color.DARK_RED}]─" + '─' * 30 + "\n"

                        line_parts = line.strip().split(
                            delimiter) if delimiter else [line.strip()]

                        for i, part in enumerate(line_parts):
                            header_name = header[i] if i < len(
                                header) else f"Field {i + 1}"
                            formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{header_name.strip()}: {Color.WHITE}{part.strip()}\n"

                        formatted_result += f"{Color.DARK_RED}└" + \
                            '─' * (40 + len(filename)) + "\n"
                        print(formatted_result)
                        # Stop after first match in file, can be removed if all matches are needed
                        break

        except FileNotFoundError:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error: File not found {filename}")
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error reading file {filename}: {e}")

    if not found_results:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} No matches found.")
