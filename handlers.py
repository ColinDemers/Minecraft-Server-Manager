import logging
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import QObject, Signal

class QTextEditLogHandler(logging.Handler, QObject):
   new_log = Signal(str)

   def __init__(self, text_edit: QTextEdit):
       logging.Handler.__init__(self)
       QObject.__init__(self)
       self.text_edit = text_edit
       self.new_log.connect(self.append_text)

   def emit(self, record):
       msg = self.format(record)
       self.new_log.emit(msg)

   def append_text(self, msg):
       self.text_edit.append(msg)
       self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())
