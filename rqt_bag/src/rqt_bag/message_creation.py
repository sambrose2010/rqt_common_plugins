# Software License Agreement (BSD License)
#
# Copyright (c) 2014, Surya Ambrose, Aldebaran
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import rosgraph
import rospkg
import rosmsg
import roslib
from .message_tree import MessageTree

from python_qt_binding.QtCore import Qt, Signal, qErrnoWarning, qWarning
from python_qt_binding.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QComboBox

class MessageCreation(QWidget):

    messageDefined = Signal()

    def __init__(self, timeline):
        super(MessageCreation, self).__init__()

        self.setWindowTitle("Compose the message you want to add")
        self.resize(500, 700)

        self.timeline = timeline
        self.topic_list = self.timeline._get_topics()
        self.topic_name = None
        self.msg_name = None

        _rospack = rospkg.RosPack()
        try:
            # this only works on fuerte and up
            self.package_list = sorted([pkg_tuple[0] for pkg_tuple in rosmsg.iterate_packages(_rospack, rosmsg.MODE_MSG)])
        except Exception, e:
            print e
            # this works up to electric
            self.package_list = sorted(rosmsg.list_packages())

        self.message_list = []

        ## VIEW DEFINITION

        # Top layer widget: topic and message definition
        self.definition_widget = QWidget(self)

        # Top left widget: topic selection
        self.topic_widget = QWidget(self.definition_widget)

        self.topic_selection_widget = QComboBox(self.topic_widget)
        self.topic_composition_widget = QLineEdit(self.topic_widget)

        self.topic_vlayout = QVBoxLayout(self)
        self.topic_vlayout.addWidget(self.topic_selection_widget)
        self.topic_vlayout.addWidget(self.topic_composition_widget)
        self.topic_widget.setLayout(self.topic_vlayout)

        # Top right widget: msg selection
        # self.msg_widget = QWidget(self.definition_widget)

        # self.msg_group_widget = QComboBox(self.msg_widget)
        # self.msg_name_widget = QComboBox(self.msg_widget)
        self.msg_name_widget = QComboBox(self.definition_widget)
        self.msg_name_widget.setEditable(False)

        # self.msg_vlayout = QVBoxLayout(self)
        # self.msg_vlayout.addWidget(self.msg_group_widget)
        # self.msg_vlayout.addWidget(self.msg_name_widget)
        # self.msg_widget.setLayout(self.msg_vlayout)

        # Integrate top left and top right widget into top layer
        self.definition_hlayout = QHBoxLayout(self)
        self.definition_hlayout.addWidget(self.topic_widget)

        # self.definition_hlayout.addWidget(self.msg_widget)
        self.definition_hlayout.addWidget(self.msg_name_widget)
        self.definition_widget.setLayout(self.definition_hlayout)

        # Middle widget 1: Import data from current state
        self.import_button = QPushButton("Import from current position", self)

        # Middle widget 2: message composition
        self.message_tree = MessageTree(self)

        # Bottom widget: Validation button
        self.add_button = QPushButton("Add", self)

        # Integrate all the widgets and the top layer widget into the main layout
        self.main_vlayout = QVBoxLayout(self)
        self.main_vlayout.addWidget(self.definition_widget)
        self.main_vlayout.addWidget(self.import_button)
        self.main_vlayout.addWidget(self.message_tree)
        self.main_vlayout.addWidget(self.add_button)
        self.setLayout(self.main_vlayout)


        ## GUI ELEMENT SETUP

        # Import button
        self.import_button.clicked.connect(self.onImportButtonClicked)
        self.import_button.setEnabled(True)

        # Validation button
        self.add_button.clicked.connect(self.onAddButtonClicked)
        self.add_button.setEnabled(True)

        # Add all available messages
        self.msg_name_widget.currentIndexChanged['QString'].connect(self._handle_message_selected)
        self.msg_name_widget.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # Topic composition
        self.topic_composition_widget.setEnabled(False)
        self.topic_composition_widget.editingFinished.connect(self._handle_topic_composition)

        # Topic selection
        self.topic_selection_widget.currentIndexChanged['QString'].connect(self._handle_topic_selected)
        self.topic_selection_widget.addItems(self.topic_list) # we add some message type
        self.topic_selection_widget.insertSeparator(len(self.topic_selection_widget))
        self.topic_selection_widget.addItem("New...")

        self.show()

    @property
    def msg(self):
        return self.message_tree.msg

    def _handle_message_selected(self, message_name):
        if message_name != '':
            newRosMessageClassType = roslib.message.get_message_class(message_name)
            self.message_tree.set_message(newRosMessageClassType())

    def _handle_topic_selected(self, topic_name):
        if topic_name == "":
            return

        if topic_name == "New...":
            self.topic_composition_widget.setEnabled(True)
            self.topic_name = ""
            self.msg_name_widget.clear()
            for package in self.package_list:
                self.msg_name_widget.addItems(rosmsg.list_msgs(package))
                self.msg_name_widget.insertSeparator(len(self.msg_name_widget))
            self.msg_name_widget.setEnabled(True)
        else:
            self.topic_composition_widget.setText('')
            self.topic_composition_widget.setEnabled(False)
            self.topic_name = topic_name.encode('ascii', 'ignore')
            self.msg_name = self.timeline.get_datatype(self.topic_name)
            self.msg_name_widget.clear()
            self.msg_name_widget.addItem(self.msg_name)
            self.msg_name_widget.setEnabled(False)
        self.update()


    def _handle_topic_composition(self):
        if self.topic_composition_widget.text() in self.topic_list:
            qWarning("This will not create a new topic but use the already created topic with th same name")
        self.topic_name = self.topic_composition_widget.text().encode('ascii', 'ignore')

    def onImportButtonClicked(self):
        if self.topic_name is None:
            qWarning("No topic selected")
            return
        bag, entry = self.timeline.get_entry(self.timeline._timeline_frame.playhead, self.topic_name)
        msg = bag._read_message(entry.position)
        self.message_tree.set_message(msg[1])

    def onAddButtonClicked(self):
        if self.topic_name == "":
            qErrnoWarning(1,"Topic name is empty")
            return
        self.messageDefined.emit()
        if self.topic_selection_widget.currentText() == "New...":
            self.topic_list = self.timeline._get_topics()
            self.topic_selection_widget.clear()
            self.topic_selection_widget.addItems(self.topic_list)
            self.topic_selection_widget.insertSeparator(len(self.topic_selection_widget))
            self.topic_selection_widget.addItem("New...")
