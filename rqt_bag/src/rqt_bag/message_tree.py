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
"""
Defines a raw view: a TopicMessageView that displays the message contents in a tree.
"""
import rospy
import codecs
import math

import genmsg
import rospkg
import rosmsg
import roslib

import os.path

from python_qt_binding.QtCore import Qt
from python_qt_binding.QtGui import QApplication, QAbstractItemView, QSizePolicy, QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton

class MessageTree(QTreeWidget):
    def __init__(self, parent):
        super(MessageTree, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setColumnCount(2)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self._expanded_paths = None
        self.keyPressEvent = self.on_key_press
        self._rosObject = None

        self.itemExpanded.connect(lambda: self.resizeColumnToContents(0))
        self.itemCollapsed.connect(lambda: self.resizeColumnToContents(0))

    @property
    def msg(self):
        return self._rosObject

    def refresh(self):
        rosObject = self._rosObject
        self.set_message(rosObject)

    def set_message(self, msg_obj):
        """
        Clears the tree view and displays the new message
        :param msg: message object to display in the treeview, ''msg''
        """
        # Remember whether items were expanded or not before deleting
        if self._rosObject:
            for item in self.get_all_items():
                path = self.get_item_path(item)
                if item.isExpanded():
                    self._expanded_paths.add(path)
                elif path in self._expanded_paths:
                    self._expanded_paths.remove(path)
            self.clear()
            self._rosObject = None

        if msg_obj:
            self._rosObject = msg_obj
            # Populate the tree
            self._add_msg_object(None, '', '', msg_obj, msg_obj._type)

            if self._expanded_paths is None:
                self._expanded_paths = set()
            else:
                # Expand those that were previously expanded, and collapse any paths that we've seen for the first time
                for item in self.get_all_items():
                    path = self.get_item_path(item)
                    if path in self._expanded_paths:
                        item.setExpanded(True)
                    else:
                        item.setExpanded(False)
        self.resizeColumnToContents(0)
        self.update()

    # Keyboard handler
    def on_key_press(self, event):
        key, ctrl = event.key(), event.modifiers() & Qt.ControlModifier
        if ctrl:
            if key == ord('C') or key == ord('c'):
                # Ctrl-C: copy text from selected items to clipboard
                self._copy_text_to_clipboard()
                event.accept()
            elif key == ord('A') or key == ord('a'):
                # Ctrl-A: select all
                self._select_all()

    def _select_all(self):
        for i in self.get_all_items():
            if not i.isSelected():
                i.setSelected(True)
                i.setExpanded(True)

    def _copy_text_to_clipboard(self):
        # Get tab indented text for all selected items
        def get_distance(item, ancestor, distance=0):
            parent = item.parent()
            if parent == None:
                return distance
            else:
                return get_distance(parent, ancestor, distance + 1)
        text = ''
        for i in self.get_all_items():
            if i in self.selectedItems():
                text += ('\t' * (get_distance(i, None))) + i.text(0) + '\n'
        # Copy the text to the clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def get_item_path(self, item):
        return item.data(0, Qt.UserRole)[0].replace(' ', '')  # remove spaces that may get introduced in indexing, e.g. [  3] is [3]

    def get_all_items(self):
        items = []
        try:
            root = self.invisibleRootItem()
            self.traverse(root, items.append)
        except Exception:
            # TODO: very large messages can cause a stack overflow due to recursion
            pass
        return items

    def traverse(self, root, function):
        for i in range(root.childCount()):
            child = root.child(i)
            function(child)
            self.traverse(child, function)

    def _add_msg_object(self, parent, path, name, obj, obj_type):
        value = None

        if hasattr(obj, '__slots__'):
            subobjs = [(slot, getattr(obj, slot)) for slot in obj.__slots__]
        elif type(obj) in [list, tuple]:
            len_obj = len(obj)
            if len_obj == 0:
                subobjs = []
            else:
                w = int(math.ceil(math.log10(len_obj)))
                subobjs = [('[%*d]' % (w, i), subobj) for (i, subobj) in enumerate(obj)]
        else:
            subobjs = []

        if type(obj) in [int, long, float]:
            if type(obj) == float:
                value = '%.6f' % obj
            else:
                value = str(obj)

        elif type(obj) in [str, bool, int, long, float, complex, rospy.Time]:
            # Ignore any binary data
            value = codecs.utf_8_decode(str(obj), 'ignore')[0]

        item = QTreeWidgetItem([name, ''])
        if name == '':
            pass
        elif path.find('.') == -1 and path.find('[') == -1:
            self.addTopLevelItem(item)
        else:
            parent.addChild(item)
        item.setData(0, Qt.UserRole, (path, obj_type))

        if value is not None:
            inputWidget = QLineEdit(self)
            inputWidget.setText(value)
            inputWidget.textChanged[str].connect(lambda x: self.onChanged(item, type(obj), x))
            self.setItemWidget(item, 1, inputWidget)

        elif type(obj) in [list, tuple]:
            inputWidget = QPushButton(self)
            inputWidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            inputWidget.setText("Add element")
            inputWidget.clicked.connect(lambda: self.elementAdditionRequired(item, parent, path, name, obj, obj_type))
            self.setItemWidget(item, 1, inputWidget)


        for subobj_name, subobj in subobjs:
            if subobj is None:
                continue

            if path == '':
                subpath = subobj_name  # root field
            elif subobj_name.startswith('['):
                subpath = '%s%s' % (path, subobj_name)  # list, dict, or tuple
            else:
                subpath = '%s.%s' % (path, subobj_name)  # attribute (prefix with '.')

            if hasattr(subobj, '_type'):
                subobj_type = subobj._type
            else:
                subobj_type = type(subobj).__name__

            self._add_msg_object(item, subpath, subobj_name, subobj, subobj_type)

    def walkThrough(self, path):
        splittedpath = path.split('.')
        finalstep = splittedpath.pop()
        step = self._rosObject
        for subpath in splittedpath:
            subsubpath=subpath.split("[")
            if len(subsubpath) == 1:
                step = getattr(step, subpath)
            else:
                step = getattr(step, subsubpath[0])
                index = int(subsubpath[-1].split("]")[0])
                step = step.__getitem__(index)
        return (step, finalstep)

    def onChanged(self, obj, objtype, newvalue):
        path = obj.data(0, Qt.UserRole)[0]
        (step, finalstep) = self.walkThrough(path)

        subfinalstep = finalstep.split("[")
        if len(subfinalstep) == 1:
            setattr(step, finalstep, objtype(newvalue))
        else:
            array = list(getattr(step, subfinalstep[0]))
            index = int(subfinalstep[-1].split("]")[0])
            array.pop(index)
            array.insert(index, objtype(newvalue))
            setattr(step, subfinalstep[0], tuple(array))

    def elementAdditionRequired(self, item, parent, path, name, obj, obj_type):
        if parent is None:
            # This item is a top level item
            myParentType = self._rosObject._type
        else:
            myParentType = parent.data(0, Qt.UserRole)[1]

        if len(myParentType.split('/'))==1:
            #TODO: handle the case where the parent of the list is not a ROS message...
            pass

        else:
            rospack = rospkg.RosPack()
            search_path = {}
            p = myParentType.split('/')[0]
            search_path[p] = [os.path.join(rospack.get_path(p), 'msg')]

            context = genmsg.MsgContext.create_default()
            try:
                spec = genmsg.load_msg_by_type(context, myParentType, search_path)
            except Exception as e:
                raise Exception("Unable to load msg [%s]: %s"%(myParentType, e))
            else:
                parent_fields = spec.fields()

            for field in parent_fields:
                if field[1] != name:
                    pass
                else:
                    myType = field[0].split('[')[0]

            if len(myType.split('/'))==1:
                if myType == "string":
                    myType = "str"
                if "float" in myType:
                    myType = "float"
                if "int" in myType:
                    myType = "int"
                creator = __builtins__[myType]
            else:
                creator = roslib.message.get_message_class(myType)

            (step, finalstep) = self.walkThrough(path)
            step = getattr(step, finalstep)
            step.append(creator())
            self.refresh()
