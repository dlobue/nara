from overwatch import mail_grab
from overwatch import eband, emit_signal

import time


def set_read(muuid):
    """
    Set the Seen flag in the index as well as on the filesystem.
    """
    emit_signal(eband, 'log', 'doing set_read on muuid %s' % muuid)
    msg = mail_grab.get(muuid)
    subdir = msg.get_subdir()
    if subdir == 'new':
        msg.set_subdir('cur')
    if 'S' not in msg.get_flags():
        msg.add_flag('S')
        t = time.time()
        mail_grab.update(muuid, msg)
        t = time.time() - t
        emit_signal(eband, 'log', 'update took %s seconds' % t)
        return (muuid, [('flags', 'S')])
    else:
        mail_grab.update(muuid, msg)
    return None

def set_unread(muuid):
    """
    Remove the seen flag both from the xapian index and from the filesystem.
    """
    emit_signal(eband, 'log', 'doing set_unread on muuid %s' % muuid)
    msg = mail_grab.get(muuid)
    subdir = msg.get_subdir()
    if subdir == 'new':
        msg.set_subdir('cur')
    if 'S' in msg.get_flags():
        msg.remove_flag('S')
        t = time.time()
        mail_grab.update(muuid, msg)
        t = time.time() - t
        emit_signal(eband, 'log', 'update took %s seconds' % t)
        return (muuid, [('flags', 'S')])
    else:
        mail_grab.update(muuid, msg)
    return None

