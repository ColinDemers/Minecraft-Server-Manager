import sys
import os
import backend
import logging
import time
import json

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton, QCheckBox, QLineEdit, QHBoxLayout, QSplitter, QTextEdit, QSizePolicy, QMessageBox
from PySide6.QtCore import Qt

from handlers import QTextEditLogHandler

class MainWindow(QMainWindow):
   def __init__(self):
       super().__init__()

       self.setWindowTitle("Minecraft Server Manager")

       # Create a QTabWidget and store it as an instance variable
       self.tabs = QTabWidget()
       self.tabs.setTabPosition(QTabWidget.North)
       self.tabs.setMovable(True)

       # Create tabs with simple text labels
       self.servers = []
       self.load_servers()

       self.setCentralWidget(self.tabs)

   def load_servers(self):
       subfolders = [os.path.basename(f.path) for f in os.scandir(os.getcwd()) if f.is_dir()]
       for folder in subfolders:
           if os.path.exists(os.path.join(os.getcwd(), folder, 'backend.json')):
               self.servers.append(folder)

       if len(self.servers) == 0:
           self.create_server_tab()
       else:
           self.add_server_tabs()

   def create_server_tab(self):
       # Create Server tab
       tab_content = QWidget()
       layout = QVBoxLayout()
      
       label = QLabel("Create New Server")
       font = label.font()
       font.setPointSize(15)
       label.setFont(font)
       label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

       self.checkbox = QCheckBox()
       self.checkbox.setCheckState(Qt.CheckState.Unchecked)
       self.checkbox.setText('Agree to the Minecraft EULA (https://www.minecraft.net/en-us/eula)')
       self.checkbox.stateChanged.connect(self.show_state)

       self.lineedit = QLineEdit()
       self.lineedit.setMaxLength(10)
       self.lineedit.setPlaceholderText("Server name")
       self.lineedit.textEdited.connect(self.text_edited)

       self.button = QPushButton('Create Server')
       self.button.setEnabled(False)
       self.button.clicked.connect(self.button_pressed)

       layout.addWidget(label)
       layout.addWidget(self.lineedit)
       layout.addWidget(self.checkbox)
       layout.addWidget(self.button)

       tab_content.setLayout(layout)
       self.tabs.addTab(tab_content, 'Create Server')

   def add_server_tabs(self):
       for server in self.servers:
           tab_content = QWidget()
           layout = QVBoxLayout()

           # Top Buttons
           button_layout = QHBoxLayout()
           start_button = QPushButton('Start')
           stop_button = QPushButton('Stop')
           update_button = QPushButton('Update')
           button_layout.addWidget(start_button)
           button_layout.addWidget(stop_button)
           button_layout.addWidget(update_button)
           layout.addLayout(button_layout)

           splitter = QSplitter()

           left_splitter = QWidget()
           left = QVBoxLayout()

           right_splitter = QWidget()
           right = QVBoxLayout()

           # Left Splitter
           options = QTabWidget()
           options.addTab(QLabel('Work In Progress'), 'General')

           #Properties Tab

           properties_widget = QWidget()
           properties_layout = QVBoxLayout()

           self.properties_text = QTextEdit()

           try:
               with open(f'{os.path.join(os.getcwd(), server)}/server.properties', 'r') as file:
                   contents = file.read()
                   self.properties_text.setText(contents)
           except Exception as e:
               self.properties_text.setText(f"Error loading file: {e}. \n\nThis error will occur if you have not started the server yet, try starting it first. You may have to re-open the program once you do.")

           save_button = QPushButton('Save')

           self.properties_text.setSizePolicy(
               QSizePolicy.Policy.Expanding,
               QSizePolicy.Policy.Expanding
           )

           properties_layout.addWidget(self.properties_text)
           properties_layout.addWidget(save_button)

           properties_widget.setLayout(properties_layout)
           options.addTab(properties_widget, 'Properties')

           save_button.pressed.connect(lambda server_name=server: self.properties_save(server_name))

           #Memory Tab

           memory_widget = QWidget()
           memory_layout = QVBoxLayout()

           label = QLabel('How much memory do you want to give to your server? It has a direct effect on performance. Memory is in MB, one GB = 1024 MB, e.g., 8 GB = 1024 x 8 = 8192 MB')
           label.setWordWrap(True)
           label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

           minimum = QHBoxLayout()
           maximum = QHBoxLayout()

           minimum.addWidget(QLabel('Minimum Memory'))
           maximum.addWidget(QLabel('Maximum Memory'))

           with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
               data = json.load(file)

           minimumBox = QLineEdit(data['minimum'])
           maximumBox = QLineEdit(data['maximum'])

           minimum.addWidget(minimumBox)
           maximum.addWidget(maximumBox)

           memory_layout.addWidget(label)
           memory_layout.addLayout(minimum)
           memory_layout.addLayout(maximum)

           minimumBox.textChanged.connect(lambda text: self.minimum_changed(text, server))
           maximumBox.textChanged.connect(lambda text: self.maximum_changed(text, server))

           memory_layout.addStretch()

           memory_widget.setLayout(memory_layout)

           options.addTab(memory_widget, 'Memory')

           #Playit.gg

           bedrock_widget = QWidget()
           bedrock_layout = QVBoxLayout()
           bedrock_label = QLabel('Uses GeyserMC.org (Geyser and Floodgate), along with ViaVersion to enable Minecraft: Bedrock Edition players to join Minecraft: Java Edition servers. This may cause errors. ')
           bedrock_label.setWordWrap(True)
           bedrock_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

           bedrock_download_button = QPushButton('Enable Bedrock Support')

           bedrock_layout.addWidget(bedrock_label)
           bedrock_layout.addWidget(bedrock_download_button)

           bedrock_download_button.clicked.connect(lambda text: self.download_bedrock(server))

           bedrock_layout.addStretch()

           bedrock_widget.setLayout(bedrock_layout)

           options.addTab(bedrock_widget, 'Bedrock')

           #Bedrock Tab

           playit = QWidget()
           playit_layout = QVBoxLayout()

           playit_label = QLabel('Playit.gg is a free online service build specifically for minecraft Java servers, however it does work with anything else, to connect it to the internet. For this server, we will use it to get other players outside the local network to connect and play. Once you click the download button below, a playit.gg client will download (you might need to restart the server). Next, you will have to go to https://playit.gg/ and create an account. In the console, it will be telling you to go to a website, do that and add the agent (instance). Once complete, create a tunnel, and make it redirect to 127.0.0.1 on port 25565 (unless set otherwise, you can find it in your properties tab). It will give you a domain, and that will be used for other players to connect to your server. Please note the consequences of allowing access to the internet. You can use this domain, however the client will be set up for you via a plugin: https://docs.famlam.ca/server-hosting/setup-playit-gg')
           playit_label.setWordWrap(True)
           playit_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

           download_button = QPushButton('Download Playit.gg')

           playit_layout.addWidget(playit_label)
           playit_layout.addWidget(download_button)

           download_button.clicked.connect(lambda text: self.download_playit(server))

           playit_layout.addStretch()

           playit.setLayout(playit_layout)

           options.addTab(playit, 'Playit.gg')

           #Other stuff

           left.addWidget(options)

           # Right Splitter
           self.console = QTextEdit()  # Store the console as an instance variable

           log_handler = QTextEditLogHandler(self.console)
           log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
           logging.getLogger().addHandler(log_handler)

           self.console.setReadOnly(True)
           self.console.setSizePolicy(
               QSizePolicy.Policy.Expanding,
               QSizePolicy.Policy.Expanding
           )
           right.addWidget(self.console)

           command = QHBoxLayout()
           command.addWidget(QLabel('Command:'))
           self.prompt = QLineEdit()
           command.addWidget(self.prompt)
           send = QPushButton('Send')
           command.addWidget(send)

           right.addLayout(command)

           self.prompt.returnPressed.connect(lambda server_name=server: self.send_command(server_name))

           send.pressed.connect(lambda server_name=server: self.send_command(server_name))

           left_splitter.setLayout(left)
           right_splitter.setLayout(right)
           splitter.addWidget(left_splitter)
           splitter.addWidget(right_splitter)

           layout.addWidget(splitter)

           tab_content.setLayout(layout)
           self.tabs.addTab(tab_content, server)

           # Connect start and stop buttons to their respective functions
           start_button.clicked.connect(lambda _, s=server: self.start_server(s))
           stop_button.clicked.connect(lambda _, s=server: self.stop_server(s))
           update_button.clicked.connect(lambda _, s=server: self.update_server(s))

   def download_playit(self, server):
       backend.downloadPlayit(server)

   def download_bedrock(self, server):
       backend.bedrock(server)

   def send_command(self, server):
           command_text = self.prompt.text()
           if command_text:
               logging.info(f"Sending command: {command_text}")
               backend.command(server, command_text)
               self.prompt.clear()

   def start_server(self, server):
       # Call the backend start function and pass the console
       backend.start(server)

   def update_server(self, server):
       backend.update(server)

   def properties_save(self, server):
       try:
           with open(f'{os.path.join(os.getcwd(), server)}/server.properties', 'w') as file:
               content = self.properties_text.toPlainText()
               file.write(content)

               reply = QMessageBox.question(self, 'Restart Server',
                               "The server has to be restarted for these changed to be applied, would you like to restart?",
                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

               if reply == QMessageBox.Yes:
                   backend.stop(server)
                   backend.start(server)
               else:
                   event.ignore()  # Ignore the event to keep the window open
       except Exception as e:
           logging.error(f"Error saving file: {e}")

   def stop_server(self, server):
       # Call the backend stop function
       backend.stop(server)

   def minimum_changed(self, text, server):
       if text.isdigit():
           with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
               data = json.load(file)

           data['minimum'] = text

           with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as file:
               json.dump(data, file, indent=4)

   def maximum_changed(self, text, server):
       if text.isdigit():
           with open(os.path.join(os.getcwd(), server, 'backend.json'), 'r') as file:
               data = json.load(file)

           data['maximum'] = text

           with open(os.path.join(os.getcwd(), server, 'backend.json'), 'w') as file:
               json.dump(data, file, indent=4)

   def show_state(self, state):
       if state == 2 or (state == True and len(self.lineedit.text()) > 0):
           self.button.setEnabled(True)
       else:
           self.button.setEnabled(False)
  
   def text_edited(self, text):
       state = self.checkbox.isChecked()
       self.show_state(state)

   def button_pressed(self):
       server_name = self.lineedit.text()
       backend.create(server_name)  # Call the backend to create the server
       self.add_server_tab(server_name)  # Add a new tab for the created server

   def add_server_tab(self, server_name):
       tab_content = QWidget()
       layout = QVBoxLayout()
       layout.addWidget(QLabel(f"Server Created, please close and re-open this program"))
       tab_content.setLayout(layout)
       self.tabs.addTab(tab_content, server_name)

   def closeEvent(self, event):
       # Create a confirmation dialog
       reply = QMessageBox.question(self, 'Confirm Exit',
                                    "Are you sure you want to exit? Any running servers will be stopped.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

       if reply == QMessageBox.Yes:
           # Stop all running servers before closing
           for server in self.servers:
               backend.stop(server)  # Call the backend stop function for each server
           event.accept()  # Accept the event to close the window
       else:
           event.ignore()  # Ignore the event to keep the window open

if __name__ == "__main__":
   app = QApplication(sys.argv)
   window = MainWindow()
   window.show()
   app.exec()
