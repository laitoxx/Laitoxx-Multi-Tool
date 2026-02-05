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

from telegraph import TelegraphException

from ..shared_utils import MAX_TITLE_LENGTH, Color, telegraph


def create_article_loop():
    """
    Handles the logic for creating a Telegraph article with a logger link.
    """
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Create a new logger article...")

    # Get Title
    while True:
        title = input(
            f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the article title (max {MAX_TITLE_LENGTH} chars): {Color.RESET}").strip()
        if 0 < len(title) <= MAX_TITLE_LENGTH:
            break
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The title must be between 1 and {MAX_TITLE_LENGTH} characters.")

    # Get Content
    content = input(
        f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the article content: {Color.RESET}").strip()

    # Get Grabify Link
    while True:
        link = input(
            f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the Grabify logger link (must end with .jpg or .png): {Color.RESET}").strip()
        if link.startswith("https://grabify.link/") and (link.endswith(".jpg") or link.endswith(".png")):
            break
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid link format. It must be a grabify.link ending in .jpg or .png.")

    # Get Number of Links
    while True:
        try:
            num_links_str = input(
                f"{Color.DARK_GRAY}  - {Color.WHITE}How many times to embed the logger? (e.g., 1-10): {Color.RESET}").strip()
            num_links = int(num_links_str)
            if 1 <= num_links <= 50:  # Limit to 50 to avoid abuse
                break
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Please enter a number between 1 and 50.")
        except ValueError:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Please enter a valid number.")

    # Create HTML content
    full_content = f"<p>{content}</p>" + f'<img src="{link}"/>' * num_links

    try:
        if not telegraph:
            raise TelegraphException("Telegraph API is not initialized.")

        response = telegraph.create_page(
            title=title, html_content=full_content)

        print(
            f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Article created successfully!")
        print(
            f"{Color.DARK_GRAY}  - {Color.WHITE}Link: {Color.LIGHT_BLUE}{response['url']}")

    except TelegraphException as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Telegraph API error: {e}")
    except Exception as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}")


def show_faq():
    """
    Displays a simple FAQ for the IP logger tool.
    """
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} IP Logger FAQ")
    print(f"{Color.DARK_GRAY}  1. {Color.WHITE}Go to {Color.LIGHT_BLUE}grabify.link{Color.WHITE} and create a tracking link.")
    print(f"{Color.DARK_GRAY}  2. {Color.WHITE}In the tracking link settings, ensure the extension is set to {Color.LIGHT_BLUE}.png{Color.WHITE} or {Color.LIGHT_BLUE}.jpg{Color.WHITE}.")
    print(f"{Color.DARK_GRAY}  3. {Color.WHITE}Use that link in this tool to embed it in a Telegraph article.")
    print(f"{Color.DARK_GRAY}  4. {Color.WHITE}When a user opens your article, their IP will be logged on the Grabify website.")
    print(f"{Color.DARK_GRAY}  - {Color.WHITE}Detailed tutorial: {Color.GRAY}https://telegra.ph/Tutor-po-sozdaniyu-ssylki-07-21")


def logger_ip():
    """
    Main function for the IP logger tool.
    """
    while True:
        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} IP Logger Main Menu")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Create an article")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} FAQ")
        print(
            f"  {Color.DARK_GRAY}[{Color.DARK_RED}0{Color.DARK_GRAY}]{Color.LIGHT_RED} Back to Main Menu")

        choice = input(
            f"{Color.LIGHT_BLUE}Choose an option: {Color.RESET}").strip()

        if choice == '1':
            create_article_loop()
        elif choice == '2':
            show_faq()
        elif choice == '0':
            print(f"{Color.DARK_RED}Returning to main menu...{Color.RESET}")
            break
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid choice. Please try again.")
