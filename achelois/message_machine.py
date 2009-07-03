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

    def _is_html(self, subpart):
        self.state_results.append(['HTML', subpart])

    def _is_plaintxt(self, subpart):
        subpart_states = []
        subpart_gen = (line for line in subpart.get_payload().splitlines())

        self.appendee = []
        self.prev_state = 'MSG'
        tolerance = 0

        def _flush():
            if self.appendee:
                subpart_states.append(tuple([self.prev_state, u'\n'.join(self.appendee)]))
            self.appendee = []

        while 1:
            try: line = subpart_gen.next()
            except StopIteration: break
            else:
                if line == '': pass
            #if not line: break
            if line in self.block_start:
                _flush()
                self.prev_state = 'BLOCK'
                tolerance = 1
                self.appendee.append(line)
            elif line.startswith('>'):
                _flush()
                self.prev_state = 'QUOTE'
                self.appendee.append(line)
            elif line.startswith('From:'):
                if tolerance == 1:
                    tolerance = 0
                    self.appendee.append(line)
                    continue
                _flush()
                self.prev_state = 'BLOCK'
                self.appendee.append(line)
            else:
                self.appendee.append(line)

        _flush()

        #self.state_results.append(tuple(['PLAINTXT', subpart_states]))
        self.state_results.extend(subpart_states)

    def _is_dunno(self, subpart):
        self.state_results.append(['DUNNO', subpart])

    def _is_attachment(self, subpart):
        self.state_results.append(['ATTACHMENT', subpart])
