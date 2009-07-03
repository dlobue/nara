import email.iterators

'''
def chunkify(rawmail):
    ostandin = rawmail.replace(message_seperators[0], '%mesg-sep').replace(message_seperators[1], '%mesg-sep').replace('\n \n', '%sdnewline').replace('\n\n', '%newline').replace('%newline', '\n').replace('%sdnewline', '').replace('\n\nFrom: ', '\n%mesg-sep\nFrom: ').split('%mesg-sep')
    return ostandin
    '''

class msg_machine(object):

    block_start = ('________________________________', '-----Original Message-----')

    @classmethod
    def process(cls, message):
        cls.state_results = []
        for subpart in email.iterators.typed_subpart_iterator(message):
            if 'filename' in subpart.get('Content-Disposition',''):
                cls._is_attachment(subpart)
                continue
            if subpart.get_content_maintype() == 'text':
                subtype = subpart.get_content_subtype() 
                if subtype == 'html': cls._is_html(subpart)
                elif subtype == 'plain': cls._is_plaintxt(subpart)
                else: cls._is_dunno(subpart)
            else: cls._is_dunno(subpart)

        return cls.state_results

    @classmethod
    def _is_html(cls, subpart):
        cls.state_results.append(['HTML', subpart])

    @classmethod
    def _is_plaintxt(cls, subpart):
        subpart_states = []
        subpart_gen = (line for line in subpart.get_payload().splitlines())

        cls.appendee = []
        cls.prev_state = 'MSG'
        tolerance = 0

        def _flush():
            if cls.appendee:
                subpart_states.append(tuple([cls.prev_state, u'\n'.join(cls.appendee)]))
            cls.appendee = []

        while 1:
            try: line = subpart_gen.next()
            except StopIteration: break
            else:
                if line == '': pass
            #if not line: break
            if line in cls.block_start:
                _flush()
                cls.prev_state = 'BLOCK'
                tolerance = 1
                cls.appendee.append(line)
            elif line.startswith('>'):
                _flush()
                cls.prev_state = 'QUOTE'
                cls.appendee.append(line)
            elif line.startswith('From:'):
                if tolerance == 1:
                    tolerance = 0
                    cls.appendee.append(line)
                    continue
                _flush()
                cls.prev_state = 'BLOCK'
                cls.appendee.append(line)
            else:
                cls.appendee.append(line)

        _flush()

        #cls.state_results.append(tuple(['PLAINTXT', subpart_states]))
        cls.state_results.extend(subpart_states)

    @classmethod
    def _is_dunno(cls, subpart):
        cls.state_results.append(['DUNNO', subpart])

    @classmethod
    def _is_attachment(cls, subpart):
        cls.state_results.append(['ATTACHMENT', subpart])
