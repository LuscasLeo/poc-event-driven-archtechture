from abc import ABC, abstractmethod
from sqlite3 import adapters
from typing import Any, Dict, Generic, List, Type, TypeVar

from dependency_injector.providers import Factory, DependenciesContainer
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.wiring import Provide, inject


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

    @inject
    def dispatch(self, event: Event) -> None:
        if type(event) in self.event_map:
            for event_handler_class in self.event_map[type(event)]:
                event_handler_instance = event_handler_class()
                event_handler_instance.handle_event(event)


# Domain Level Implementation


class Container(DeclarativeContainer):
    adapters = DependenciesContainer()


class PrintNotificationService(NotificationService):
    def __init__(self) -> None:
        print("Hey, i was just constructed")

    def send_notificaition(self) -> None:
        print("Notification Sent!")


class SendNotificationOnNewMessage(EventHandler[NewMessageEvent]):
    @inject
    def __init__(
        self,
        notification_service: NotificationService = Provide[
            Container.adapters.notification_service
        ],
    ) -> None:
        self.notification_service = notification_service

    def handle_event(self, event: NewMessageEvent) -> None:
        self.notification_service.send_notificaition()


EVENT_HANDLERS: EventMap = {NewMessageEvent: [SendNotificationOnNewMessage]}

@inject
def bootstrap() -> None:
    dispatcher = RuntimeEventDispatcher(EVENT_HANDLERS)

    dispatcher.dispatch(NewMessageEvent())


class ApplicationContainer(DeclarativeContainer):
    notification_service = Factory(PrintNotificationService)


if __name__ == "__main__":
    container = Container(adapters=ApplicationContainer)
    container.init_resources()
    container.wire(modules=[__name__], from_package=__name__)
    bootstrap()
