#Add create update function to backend while creating a server

import requests
import logging
import json
import os
import sys

def update():
    url = f"https://api.github.com/repos/ColinDemers/Minecraft-Server-Manager/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        response = response.json()
    else:
        logging.error("Failed to fetch the latest release, are you connected to the internet with access to Github.com?")

    if response:
        with open(os.path.join(sys.path[0], "version.json"), "r") as f:
            data = json.load(f)
        if data["version"] != response["tag_name"]:
            logging.info(f"New version available: {response['tag_name']}")
            logging.info("Updating Minecraft Server Manager...")
            with open(os.path.join(sys.path[0], "version.json"), "w") as f:
                data["version"] = response["tag_name"]
                json.dump(data, f, indent=4)
            logging.info("Minecraft Server Manager updated successfully!")

update()