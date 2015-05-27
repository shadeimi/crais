
import persistent


class ProcessManager(persistent.Persistent):
    def __init__(self):
        self.process_list = {}

    def store(self, pid, port):
        self.process_list[pid] = port

    def delete(self, pid):
        try:
            del(self.process_list[pid])
        except KeyError:
            return False

    def get_process_port(self, pid):
        try:
            return self.process_list[pid]
        except KeyError:
            return False

    def get_process_pid(self, port):
        for key, value in self.process_list.iteritems():
            if value == port:
                return key

    def get_all_process_list(self):
        return self.process_list