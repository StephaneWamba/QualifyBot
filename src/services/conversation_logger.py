"""Service for logging conversations to files with intelligent summaries."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.logging import get_logger
from src.services.llm_service import llm_service

logger = get_logger(__name__)

CONVERSATIONS_DIR = Path("conversations")


class ConversationLogger:
    """Service for logging conversation transcripts to files."""

    def __init__(self, base_dir: Path = CONVERSATIONS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_conversation_dir(self, call_sid: str) -> Path:
        """Get directory for a specific conversation."""
        conv_dir = self.base_dir / call_sid
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def log_conversation(
        self,
        call_sid: str,
        messages: list[Any],
        qualification_data: dict,
        metadata: dict | None = None,
    ) -> dict[str, str]:
        """
        Log conversation to files - merges with existing conversation to preserve all messages.

        Args:
            call_sid: Call SID
            messages: List of conversation messages (should be full conversation history)
            qualification_data: Extracted qualification data
            metadata: Additional metadata

        Returns:
            Dictionary with file paths
        """
        try:
            conv_dir = self._get_conversation_dir(call_sid)
            timestamp = datetime.utcnow().isoformat()
            transcript_file = conv_dir / "transcript.json"

            # Load existing messages if file exists
            existing_messages = []
            existing_qualification_data = {}
            if transcript_file.exists():
                try:
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        existing_messages = existing_data.get("messages", [])
                        existing_qualification_data = existing_data.get(
                            "qualification_data", {})
                        logger.info("Loaded existing conversation", call_sid=call_sid,
                                    existing_message_count=len(existing_messages))
                except Exception as e:
                    logger.warning("Failed to load existing transcript",
                                   call_sid=call_sid, error=str(e))

            # Extract new message content properly
            new_formatted_messages = []
            seen_contents = set()  # Track seen messages to avoid duplicates

            # Add existing messages to seen set
            for existing_msg in existing_messages:
                content = existing_msg.get("content", "")
                if content:
                    seen_contents.add(content)

            # Process new messages and add only if not seen
            for msg in messages:
                # Determine message type - check for HumanMessage first
                if isinstance(msg, dict):
                    msg_type = msg.get("type", "unknown")
                    content = msg.get("content", "")
                else:
                    # Check if it's a HumanMessage or AIMessage
                    msg_class_str = str(type(msg))
                    if "HumanMessage" in msg_class_str:
                        msg_type = "human"
                    elif "AIMessage" in msg_class_str:
                        msg_type = "ai"
                    else:
                        msg_type = "unknown"
                    content = getattr(msg, "content", str(msg))

                if content and content not in seen_contents:  # Only add new messages
                    new_formatted_messages.append({
                        "type": msg_type,
                        "content": content,
                    })
                    seen_contents.add(content)
                    logger.debug("Added new message to log", call_sid=call_sid,
                                 msg_type=msg_type, content_preview=content[:50])

            # Merge messages: existing + new
            all_messages = existing_messages + new_formatted_messages

            # Merge ticket/qualification data (new values override old)
            merged_qualification_data = {
                **existing_qualification_data, **qualification_data}

            # Merge metadata
            existing_metadata = {}
            if transcript_file.exists():
                try:
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        existing_metadata = existing_data.get("metadata", {})
                except Exception:
                    pass

            merged_metadata = {**existing_metadata, **(metadata or {})}
            merged_metadata["last_updated"] = timestamp

            transcript_data = {
                "call_sid": call_sid,
                "timestamp": timestamp,
                "messages": all_messages,
                "qualification_data": merged_qualification_data,
                "metadata": merged_metadata,
            }

            # Write merged conversation
            with open(transcript_file, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)

            # Regenerate summary with all messages
            summary_file = conv_dir / "summary.md"
            summary = self._generate_summary(
                all_messages, merged_qualification_data)
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)

            # Generate LLM summary in background thread (non-blocking)
            if len(all_messages) >= 4:
                try:
                    import threading
                    thread = threading.Thread(
                        target=self._generate_llm_summary_sync,
                        args=(all_messages, summary_file, call_sid),
                        daemon=True
                    )
                    thread.start()
                except Exception as e:
                    logger.debug("Could not schedule LLM summary thread",
                                 call_sid=call_sid, error=str(e))

            logger.info("Conversation logged", call_sid=call_sid,
                        total_messages=len(all_messages),
                        new_messages=len(new_formatted_messages),
                        transcript_file=str(transcript_file),
                        summary_file=str(summary_file))

            return {
                "transcript": str(transcript_file),
                "summary": str(summary_file),
            }
        except Exception as e:
            logger.error("Failed to log conversation",
                         call_sid=call_sid, error=str(e), exc_info=True)
            return {}

    def _generate_summary(self, messages: list[Any], qualification_data: dict) -> str:
        """Generate markdown summary of conversation with LLM-powered insights."""
        lines = ["# Conversation Summary\n"]
        lines.append(
            f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Build conversation transcript
        transcript_lines = []
        for msg in messages:
            if isinstance(msg, dict):
                msg_type = msg.get("type", "unknown").upper()
                content = msg.get("content", "")
            else:
                msg_type = "AI" if hasattr(
                    msg, "__class__") and "AIMessage" in str(type(msg)) else "HUMAN"
                content = getattr(msg, "content", str(msg))

            if content:
                transcript_lines.append(f"**{msg_type}:** {content}\n")

        lines.append("## Conversation Transcript\n")
        lines.extend(transcript_lines)

        lines.append("\n## Ticket Data\n")
        for key, value in qualification_data.items():
            if value:
                if isinstance(value, list):
                    value_str = ", ".join(str(v)
                                          for v in value) if value else "None"
                else:
                    value_str = str(value)
                lines.append(
                    f"- **{key.replace('_', ' ').title()}:** {value_str}\n")

        # Add conversation metrics
        lines.append("\n## Conversation Metrics\n")
        lines.append(f"- **Total Messages:** {len(messages)}\n")
        human_messages = sum(1 for msg in messages
                             if (isinstance(msg, dict) and msg.get('type') == 'human') or
                             (hasattr(msg, '__class__') and 'HumanMessage' in str(type(msg))))
        ai_messages = len(messages) - human_messages
        lines.append(f"- **User Messages:** {human_messages}\n")
        lines.append(f"- **AI Messages:** {ai_messages}\n")

        if qualification_data.get("issue_type"):
            lines.append(
                f"- **Issue Type:** {qualification_data.get('issue_type')}\n")
        if qualification_data.get("severity"):
            lines.append(
                f"- **Severity:** {qualification_data.get('severity')}\n")

        return "".join(lines)

    def _generate_llm_summary_sync(
        self, messages: list[Any], summary_file: Path, call_sid: str
    ) -> None:
        """Generate LLM-powered summary in a thread and append to existing summary file."""
        try:
            import asyncio
            conversation_text = "\n".join([
                f"{'AI' if (isinstance(msg, dict) and msg.get('type') == 'ai') or (hasattr(msg, '__class__') and 'AIMessage' in str(type(msg))) else 'User'}: {msg.get('content', '') if isinstance(msg, dict) else getattr(msg, 'content', str(msg))}"
                for msg in messages
            ])

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm_summary = loop.run_until_complete(
                    llm_service.summarize_conversation(conversation_text)
                )

                if llm_summary and summary_file.exists():
                    with open(summary_file, "r", encoding="utf-8") as f:
                        existing_content = f.read()

                    if "## AI-Generated Summary" not in existing_content:
                        with open(summary_file, "a", encoding="utf-8") as f:
                            f.write("\n## AI-Generated Summary\n")
                            f.write(f"{llm_summary}\n")
                        logger.info(
                            "LLM summary appended to conversation", call_sid=call_sid)
            finally:
                loop.close()
        except Exception as e:
            logger.warning("Failed to generate LLM summary",
                           call_sid=call_sid, error=str(e))


conversation_logger = ConversationLogger()
