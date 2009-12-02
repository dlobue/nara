from overwatch import mail_grab
from overwatch import eband, emit_signal

import time


def set_read(muuid):
    emit_signal(eband, 'log', 'doing set_read on muuid %s' % muuid)
    msg = mail_grab.get(muuid)
    #emit_signal(eband, 'log', 'msg type is %s' % str(type(msg)))
    #emit_signal(eband, 'log', 'msg has these attributes:\n%s' % '\n'.join(dir(msg)))
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
    emit_signal(eband, 'log', 'doing set_unread on muuid %s' % muuid)
    msg = mail_grab.get(muuid)
    #emit_signal(eband, 'log', 'msg type is %s' % str(type(msg)))
    #emit_signal(eband, 'log', 'msg has these attributes:\n%s' % '\n'.join(dir(msg)))
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

