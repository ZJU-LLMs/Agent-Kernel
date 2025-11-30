"""Message dispatcher actor that filters and routes agent communications."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, List, Optional, Set, Tuple

from ....toolkit.logger import get_logger
from ....types.configs.system import MessagerConfig
from ....types.schemas.message import Message, MessageKind
from .base import SystemComponent

if TYPE_CHECKING:
    from ...controller import BaseController


logger = get_logger(__name__)

__all__ = ["Messager"]


class Messager(SystemComponent):
    """Filter incoming messages and deliver them to the appropriate agents."""

    COMPONENT_NAME = "messager"

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize the message dispatcher with the provided configuration.

        Args:
            **kwargs (object): Fields used to construct a `MessagerConfig`.
        """
        self.config = MessagerConfig(**kwargs)

        self.message_queue: asyncio.Queue[Message] = asyncio.Queue()

        self.blocked_senders: Set[str] = set(self.config.blocked_senders or [])
        self.blocked_receivers: Set[str] = set(self.config.blocked_receivers or [])

        pairs: List[Tuple[str, str]] = []
        for entry in self.config.blocked_pairs or []:
            if isinstance(entry, tuple) and len(entry) == 2:
                pairs.append((entry[0], entry[1]))
            elif isinstance(entry, dict) and "from" in entry and "to" in entry:
                pairs.append((entry["from"], entry["to"]))
        self.blocked_pairs: Set[Tuple[str, str]] = set(pairs)

        self.allow_kinds: Set[str] = set(self.config.allow_kinds or [])
        self.allow_self_messages: bool = self.config.allow_self_messages
        self.block_empty_content: bool = self.config.block_empty_content
        self.max_content_length: Optional[int] = self.config.max_content_length
        self.blocked_keywords: List[str] = [keyword.lower() for keyword in self.config.blocked_keywords]
        self.blocked_regex_compiled = [re.compile(pattern, re.IGNORECASE) for pattern in self.config.blocked_regex]

        logger.info("Messager initialized")

    async def post_init(self, controller: "BaseController") -> None:
        """
        Inject the controller handle after construction.

        Args:
            controller ("BaseController"): Controller used to deliver inter-agent messages.
        """
        self._controller = controller

    async def send_message(self, message: Message) -> None:
        """
        Enqueue a message for later dispatch.

        Args:
            message (Message): Message instance to queue.
        """
        await self.message_queue.put(message)

    async def _intercept_message(self, message: Message) -> Optional[Message]:
        """
        Apply configured filters to a message before dispatching it.

        Args:
            message (Message): Candidate message to inspect.

        Returns:
            Optional[Message]: Message when permitted; None when blocked.
        """
        if (
            self.allow_kinds
            and str(message.kind) not in self.allow_kinds
            and message.kind.value not in self.allow_kinds
        ):
            logger.debug("Intercepted message: kind '%s' not allowed", message.kind)
            return None

        if message.from_id in self.blocked_senders:
            logger.debug("Intercepted message: sender '%s' blocked", message.from_id)
            return None

        to_ids = message.to_id if isinstance(message.to_id, list) else [message.to_id]
        if any(recipient in self.blocked_receivers for recipient in to_ids):
            logger.debug("Intercepted message: receiver in blocked list %s", to_ids)
            return None

        if isinstance(message.to_id, list):
            if any((message.from_id, recipient) in self.blocked_pairs for recipient in message.to_id):
                logger.debug("Intercepted message: blocked sender/receiver pair in list.")
                return None
        elif (message.from_id, message.to_id) in self.blocked_pairs:
            logger.debug("Intercepted message: blocked sender/receiver pair.")
            return None

        if not self.allow_self_messages and message.from_id in to_ids:
            logger.debug("Intercepted message: self-messages disabled.")
            return None

        content = message.content
        if isinstance(content, str):
            if self.block_empty_content and not content.strip():
                logger.debug("Intercepted message: empty content.")
                return None
            if self.max_content_length is not None and len(content) > self.max_content_length:
                logger.debug("Intercepted message: content exceeds maximum length.")
                return None
            lowered = content.lower()
            if any(keyword in lowered for keyword in self.blocked_keywords):
                logger.debug("Intercepted message: blocked keyword detected.")
                return None
            if any(pattern.search(content) for pattern in self.blocked_regex_compiled):
                logger.debug("Intercepted message: blocked regex match.")
                return None
        elif self.block_empty_content and content is None:
            logger.debug("Intercepted message: None content not allowed.")
            return None

        return message

    async def dispatch_messages(self) -> None:
        """Dequeue messages and deliver them to their intended recipients."""
        queue_size = self.message_queue.qsize()
        if queue_size > 0:
            logger.info("Messager: dispatching %s queued messages.", queue_size)

        while not self.message_queue.empty():
            message = await self.message_queue.get()
            logger.debug("Processing message from %s to %s", message.from_id, message.to_id)

            try:
                message = await self._intercept_message(message)
            except Exception as exc:
                logger.warning("Message intercept error: %s", exc, exc_info=True)
                message = None

            if message is None:
                self.message_queue.task_done()
                continue

            if message.kind in (MessageKind.FROM_AGENT_TO_AGENT, MessageKind.FROM_USER_TO_AGENT):
                recipients = message.to_id if isinstance(message.to_id, list) else [message.to_id]
                if message.kind == MessageKind.FROM_AGENT_TO_AGENT:
                    recipients = list({*recipients, message.from_id})

                if not self._controller:
                    logger.error("Pod manager handle not available; dropping message.")
                else:
                    delivery_tasks = [self._controller.deliver_message(recipient, message) for recipient in recipients]
                    if delivery_tasks:
                        await asyncio.gather(*delivery_tasks)

            self.message_queue.task_done()

    def get_queue_size(self) -> int:
        """
        Return the current number of enqueued messages.

        Returns:
            int: Queue size.
        """
        return self.message_queue.qsize()

    async def close(self) -> None:
        """Drain the queue to release pending producers."""
        while not self.message_queue.empty():
            self.message_queue.get_nowait()
            self.message_queue.task_done()
