"""
A module to arrange mail and news messages into message threads using
their References headers. Implemented from Jamie Zawinski's algorithm
described at: http://www.jwz.org/doc/threading.html.

Input is an iterable collection of mail objects that have get()
methods which return the text of the header named in get()'s first
argument and, if there is no such header, returns get()'s second
argument. A list of Message objects from the email module (or the old
rfc822 module) would work fine.

Output is a list of trees of messageContainer objects. Each of those
objects has a messages attribute that holds a list of messages that
have the same message-id. At the root level that list may be empty,
but below the root level there will always be at least one message.
The messageContainer objects also have the attributes children and
parent. The attribute children is a list of messageContainers that
hold messages that (claim to be) replies to the current
one. Naturally, the list may be empty. The attribute parent is either
None or the messageContainer that has the current one in its list of
children.

The routine does nothing about sorting the message siblings. It's up
to you to sort them in whatever order suits you.

The only thing that's intended to be used from outside the module is
the function jwzThread(). It's also fair game to query the version
number.

"""

# Copyright (c) 2002 Matthew Dixon Cowles <matt@mondoinfo.com>
#
# This program is free software; you may redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA


import re

# Set these depening on how brave and/or curious you are
kModuleDebug=1
kModuleVerbose=1

kVersion="0.5"

kInAngleBracketsRE=re.compile("(<.*?>)") # Not even close to proper parsing
kSubjJunkRE=re.compile("^re[\[\]0-9 ]* *: *") # Could be more sophisticated


def chaseChildrenForID(container,msgID):
  while 1:
    if container.messageID==msgID:
      return 1
    if len(container.children)==0:
      return 0
    for child in container.children:
      result=chaseChildrenForID(child,msgID)
      if result:
        return 1
    return 0


def chaseParentsForID(container,msgID):
  while 1:
    if container.messageID==msgID:
      return 1
    if container.parent==None:
      return 0
    container=container.parent


# Could lose Fw:, Fwd:, etc
def stripSubjJunk(subj):
  while 1:
    subj=subj.lower()
    where=kSubjJunkRE.search(subj)
    if where==None:
      return subj.strip()
    subj=subj[len(where.group(0)):]


class messageContainer:
  def __init__(self):
    self.messages=[]
    self.parent=None
    self.children=[]
    self.messageID=None
    self.subject=None
    self.strippedSubject=None
    return None

  def __repr__(self):
    if self.parent==None:
      parentStr="no"
    else:
      parentStr="yes"

    if self.messageID==None:
      idStr="(none)"
    else:
      idStr=self.messageID

    return "%s, Message-ID: %s parent: %s children: %i messages: %i" % \
      (self.__class__.__name__,idStr,parentStr,len(self.children),len(self.messages))


def tableCount(idTable):
  tot=0
  for container in idTable.values():
    tot+=len(container.messages)
  return tot

def countMessages(rootSet):

  def recurseCountMessages(container):
    tot=len(container.messages)
    for child in container.children:
      tot+=recurseCountMessages(child)
    return tot

  tot=0
  for container in rootSet:
    tot+=recurseCountMessages(container)
  return tot

def countExtraMessages(rootSet):

  def recurseCountExtras(container):
    tot=0
    if len(container.messages)>1:
      tot+=len(container.messages)-1
    for child in container.children:
      tot+=recurseCountExtras(child)
    return tot

  tot=0
  for container in rootSet:
    tot+=recurseCountExtras(container)
  return tot

def countContainers(rootSet):

  def recurseCountContainers(container):
    tot=1
    for child in container.children:
      tot+=recurseCountContainers(child)
    return tot

  tot=0
  for container in rootSet:
    tot+=recurseCountContainers(container)
  return tot

def countContainersWithoutMessages(rootSet):

  def recurseCountNoMessages(container):
    empties=0
    if len(container.messages)==0:
      empties+=1
      for child in container.children:
        empties+=recurseCountNoMessages(child)
    return empties

  tot=0
  for container in rootSet:
    tot+=recurseCountNoMessages(container)
  return tot


def countEmpties(rootSet):

  def recurseCountEmpties(container):
    empties=0
    if len(container.messages)==0 and len(container.children)==0:
      empties+=1
      for child in container.children:
        empties+=recurseCountEmpties(child)
    return empties

  tot=0
  for container in rootSet:
    tot+=recurseCountEmpties(container)
  return tot

def countNoMessagesTopLevel(rootSet):
  empties=0
  for container in rootSet:
    if len(container.messages)==0:
      empties+=1
  return empties

def countTopLevelWithParents(rootSet):
  n=0
  for container in rootSet:
    if container.parent<>None:
      n+=1
  return n

def topLevelSubjectsUnique(rootSet):
  subjects=[]
  for container in rootSet:
    if container.strippedSubject<>"" and container.strippedSubject in subjects:
      return 0
    subjects.append(container.strippedSubject)
  return 1


def recursePrune(container):
  ind=0
  containersRemoved=0
  while ind<len(container.children):
    child=container.children[ind]
    containersRemoved+=recursePrune(child)

    if len(child.messages)==0 and len(child.children)==0:
      container.children.remove(child)
      containersRemoved+=1
    elif len(child.messages)==0 and len(child.children)>0:
      container.children+=child.children
      container.children.remove(child)
      containersRemoved+=1
    else:
      ind+=1
  return containersRemoved


def jwzThread(iterableMailbox):
  if kModuleVerbose:
    print "Building ID table"
  idTable={}
  nMsgs=0
  nContainersAdded=0
  nDupMsgIDs=0
  for msg in iterableMailbox:
    nMsgs+=1
    subjHeader=msg.get("subject","")
    refsHeader=msg.get("references","")
    msgIDHeader=msg.get("message-id","")

    if idTable.has_key(msgIDHeader):
      thisMessageContainer=idTable[msgIDHeader]
      idTable[msgIDHeader].messages.append(msg)
      if len(thisMessageContainer.messages)>1: # If duplicate message-id
        nDupMsgIDs+=1
        continue
    else:
      thisMessageContainer=messageContainer()
      thisMessageContainer.messageID=msgIDHeader
      nContainersAdded+=1
      thisMessageContainer.messages.append(msg)
      idTable[msgIDHeader]=thisMessageContainer

    refs=refsHeader.split() # Naive but may be sufficient

    # Make sure that no reference is repeated. Weird
    # but it can happen.
    ind=0
    while ind<len(refs):
      if refs.count(refs[ind])>1:
        del refs[ind]
      else:
        ind+=1

    irtHeader=msg.get("in-reply-to","")
    ans=kInAngleBracketsRE.search(irtHeader)
    if ans<>None:
      irtID=ans.group(1)
      # I understand that this can happen sometimes
      if irtID not in refs:
        refs.append(irtID)

    for count in range(len(refs)-1):
      thisRef=refs[count]
      if idTable.has_key(thisRef):
        thisContainer=idTable[thisRef]
      else:
        nContainersAdded+=1
        thisContainer=messageContainer()
        thisContainer.messageID=thisRef
        idTable[thisRef]=thisContainer

      nextRef=refs[count+1]
      if idTable.has_key(nextRef):
        nextContainer=idTable[nextRef]
      else:
        nContainersAdded+=1
        nextContainer=messageContainer()
        nextContainer.messageID=nextRef
        idTable[nextRef]=nextContainer

      # First clause a PITA to find need for
      if nextContainer.parent==None and \
        not nextContainer in thisContainer.children and \
        not chaseChildrenForID(nextContainer,thisContainer.messageID) and \
        not chaseParentsForID(thisContainer,nextContainer.messageID):
        thisContainer.children.append(nextContainer)
        nextContainer.parent=thisContainer

    if len(refs)>0:
      lastRef=refs[-1]
      if idTable.has_key(lastRef):
        lastContainer=idTable[lastRef]
      else:
        nContainersAdded+=1
        lastContainer=messageContainer()
        lastContainer.messageID=lastRef
        idTable[lastRef]=lastContainer

      # If we've already got a parent, don't believe it.
      if thisMessageContainer.parent<>None and thisMessageContainer.parent<>lastContainer:
        thisMessageContainer.parent.children.remove(thisMessageContainer)
        thisMessageContainer.parent=None

      if thisMessageContainer.parent==None and \
        not thisMessageContainer in lastContainer.children and \
        not chaseChildrenForID(thisMessageContainer,lastContainer.messageID) and \
        not chaseParentsForID(lastContainer,thisMessageContainer.messageID):
        lastContainer.children.append(thisMessageContainer)
        thisMessageContainer.parent=lastContainer

  if kModuleVerbose:
    print "Done"
    print

    print "%i containers added" % nContainersAdded
    print "%i containers in table" % len(idTable.keys())

    print "%i messages seen" % nMsgs
    print "%i messages in table" % tableCount(idTable)
    print

  if kModuleDebug and kModuleVerbose:
    print "Checking invariants"

  if kModuleDebug:
    assert nContainersAdded==len(idTable.keys())
    assert nMsgs==tableCount(idTable)

  if kModuleDebug and kModuleVerbose:
    print "Done"
    print

  if kModuleVerbose:
    print "Finding root set"

  rootSet=[]
  for container in idTable.values():
    if container.parent==None:
      rootSet.append(container)

  if kModuleVerbose:
    print "Done"
    print

    print "%i duplicate message-ids seen" % nDupMsgIDs
    print "%i extra messages in tree" % countExtraMessages(rootSet)
    print "%i messages in tree" % countMessages(rootSet)
    print "%i containers in tree" % countContainers(rootSet)
    print "%i empty containers in tree" % countEmpties(rootSet)
    print "%i containers at top level" % len(rootSet)
    print "%i containers without messages in tree" % countContainersWithoutMessages(rootSet)
    print "%i containers without messages at top level" % countNoMessagesTopLevel(rootSet)
    print "%i top-level containers with parents" % countTopLevelWithParents(rootSet)
    print

  if kModuleVerbose and kModuleDebug:
    print "Checking invariants"

  if kModuleDebug:
    assert nDupMsgIDs==countExtraMessages(rootSet)
    assert nMsgs==countMessages(rootSet)
    assert nContainersAdded==countContainers(rootSet)
    assert countTopLevelWithParents(rootSet)==0

  if kModuleVerbose and kModuleDebug:
    print "Done"
    print

  if kModuleVerbose:
    print "Pruning empty containers"

  containersRemoved=0
  for container in rootSet:
    containersRemoved+=recursePrune(container)

  ind=0
  while ind<len(rootSet):
    container=rootSet[ind]
    if len(container.messages)==0 and len(container.children)==0:
      del rootSet[ind]
      containersRemoved+=1
    elif len(container.messages)==0 and len(container.children)==1:
      rootSet[ind]=container.children[0]
      rootSet[ind].parent=None
      containersRemoved+=1
      ind+=1
    else:
      ind+=1

  if kModuleVerbose:
    print "Done"
    print

    print "%i containers removed" % containersRemoved
    print "%i messages in tree" % countMessages(rootSet)
    print "%i containers in tree" % countContainers(rootSet)
    print "%i empty containers in tree" % countEmpties(rootSet)
    print "%i containers at top level" % len(rootSet)
    print "%i containers without messages" % countContainersWithoutMessages(rootSet)
    print "%i containers without messages at top level" % countNoMessagesTopLevel(rootSet)
    print "%i top-level containers with parents" % countTopLevelWithParents(rootSet)
    print

  if kModuleVerbose and kModuleDebug:
    print "Checking invariants"

  if kModuleDebug:
    assert nMsgs==countMessages(rootSet)
    assert nContainersAdded-containersRemoved==countContainers(rootSet)
    assert countContainersWithoutMessages(rootSet)==countNoMessagesTopLevel(rootSet)
    assert countTopLevelWithParents(rootSet)==0
    assert countEmpties(rootSet)==0

  if kModuleVerbose and kModuleDebug:
    print "Done"
    print

  if kModuleVerbose:
    print "Building subject table"

  subjectTable={}
  for thisContainer in rootSet:
    if len(thisContainer.messages)>0:
      subjHeader=thisContainer.messages[0].get("subject","")
    else:
      subjHeader=thisContainer.children[0].messages[0].get("subject","")
    strippedSubject=stripSubjJunk(subjHeader)

    thisContainer.subject=subjHeader
    thisContainer.strippedSubject=strippedSubject

    if strippedSubject=="":
      continue

    if not subjectTable.has_key(strippedSubject):
      subjectTable[strippedSubject]=thisContainer
    else:
      containerInTable=subjectTable[strippedSubject]
      if len(containerInTable.messages)>0 and len(thisContainer.messages)==0:
        subjectTable[strippedSubject]=thisContainer
      elif len(containerInTable.subject)<>len(containerInTable.strippedSubject) and \
        len(thisContainer.subject)==len(thisContainer.strippedSubject):
        subjectTable[strippedSubject]=thisContainer

  containersAddedForSubj=0
  containersRemovedForSubj=0
  ind=0
  while ind<len(rootSet):
    thisContainer=rootSet[ind]
    strippedSubject=thisContainer.strippedSubject

    if not subjectTable.has_key(strippedSubject):
      assert strippedSubject==""
      ind+=1
      continue

    containerInTable=subjectTable[strippedSubject]

    if thisContainer==containerInTable:
      ind+=1
      continue

    if len(thisContainer.messages)==0 and len(containerInTable.messages)==0:
      containerInTable.children+=thisContainer.children
      containersRemovedForSubj+=1
      del rootSet[ind]
      continue

    if len(containerInTable.messages)==0:
      assert len(thisContainer.messages)>0
      containerInTable.children.append(thisContainer)
      del rootSet[ind]
      continue

    if len(thisContainer.strippedSubject)<>len(thisContainer.subject) and \
      len(containerInTable.strippedSubject)==len(containerInTable.subject):
      containerInTable.children.append(thisContainer)
      del rootSet[ind]
      continue

    newOne=messageContainer()
    containersAddedForSubj+=1
    newOne.children.append(thisContainer)
    newOne.children.append(containerInTable)
    newOne.strippedSubject=strippedSubject
    del rootSet[ind]
    where=rootSet.index(containerInTable)
    rootSet[where]=newOne
    subjectTable[strippedSubject]=newOne

  if kModuleVerbose:
    print "Done"
    print

    print "%i messages in tree" % countMessages(rootSet)
    print "%i containers added" % containersAddedForSubj
    print "%i containers removed" % containersRemovedForSubj
    print "%i containers in tree" % countContainers(rootSet)
    print "%i empty containers in tree" % countEmpties(rootSet)
    print "%i containers at top level" % len(rootSet)
    print "%i containers without messages in root set" % countContainersWithoutMessages(rootSet)
    print "%i containers without messages at top level" % countNoMessagesTopLevel(rootSet)
    print "%i top-level containers with parents" % countTopLevelWithParents(rootSet)
    print

  if kModuleVerbose and kModuleDebug:
    print "Checking invariants"

  if kModuleDebug:
    assert nMsgs==countMessages(rootSet)
    assert nContainersAdded-containersRemoved+containersAddedForSubj-containersRemovedForSubj==countContainers(rootSet)
    assert countContainersWithoutMessages(rootSet)==countNoMessagesTopLevel(rootSet)
    assert countTopLevelWithParents(rootSet)==0
    assert countEmpties(rootSet)==0
    assert topLevelSubjectsUnique(rootSet)

  if kModuleVerbose and kModuleDebug:
    print "Done"
    print

  return rootSet
