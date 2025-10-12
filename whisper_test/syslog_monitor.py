from threading import Thread
from queue import Queue
from threading import Thread, Event
from ssl import SSLError
from pymobiledevice3.services.syslog import SyslogService


DEFAULT_QUEUE_READ_TIMEOUT = 3


class SyslogMonitor:

    def __init__(self, lockdown, syslog_search_strings=None):
        self.lockdown = lockdown
        self.syslog_search_strings = syslog_search_strings
        self.stop_event = Event()
        self.thread, self.queue = self.start()

    def start(self):
        """Start syslog monitoring."""
        self.queue = Queue()
        self.thread = Thread(
            target=self.old_sys_log,
            kwargs={
                # 'service_provider': lockdown, # new
                'lockdown': self.lockdown, # old
                # 'out': None, # new
                'pid': -1,
                'process_name': None,
                'match': self.syslog_search_strings,
                # 'match_insensitive': (), # new
                'include_label': False,
                # 'insensitive_regex': (), # new
                'queue_': self.queue,
                'stop_event': self.stop_event
            }
        )
        self.thread.daemon = True
        self.thread.start()
        print("Syslog monitoring started. Thread alive:", self.thread.is_alive())
        return self.thread, self.queue

    def stop(self):
        if self.thread is not None and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(DEFAULT_QUEUE_READ_TIMEOUT)
            print("Syslog monitoring stopped.")


    # based on pymobiledevice3
    def old_sys_log(self, lockdown, pid=-1, process_name=None, include_label=False, match=(), queue_=None, stop_event=None, max_retries=3):

        retries = 0
        while retries < max_retries:
            try:
                for line in SyslogService(service_provider=lockdown).watch():

                    if stop_event and stop_event.is_set():
                        break

                    skip = False

                    if match is not None:
                        skip = True
                        for m in match:
                            if m in line:
                                skip = False
                                break

                    if skip:
                        continue

                    if queue_:
                        queue_.put(line)
                    else:
                        print('syslog_live: ', line, flush=True)
                break  # Exit the loop if successful
            except (ConnectionAbortedError, OSError, SSLError, Exception) as e:  # Add other exceptions as needed
                print(f"Error occurred: {e}. Retrying {retries + 1} / {max_retries}...")
                retries += 1
        else:
            print("Max retries reached. Could not reconnect.")
