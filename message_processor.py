# message_processor.py
"""
Message Processor for AI Agents

Updated: 2025
- Added system_prompt support
- Added RAG context support
- Fixed encoding issues
"""
from datetime import datetime
import pytz
from openai_client import OpenAIClient
from tools_registry import get_enabled_tools, execute_tool


class MessageProcessor:
    def __init__(self, agent, bitrix_client, db):
        self.agent = agent
        self.bitrix = bitrix_client
        self.db = db
        self.openai = OpenAIClient(agent['openai_api_key'])

    def is_working_hours(self):
        """Check agent working hours"""
        if not self.agent['working_hours_enabled']:
            return True  # 24/7

        try:
            tz = pytz.timezone(self.agent['timezone'])
            now = datetime.now(tz)

            # Day of week (monday, tuesday, ...)
            weekday = now.strftime('%A').lower()

            schedule = self.agent.get('working_hours_schedule', {})

            if weekday not in schedule:
                return False  # Non-working day

            day_schedule = schedule[weekday]
            time_from = day_schedule.get('from', '00:00')
            time_to = day_schedule.get('to', '23:59')

            current_time = now.strftime('%H:%M')

            return time_from <= current_time <= time_to

        except Exception as e:
            print(f"Error checking working hours: {e}")
            return True  # Default to working

    def process_chat_messages(self, chat_table_id, chat_id):
        """
        Process accumulated messages in chat

        Args:
            chat_table_id: Chat ID in our DB
            chat_id: Chat ID in Bitrix24
        """
        # Check working hours
        if not self.is_working_hours():
            tz = pytz.timezone(self.agent['timezone'])
            now = datetime.now(tz)

            message = f"Thank you for reaching out! Our working hours are: {self._format_working_hours()}. We will respond during business hours."

            self.bitrix.bot_send_message(
                bot_id=self.agent['bot_id'],
                dialog_id=chat_id,
                message=message
            )
            self.db.add_log(
                self.agent['id'],
                'outside_working_hours',
                {'chat_id': chat_id, 'time': now.isoformat()},
                chat_table_id
            )
            return

        # Get unprocessed messages
        messages = self.db.get_unprocessed_messages(chat_table_id)

        if not messages:
            return

        # Build dialog history for GPT
        conversation = self._build_conversation(messages)

        # Get enabled tools
        tools = get_enabled_tools(self.agent.get('enabled_tools', []))

        try:
            # Request to OpenAI
            response = self.openai.chat_completion(
                messages=conversation,
                model=self.agent['openai_model'],
                temperature=self.agent['temperature'],
                tools=tools if tools else None,
                max_retries=self.agent['max_retries']
            )

            # Handle tool calls (if GPT called functions)
            if response['tool_calls']:
                tool_results = []

                for tool_call in response['tool_calls']:
                    result = execute_tool(
                        tool_call['function'],
                        tool_call['arguments'],
                        self.bitrix,
                        chat_id=chat_id,
                        agent_timezone=self.agent['timezone']
                    )

                    tool_results.append(result)

                    # Log function call
                    self.db.add_log(
                        self.agent['id'],
                        f"tool_call_{tool_call['function']}",
                        {
                            'arguments': tool_call['arguments'],
                            'result': result
                        },
                        chat_table_id,
                        success=result.get('success', False)
                    )

                    # If created lead/deal and Inbound Only is enabled
                    if self.agent['inbound_only']:
                        if tool_call['function'] in ['crm_lead_add', 'crm_deal_add']:
                            if result.get('success'):
                                # Update chat status
                                lead_id = result.get('lead_id')
                                deal_id = result.get('deal_id')

                                self.db.update_chat_status(
                                    chat_table_id,
                                    'completed',
                                    lead_id=lead_id,
                                    deal_id=deal_id
                                )

                                self.db.add_log(
                                    self.agent['id'],
                                    'inbound_only_disconnect',
                                    {'chat_id': chat_id, 'lead_id': lead_id, 'deal_id': deal_id},
                                    chat_table_id
                                )

                # Form final response
                final_message = response.get('content', '')

                if not final_message:
                    # If GPT didn't give text response, form one ourselves
                    successful = [r.get('message', 'OK') for r in tool_results if r.get('success')]
                    if successful:
                        final_message = "Done: " + ", ".join(successful)
                    else:
                        final_message = "Action completed."

            else:
                final_message = response.get('content', 'Sorry, I cannot respond.')

            # Send response to chat
            if final_message:
                self.bitrix.bot_send_message(
                    bot_id=self.agent['bot_id'],
                    dialog_id=chat_id,
                    message=final_message
                )

                self.db.add_log(
                    self.agent['id'],
                    'message_sent',
                    {'content': final_message},
                    chat_table_id
                )

            # Mark messages as processed
            message_ids = [m['id'] for m in messages]
            self.db.mark_messages_processed(message_ids)

        except Exception as e:
            print(f"Error processing messages: {e}")
            import traceback
            traceback.print_exc()

            self.db.add_log(
                self.agent['id'],
                'processing_error',
                {'error': str(e)},
                chat_table_id,
                success=False,
                error_message=str(e)
            )

    def _build_conversation(self, messages):
        """Build dialog history for GPT"""
        # Get current time info
        tz = pytz.timezone(self.agent['timezone'])
        now = datetime.now(tz)
        current_time = now.strftime('%Y-%m-%d %H:%M:%S %Z')

        # Get RAG context
        rag_context = self.db.get_rag_context(self.agent['id'], max_length=4000)

        # Build system prompt
        system_prompt = self.openai.build_system_prompt(
            custom_system_prompt=self.agent.get('system_prompt'),
            agent_description=self.agent.get('description'),
            current_time_info=current_time,
            rag_context=rag_context
        )

        conversation = [
            {"role": "system", "content": system_prompt}
        ]

        # Add messages
        for msg in messages:
            role = "assistant" if msg['author_type'] == 'bot' else "user"

            content = msg['content']

            # If voice message - use transcription
            if msg['is_audio'] and msg['audio_transcription']:
                content = f"[Voice message]: {msg['audio_transcription']}"

            conversation.append({
                "role": role,
                "content": content
            })

        return conversation

    def _format_working_hours(self):
        """Format working hours for message"""
        if not self.agent['working_hours_enabled']:
            return "24/7"

        schedule = self.agent.get('working_hours_schedule', {})

        if not schedule:
            return "24/7"

        days_short = {
            'monday': 'Mon',
            'tuesday': 'Tue',
            'wednesday': 'Wed',
            'thursday': 'Thu',
            'friday': 'Fri',
            'saturday': 'Sat',
            'sunday': 'Sun'
        }

        parts = []
        for day, times in schedule.items():
            day_name = days_short.get(day, day)
            parts.append(f"{day_name} {times['from']}-{times['to']}")

        return ", ".join(parts)

    def process_audio_message(self, chat_table_id, message_data, audio_data):
        """
        Process voice message

        Args:
            chat_table_id: Chat ID in DB
            message_data: message data
            audio_data: audio file bytes
        """
        if not self.agent['audio_transcription']:
            return  # Transcription disabled

        try:
            # Determine language (can improve logic)
            language = 'ru'  # Default

            # Transcribe
            transcription = self.openai.transcribe_audio(
                audio_data,
                language=language,
                max_retries=self.agent['max_retries']
            )

            # Save transcription
            message_data['audio_transcription'] = transcription
            message_data['is_audio'] = 1

            self.db.add_log(
                self.agent['id'],
                'audio_transcribed',
                {'transcription': transcription},
                chat_table_id
            )

        except Exception as e:
            print(f"Transcription error: {e}")

            self.db.add_log(
                self.agent['id'],
                'audio_transcription_error',
                {'error': str(e)},
                chat_table_id,
                success=False,
                error_message=str(e)
            )
