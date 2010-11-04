import email.iterators

block_start = ('________________________________', '-----Original Message-----')

class msg_machine(object):
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
        #rstrip = unicode.rstrip
        subpart_states = []
        subpart_gen = (line for line in subpart.get_payload(decode=True).splitlines())

        cls.appendee = []
        cls.prev_state = 'MSG'
        tolerance = 0
        empty_tolerance = 0

        def _flush(newstate, theline):
            if cls.appendee:
                while 1:
                    try: endone = cls.appendee.pop()
                    except IndexError:
                        cls.appendee.append(endone)
                        break
                    if endone:
                        cls.appendee.append(endone)
                        break
                #subpart_states.append(tuple([cls.prev_state, u'\n'.join(cls.appendee)]))
                subpart_states.append(tuple([cls.prev_state, '\n'.join(cls.appendee)]))
            cls.appendee = []
            if newstate != 'eof':
                cls.prev_state = newstate
                cls.appendee.append(theline)

        while 1:
            try: line = subpart_gen.next()
            except StopIteration: break

            if line == '':
                if empty_tolerance: continue
                else: empty_tolerance = 1
            elif empty_tolerance: empty_tolerance = 0
            #if line == '': continue
            #line = line.rstrip()

            if line in block_start:
                _flush('BLOCK', line)
                tolerance = 1
            elif line.startswith('From:'):
                if tolerance == 1:
                    tolerance = 0
                    cls.appendee.append(line)
                    continue
                _flush('BLOCK', line)
            elif line.startswith('>'):
                _flush('QUOTE', line)
            elif cls.prev_state == 'QUOTE':
                _flush('MSG', line)
            else:
                cls.appendee.append(line)

        _flush('eof','eof')
        cls.state_results.extend(subpart_states)

    @classmethod
    def _is_dunno(cls, subpart):
        cls.state_results.append(['DUNNO', subpart])

    @classmethod
    def _is_attachment(cls, subpart):
        cls.state_results.append(['ATTACHMENT', subpart])
