import requests

url = "https://i.gifer.com/origin/a7/a7b92681655159733a306464c70f27c1_w200.gif"
response = requests.get(url)

if response.status_code == 200:
    with open("background.gif", "wb") as f:
        f.write(response.content)
    print("GIF downloaded successfully.")
else:
    print(f"Failed to download GIF. Status code: {response.status_code}")
