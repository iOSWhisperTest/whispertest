from time import time

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.accessibilityaudit import AccessibilityAudit
from queue import Queue, Empty
from threading import Thread, Event
from whisper_test.common import logger


A11Y_CURRENT_ELEMENT_CHANGED_EVENT = 'hostInspectorCurrentElementChanged:'
EVENT_QUEUE_READ_TIMEOUT = 2


class axServices:

    def __init__(self):
        self.lockdown = create_using_usbmux()

    def event_listener(self, service, event_queue):
        """Thread target for listening to events and putting them into a queue."""
        for event in service.iter_events():
            event_queue.put(event)
        event_queue.put(None)


    def get_ax_settings(self):
        """Get Accessibility settings using iOS Accessibility Audit service."""
        ax_settings = {}
        with AccessibilityAudit(lockdown=self.lockdown) as audit:
            for setting in audit.settings:
                ax_settings[setting.key] = setting.value
        return ax_settings


    def listen_for_ax_events(self, service, events_queue, should_listen_for_events):
        """Listen for events from the service and add them to the events queue."""
        seen_events = False
        while should_listen_for_events.is_set():
            try:
                for event in service.iter_events():
                    events_queue.put(event)
                    seen_events = True
            except Exception as e:
                if not seen_events:
                    logger.error("❌ Error while listening for events: %s", e)
                break

    def start_listener_thread(self, service, events_queue):
        """Start a thread to listen for events."""
        should_listen_for_events = Event()
        should_listen_for_events.set()

        listener_thread = Thread(target=self.listen_for_ax_events, args=(service, events_queue, should_listen_for_events))
        listener_thread.daemon = False
        listener_thread.start()
        return listener_thread, should_listen_for_events

    def get_ax_list_items_old(self, timeout=1, max_items=20):
        """ Return list items available in currently shown menu.
        Based on: https://github.com/doronz88/pymobiledevice3/blob/2b5621e95871817255613170607c89f2a2e17bdb/pymobiledevice3/cli/developer.py#L861
        """
        service = AccessibilityAudit(self.lockdown)
        service.move_focus_next()

        events_queue = Queue()

        listener_thread, should_listen_for_events = self.start_listener_thread(service, events_queue)
        logger.info("🚀 Listener event thread started.")

        seen_captions = set()
        captions = []
        start_time = time()
        # Initialize a list to keep track of all captions
        all_captions = []
        seen_pairs = set()

        try:
            while max_items == -1 or len(seen_captions) < max_items:
                if time() - start_time > timeout:
                    logger.info("⌛️ Timeout for fetching new event from queue reached.")
                    break
                try:
                    event = events_queue.get(timeout=2)
                except Empty:
                    logger.info("🛑 No events in the queue.")
                    continue

                if event.name != A11Y_CURRENT_ELEMENT_CHANGED_EVENT:
                    continue

                # each such event should contain one element that became in focus
                current_item = event.data[0]
                caption = current_item.caption
                logger.info(f"📋 Caption: {caption}")

                if len(caption) > 1 and "Keyboard Key" not in caption:
                    # Add the caption to all_captions list if it's length is more than 1
                    all_captions.append(caption)
                    seen_captions.add(caption)

                    # Check if any two consecutive items repeat anywhere in the list
                    if len(all_captions) > 1:
                        pair = (all_captions[-2], all_captions[-1])
                        if pair in seen_pairs:
                            logger.info(f"🟠 Pair ax captions already seen: {pair}")
                            break
                        seen_pairs.add(pair)

                    captions.append(caption)
                service.move_focus_next()
                # start_time = time()
        finally:
            logger.info("🧹 Cleaning up resources...")
            should_listen_for_events.clear()
            service.close()
            listener_thread.join(timeout=3)
            if listener_thread.is_alive():
                logger.info("🟡 Listener thread is still running.")
            else:
                logger.info("⚪️ Listener thread has stopped.")
                print("⚪️ Listener thread has stopped.")
            while not events_queue.empty():
                logger.info("🚮 Clearing the events queue.")
                events_queue.get(timeout=1)

        # Remove the last caption if it is repetitive
        if len(captions) > 1 and captions[0] == captions[-1]:
            captions.pop()

        return captions

    def get_ax_list_items(self, timeout=1, max_items=20):
        """ Return interface element captions and types using AccessibilityAudit.
        Based on: https://github.com/doronz88/pymobiledevice3/blob/2a0670079a398dffab6f2b1c15dfa0a55a9ed271/pymobiledevice3/services/accessibilityaudit.py#L421
        """
        service = AccessibilityAudit(self.lockdown)
        service.move_focus_next()

        events_queue = Queue()

        listener_thread, should_listen_for_events = self.start_listener_thread(service, events_queue)
        logger.info("🚀 Listener event thread started.")

        captions = []
        seen_element_ids = set()  # keep track of seen elements to avoid loops
        n_elements = 0
        start_time = time()
        try:
            while max_items == -1 or n_elements < max_items:
                # check if we have reached the timeout
                if time() - start_time > timeout:
                    logger.info("⌛️ a11y timeout.")
                    break
                # try to get an event from the queue
                try:
                    event = events_queue.get(timeout=EVENT_QUEUE_READ_TIMEOUT)
                except Empty:
                    logger.info("🛑 No events in the queue.")
                    continue

                if event.name != A11Y_CURRENT_ELEMENT_CHANGED_EVENT:
                    continue

                # event contains the focused element
                current_item = event.data[0]
                current_identifier = current_item.platform_identifier

                # check if we have seen this element before
                if current_identifier in seen_element_ids:
                    break  # loop detected

                seen_element_ids.add(current_identifier)
                n_elements += 1
                caption = current_item.caption
                spoken_description = current_item.spoken_description
                if caption != spoken_description:
                    logger.info(f"🟠 Caption and spoken_description are different: {caption}, {spoken_description}")
                logger.info(f"📋 Caption {n_elements}: {caption}")
                captions.append(caption)
                service.move_focus_next()
        finally:
            logger.info("🧹 Cleaning up resources...")
            should_listen_for_events.clear()
            service.close()
            listener_thread.join(timeout=3)
            if listener_thread.is_alive():
                logger.info("🟡 Listener thread is still running.")
            else:
                logger.info("⚪️ Listener thread has stopped.")
                print("⚪️ Listener thread has stopped.")
            while not events_queue.empty():
                try:
                    logger.info("🚮 Clearing the events queue.")
                    events_queue.get_nowait()
                except Empty:
                    logger.info("🛑 No more events to clear from the queue.")
                    break

        return captions
