# openai_client.py
"""
OpenAI Client with detailed logging
"""
from openai import OpenAI
import json
import os
import tempfile


class OpenAIClient:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.api_key_preview = api_key[:10] + "..." if api_key else "None"
        print(f"[OpenAI] Client initialized with key: {self.api_key_preview}")

    def chat_completion(
        self,
        messages,
        model='gpt-4o',
        temperature=0.7,
        tools=None,
        max_retries=3,
        max_tokens=4096
    ):
        print(f"\n{'='*50}")
        print(f"[OpenAI] === SENDING REQUEST ===")
        print(f"[OpenAI] Model: {model}")
        print(f"[OpenAI] Temperature: {temperature}")
        print(f"[OpenAI] Max tokens: {max_tokens}")
        print(f"[OpenAI] Messages count: {len(messages)}")

        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]
            print(f"[OpenAI] Message {i}: role={role}, content={content}...")

        if tools:
            print(f"[OpenAI] Tools: {[t['function']['name'] for t in tools]}")

        attempt = 0
        last_error = None

        while attempt < max_retries:
            try:
                print(f"[OpenAI] Attempt {attempt + 1}/{max_retries}...")

                params = {
                    'model': model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens
                }

                if tools:
                    params['tools'] = tools
                    params['tool_choice'] = 'auto'

                print(f"[OpenAI] Calling API...")
                response = self.client.chat.completions.create(**params)
                print(f"[OpenAI] === RESPONSE RECEIVED ===")

                message = response.choices[0].message

                print(f"[OpenAI] Response content: {message.content[:500] if message.content else 'None'}...")
                print(f"[OpenAI] Tool calls: {message.tool_calls}")
                print(f"[OpenAI] Usage: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}")

                result = {
                    'content': message.content,
                    'tool_calls': [],
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    }
                }

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tc = {
                            'id': tool_call.id,
                            'function': tool_call.function.name,
                            'arguments': json.loads(tool_call.function.arguments)
                        }
                        result['tool_calls'].append(tc)
                        print(f"[OpenAI] Tool call: {tc['function']}({tc['arguments']})")

                print(f"[OpenAI] === REQUEST COMPLETE ===\n")
                return result

            except Exception as e:
                last_error = str(e)
                attempt += 1
                print(f"[OpenAI] ERROR (attempt {attempt}/{max_retries}): {e}")

                if attempt >= max_retries:
                    print(f"[OpenAI] FAILED after {max_retries} retries: {last_error}")
                    raise Exception(f"OpenAI API failed: {last_error}")

    def transcribe_audio(self, audio_data, language='ru', max_retries=3):
        print(f"[OpenAI] Transcribing audio, language={language}")

        attempt = 0
        while attempt < max_retries:
            try:
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_path = temp_file.name

                try:
                    with open(temp_path, 'rb') as audio_file:
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language=language
                        )
                    print(f"[OpenAI] Transcription: {transcript.text}")
                    return transcript.text
                finally:
                    os.remove(temp_path)

            except Exception as e:
                attempt += 1
                print(f"[OpenAI] Whisper error (attempt {attempt}): {e}")
                if attempt >= max_retries:
                    raise

    def build_system_prompt(
        self,
        custom_system_prompt=None,
        agent_description=None,
        current_time_info=None,
        rag_context=None
    ):
        parts = []

        if custom_system_prompt:
            parts.append(custom_system_prompt.strip())
        elif agent_description:
            parts.append(f"You are an AI assistant in Bitrix24. {agent_description}")
        else:
            parts.append("You are an AI assistant in Bitrix24.")

        if current_time_info:
            parts.append(f"\nCurrent date and time: {current_time_info}")

        if rag_context:
            parts.append(f"\n\n--- KNOWLEDGE BASE ---\n{rag_context}\n--- END KNOWLEDGE BASE ---")

        parts.append("""

Instructions:
- Answer briefly and to the point
- Use available functions to work with CRM
- Be polite and professional
- If you don't know the answer - say so honestly
""")

        prompt = "\n".join(parts)
        print(f"[OpenAI] System prompt length: {len(prompt)} chars")
        return prompt
