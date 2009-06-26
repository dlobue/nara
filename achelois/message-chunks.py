
message_seperators = ('________________________________', '-----Original Message-----')

def chunkify(rawmail):
    ostandin = rawmail.replace(message_seperators[0], '%mesg-sep').replace(message_seperators[1], '%mesg-sep').replace('\n \n', '%sdnewline').replace('\n\n', '%newline').replace('%newline', '\n').replace('%sdnewline', '').replace('\n\nFrom: ', '\n%mesg-sep\nFrom: ').split('%mesg-sep')
    return ostandin


def set_state(line):
    if line in message_seperators:
        state_function = block
    elif line.startswith('From:'):
        state_function = reply
    elif line.startswith('>'):
        state_function = reply


for line in message:
    set_state(line)
    state_function(line)
