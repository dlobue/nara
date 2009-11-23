

def set_read(muuid):
    msg = mailgrab.get(muuid)
    subdir = msg.get_subdir()
    if subdir == 'new':
        msg.set_subdir('cur')
    if 'S' not in msg.get_flags():
        msg.add_flag('S')
        return (muuid, [('flags', 'S')])
    return None

def set_unread(muuid):
    msg = mailgrab.get(muuid)
    subdir = msg.get_subdir()
    if subdir == 'new':
        msg.set_subdir('cur')
    if 'S' in msg.get_flags():
        msg.remove_flag('S')
        return (muuid, [('flags', 'S')])
    return None

