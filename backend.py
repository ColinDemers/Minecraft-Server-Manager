import logging
import subprocess
import os
import sys
import requests
import urllib
import time
import threading
import json
import shutil
import tempfile

cwd = os.path.dirname(os.path.abspath(__file__))
process = None
running = True

logging.basicConfig(
   level=logging.DEBUG,
   format='%(asctime)s - %(levelname)s - %(message)s',
   handlers=[
       logging.StreamHandler(),
       logging.FileHandler('app.log')
   ]
)

lock = threading.Lock()

def output():
   global process
   while running:
       with lock:
           line = process.stdout.readline()
       if line == '' and process.poll() is not None:
           break
       if line:
           logging.info(line.strip())

def start(server):
   global process, thread, running
   logging.info(f'Server {server} starting')

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
       data = json.load(file)

   if process is None:
       try:
           process = subprocess.Popen(
               ['java', f'-Xmx{data["maximum"]}M', f'-Xms{data["minimum"]}M', '-jar', f'{os.path.join(os.getcwd(), server)}/{server}.jar', 'nogui'],
               cwd=os.path.join(os.getcwd(), server),
               stdout=subprocess.PIPE,
               stderr=subprocess.STDOUT,  # Combine stderr with stdout
               stdin=subprocess.PIPE,
               text=True,
               bufsize=1
           )
       except FileNotFoundError as e:
           logging.critical(f'Java not found on your system or in your system path: {e}')
           return

       running = True
       thread = threading.Thread(target=output)
       thread.start()
   else:
       logging.info(f'Server {server} is already running.')

def stop(server=None):
   try:
       global process, running, thread
       if process is not None:
           logging.warning(f'Server {server} stopping')
           try:
               process.stdin.write(f'stop\n')
               process.stdin.flush()
               running = False
               if thread.is_alive():
                   thread.join()
               process = None
               logging.info(f'Server {server} stopped')
           except Exception as e:
               logging.error(f'An error closing, terminating: {e}')
               if process is not None:
                   process.terminate()
                   process = None
       else:
           logging.info(f'Server {server} not running')
   except Exception as e:
       logging.error(e)

def command(server=None, command=None):
   global process
   if command:
       if process is not None:
           logging.info(f"Running command: {command}")
           process.stdin.write(f'{command}\n')
           process.stdin.flush()
       else:
           logging.error(f'Server {server} is not running. Cannot run command.')
   else:
       logging.error('Command not found')

def create(server = None, type = 'paper'):
    logging.info(f'Creating server {server}')
    url = f"https://api.github.com/repos/ColinDemers/Minecraft-Server-Manager/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        response = response.json()
    else:
        logging.error("Failed to fetch the latest release, are you connected to the internet with access to Github.com?")

    if response:
        with open(os.path.join(sys.path[0], "version.json"), "r") as f:
            data = json.load(f)

    url = None

    if type == 'paper':
        latest, headers = getCurrentVersion(type)

        if latest == None:
            logging.critical('Error: Could not find latest version')
            return
        
        build_url = f"https://fill.papermc.io/v3/projects/{type}/versions/{latest}/builds"
        response = requests.get(build_url, headers=headers)
        response.raise_for_status()
        
        stable = [build for build in response.json() if build['channel'] == 'STABLE']
        
        if not stable:
            logging.debug("No stable build found.")
            return
        
        latestStable = stable[0]
        
        url = latestStable['downloads']['server:default']['url']

    if url:
        os.makedirs(os.path.join(os.getcwd(), server), exist_ok=True)

        with open(os.path.join(os.getcwd(), server, 'eula.txt'), 'w') as eula:
            eula.write('eula=true')

        with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as backend:
                    backend.write(json.dumps({"version": latest,"maximum": "2048","minimum": "1024", "playit": "False", "bedrock": "False"}))

        logging.info(f"Downloading from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(os.path.join(os.path.join(os.getcwd(), server), f'{server}.jar'), 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        logging.info("Download completed")

def update(server, type='paper'):
  
   stop(server)

   logging.warning('Updating Server')

   latest, headers = getCurrentVersion('paper')

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
       data = json.load(file)
   version = data['version']
   playit = data['playit']
   Bbedrock = data['bedrock']

   if latest == version:
       logging.info('Server already on latest version')
       return

   logging.info(f'Version mismatch of: Current {version} to Latest {latest}, updating')
   logging.critical(f'NOT UPDATING PLUGINS THAT WERE MANUALLY INSTALLED, PLEASE UPDATE THOSE MANUALLY')

   logging.info('Backing up servers')

   servers = []
   subfolders = [os.path.basename(f.path) for f in os.scandir(os.getcwd()) if f.is_dir()]
   for folder in subfolders:
       if folder != '__pycache__':
           if folder != 'backups':
               servers.append(folder)

   if len(servers) == 0:
       logging.error('No servers found, this should not be possible and if you are seeing this message something very bad has happened')
   else:
       for Bserver in servers:
           os.makedirs(os.path.join(os.getcwd(), 'backups'), exist_ok=True)
           shutil.copytree(os.path.join(os.getcwd(), Bserver), os.path.join(os.getcwd(), 'backups', Bserver), dirs_exist_ok=True)

   logging.info('Downloading latest version')

   build_url = f"https://fill.papermc.io/v3/projects/{type}/versions/{latest}/builds"
   response = requests.get(build_url, headers=headers)
   response.raise_for_status()
  
   stable = [build for build in response.json() if build['channel'] == 'STABLE']
  
   if not stable:
       logging.debug("No stable build found.")
       return
  
   latestStable = stable[0]
  
   url = latestStable['downloads']['server:default']['url']

   with tempfile.NamedTemporaryFile(delete=False) as temp:
       logging.info(f"Downloading from {url}")
       response = requests.get(url, stream=True)
       response.raise_for_status()

       if response.status_code == 200:
           for chunk in response.iter_content(chunk_size=8192):
               temp.write(chunk)
           tempPath = temp.name
           logging.debug(f'Temporary file created at: {tempPath}')
       else:
           logging.debug(f'Failed to download file: {response.status_code}')

   shutil.move(tempPath, os.path.join(os.getcwd(), server, f"{server}.jar"))
   logging.debug(f'File moved to permanent location: {os.path.join(os.getcwd(), server, f"{server}.jar")}')

   if os.path.exists(tempPath):
       os.remove(tempPath)
       logging.debug(f'Temporary file deleted: {tempPath}')

   if playit == True:
       url = 'https://github.com/playit-cloud/playit-minecraft-plugin/releases/latest/download/playit-minecraft-plugin.jar'
       with tempfile.NamedTemporaryFile(delete=False) as temp:
               logging.info(f"Downloading from {url}")
               response = requests.get(url, stream=True)
               response.raise_for_status()

               if response.status_code == 200:
                   for chunk in response.iter_content(chunk_size=8192):
                       temp.write(chunk)
                   tempPath = temp.name
                   logging.debug(f'Temporary file created at: {tempPath}')
               else:
                   logging.debug(f'Failed to download file: {response.status_code}')

               shutil.move(tempPath, os.path.join(os.getcwd(), server, 'plugins', 'playit.jar'))
               logging.debug(f'File moved to permanent location: {os.path.join(os.getcwd(), server, "plugins", "playit.jar")}')

               if os.path.exists(tempPath):
                   os.remove(tempPath)
                   logging.debug(f'Temporary file deleted: {tempPath}')

   if Bbedrock == True:
       bedrock(server)

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
       data = json.load(file)

   data['version'] = latest

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as file:
       json.dump(data, file, indent=4)

   logging.info('Server updated')

def downloadPlayit(server):
   url = 'https://github.com/playit-cloud/playit-minecraft-plugin/releases/latest/download/playit-minecraft-plugin.jar'

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
       data = json.load(file)

   data['playit'] = True

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as file:
       json.dump(data, file, indent=4)

   logging.info(f"Downloading playit {url}")
   response = requests.get(url, stream=True)
   response.raise_for_status()

   os.makedirs(os.path.join(os.getcwd(), server, 'plugins'), exist_ok=True)

   with open(os.path.join(os.path.join(os.getcwd(), server, 'plugins'), f'playit.jar'), 'wb') as file:
       for chunk in response.iter_content(chunk_size=8192):
           file.write(chunk)
  
   logging.info('Playit downloaded')

def bedrock(server):

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
       data = json.load(file)

   data['bedrock'] = True

   with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as file:
       json.dump(data, file, indent=4)
  
   geyserLatest = 'https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot'
   floodgateLatest = 'https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot'
   viaversionLatest = modrinth('viaversion')

   bedrockPlugins = {'geyser': geyserLatest, 'floodgate': floodgateLatest, 'viaversion': viaversionLatest}

   os.makedirs(os.path.join(os.getcwd(), server, 'plugins'), exist_ok=True)
   for plugin, url in bedrockPlugins.items():
       logging.critical(url)
       with tempfile.NamedTemporaryFile(delete=False) as temp:
           logging.info(f"Downloading from {url}")
           response = requests.get(url, stream=True)
           response.raise_for_status()

           if response.status_code == 200:
               for chunk in response.iter_content(chunk_size=8192):
                   temp.write(chunk)
               tempPath = temp.name
               logging.debug(f'Temporary file created at: {tempPath}')
           else:
               logging.debug(f'Failed to download file: {response.status_code}')

           shutil.move(tempPath, os.path.join(os.getcwd(), server, "plugins", f"{plugin}.jar"))
           logging.debug(f'File moved to permanent location: {os.path.join(os.getcwd(), server, "plugins", f"{plugin}.jar")}')

           if os.path.exists(tempPath):
               os.remove(tempPath)
               logging.debug(f'Temporary file deleted: {tempPath}')
          
           logging.info(f'Downloaded {plugin}')

def getCurrentVersion(type='paper', agent="cool-project/1.0.0 (contact@me.com)"):
   version_url = f"https://fill.papermc.io/v3/projects/{type}"
   headers = {"User-Agent": agent}
  
   response = requests.get(version_url, headers=headers)
   if response.status_code != 200:
       logging.error(f"Received status code {response.status_code}")
       logging.debug(response.text)
       return None
  
   data = response.json()
   latest = max(max(data['versions'].values(), key=lambda v: list(map(int, v[0].split('.')))), key=lambda v: list(map(int, v.split('.'))))

   if 'versions' not in data or not data['versions']:
       logging.error("No versions found in the response.")
       return None
  
   return latest, headers

def modrinth(id):
   url = f"https://api.modrinth.com/v2/project/{id}/version"
  
   try:
       response = requests.get(url)
       response.raise_for_status()
       data = response.json()

       if data:
           latest_version = data[0]
           files = latest_version.get('files', [])
           if files:
               download_url = files[0].get('url')
               return download_url
           else:
               logging.error(f"No files found for {id}.")
       else:
           logging.error(f"No versions found for {id}.")
   except requests.RequestException as e:
       logging.error(f"Error fetching data for {id}: {e}")