from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Type, TypeVar

from kink import di, inject


# System/Architechture Level interfaces
class Event:
    pass


T = TypeVar("T")


class EventHandler(ABC, Generic[T]):
    @abstractmethod
    def handle_event(self, event: T) -> None:
        raise NotImplementedError()


class EventDispatcher(ABC):
    @abstractmethod
    def dispatch(self, event: Event) -> None:
        raise NotImplementedError()


# Domain Level Interface


class NewMessageEvent(Event):
    pass


class NotificationService(ABC):
    @abstractmethod
    def send_notificaition(self) -> None:
        raise NotImplementedError()


# System Level Implementation

EventMap = Dict[Type[Event], List[Type[EventHandler[Any]]]]


class RuntimeEventDispatcher(EventDispatcher):
    def __init__(self, event_map: EventMap) -> None:
        self.event_map = event_map

    def dispatch(self, event: Event) -> None:
        if type(event) in self.event_map:
            for event_handler_class in self.event_map[type(event)]:
                # Well... If i get it right, event_handler_class should return the SendNotificationOnNewMessage class/type 🤔
                # But, wait! the class has a dependency on its constructor! notification_service: NotificationService
                # I'm constructing a instance this type without putting any parameters. This must raise a exception, right?
                # Right, but not! The class SendNotificationOnNewMessage is decorated with kink's inject decorator. This decorator stores predefined and corresponding types from dependencies, as you can see in the line 83
                event_handler_instance = event_handler_class()
                event_handler_instance.handle_event(event)


# Domain Level Implementation


class PrintNotificationService(NotificationService):
    def __init__(self) -> None:
        print("Hey, i was just constructed")

    def send_notificaition(self) -> None:
        print("Notification Sent!")


# How will the event handler dispatcher know that the SendNotificationOnNewMessage class has a dependency of type NotificationService? 🤔
@inject(use_factory=True)  # This the 1st part of the answer! 💡 Now you should look the line 51
class SendNotificationOnNewMessage(EventHandler[NewMessageEvent]):
    def __init__(self, notification_service: NotificationService) -> None:
        self.notification_service = notification_service

    def handle_event(self, event: NewMessageEvent) -> None:
        self.notification_service.send_notificaition()


EVENT_HANDLERS: EventMap = {NewMessageEvent: [SendNotificationOnNewMessage]}


def bootstrap() -> None:

    # This is the 3rd part of the answer 💡
    # With kink's dependency injection management, i'm linkind the type NotificationService to it's implementation PrintNotificationService
    # It means that whenever i instance a class with a argument of type NotificationService, kirk will detect it and create a new instance of PrintNotificationService automatically
    di[NotificationService] = lambda di: PrintNotificationService()

    event_dispatcher = RuntimeEventDispatcher(EVENT_HANDLERS)


    while True:
        input()
        event_dispatcher.dispatch(NewMessageEvent())


bootstrap()
