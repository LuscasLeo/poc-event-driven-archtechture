from abc import ABC, abstractmethod
from datetime import datetime
import json
from typing import Any, Dict, Generic, List, Type, TypeVar

from kink import di, inject
from pika import BlockingConnection, ConnectionParameters, BasicProperties


# System/Architechture Level interfaces
class Event(ABC):
    @abstractmethod
    def serialize(self) -> bytes:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_type() -> str:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def deserialize(b: bytes) -> "Event":
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_revision() -> datetime:
        raise NotImplementedError()


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
    def __init__(self, message: str) -> None:
        self.message = message

    def serialize(self) -> bytes:
        return json.dumps({"message": self.message}).encode()

    @staticmethod
    def deserialize(_b: bytes) -> "Event":
        d = json.loads(_b.decode())
        return NewMessageEvent(d["message"])

    @staticmethod
    def get_type() -> str:
        return "some-proj/some-domain/some-event"

    @staticmethod
    def get_revision() -> datetime:
        return datetime(2022, 10, 26, 2, 49)


class NotificationService(ABC):
    @abstractmethod
    def send_notificaition(self) -> None:
        raise NotImplementedError()


# System Level Implementation

EventHandlerMap = Dict[Type[Event], List[Type[EventHandler[Any]]]]
EventTypeMap = Dict[str, Type[Event]]


class RuntimeEventDispatcher(EventDispatcher):
    def __init__(self, event_map: EventHandlerMap) -> None:
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


class EventListener:
    def __init__(
        self, event_map: EventHandlerMap, event_type_map: EventTypeMap
    ) -> None:
        self.event_map = event_map
        self.event_type_map = event_type_map

    def deserialize_event(self, type: str, b: bytes) -> Event:
        event_type = self.event_type_map.get(type)

        assert event_type is not None

        event_instance = event_type.deserialize(b)

        return event_instance

    def handle(self, event: Event) -> None:
        if type(event) in self.event_map:
            for event_handler_class in self.event_map[type(event)]:
                # Well... If i get it right, event_handler_class should return the SendNotificationOnNewMessage class/type 🤔
                # But, wait! the class has a dependency on its constructor! notification_service: NotificationService
                # I'm constructing a instance this type without putting any parameters. This must raise a exception, right?
                # Right, but not! The class SendNotificationOnNewMessage is decorated with kink's inject decorator. This decorator stores predefined and corresponding types from dependencies, as you can see in the line 83
                event_handler_instance = event_handler_class()
                event_handler_instance.handle_event(event)


class RabbitMQEvenDispatcher(EventDispatcher):
    def __init__(self, connection: BlockingConnection) -> None:
        self.connection = connection

    def dispatch(self, event: Event) -> None:
        serialized_event = event.serialize()

        self.connection.channel().basic_publish(
            exchange="",
            routing_key="test",
            properties=BasicProperties(
                headers={
                    "type": event.get_type(),
                    "revision": event.get_revision().isoformat()
                },
            ),
            body=serialized_event.decode(),
        )


# Domain Level Implementation


class PrintNotificationService(NotificationService):
    def __init__(self) -> None:
        print("Hey, i was just constructed")

    def send_notificaition(self) -> None:
        print("Notification Sent!")


# How will the event handler dispatcher know that the SendNotificationOnNewMessage class has a dependency of type NotificationService? 🤔
@inject()  # This the 1st part of the answer! 💡 Now you should look the line 51
class SendNotificationOnNewMessage(EventHandler[NewMessageEvent]):
    def __init__(self, notification_service: NotificationService) -> None:
        self.notification_service = notification_service

    def handle_event(self, event: NewMessageEvent) -> None:
        self.notification_service.send_notificaition()


EVENT_HANDLERS: EventHandlerMap = {NewMessageEvent: [SendNotificationOnNewMessage]}
EVENT_TYPES_MAP: EventTypeMap = {k.get_type(): k for k in EVENT_HANDLERS.keys()}


def bootstrap() -> None:

    # This is the 3rd part of the answer 💡
    # With kink's dependency injection management, i'm linkind the type NotificationService to it's implementation PrintNotificationService
    # It means that whenever i instance a class with a argument of type NotificationService, kirk will detect it and create a new instance of PrintNotificationService automatically
    di[NotificationService] = lambda di: PrintNotificationService()

    rmq_con = BlockingConnection(ConnectionParameters("localhost", 5672))

    event_dispatcher = RabbitMQEvenDispatcher(connection=rmq_con)

    while True:
        input()
        event_dispatcher.dispatch(NewMessageEvent(message="Hello World!"))


bootstrap()
