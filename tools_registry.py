# tools_registry.py
"""
Registry of ready-to-use functions for OpenAI Function Calling

Updated: 2025
- Updated function definitions format
- Added more CRM tools
"""

# Function definitions for OpenAI
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "crm_lead_add",
            "description": "Create a lead (potential client) in CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Client name"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "email": {"type": "string", "description": "Email address"},
                    "comments": {"type": "string", "description": "Comment or notes"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_deal_add",
            "description": "Create a deal in CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Deal title"},
                    "contact_id": {"type": "integer", "description": "Contact ID"},
                    "opportunity": {"type": "number", "description": "Deal amount"},
                    "comments": {"type": "string", "description": "Comment or notes"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_contact_add",
            "description": "Create a contact in CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "First name"},
                    "last_name": {"type": "string", "description": "Last name"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "email": {"type": "string", "description": "Email address"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_lead_get",
            "description": "Get lead information by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "Lead ID"}
                },
                "required": ["lead_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_deal_get",
            "description": "Get deal information by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_id": {"type": "integer", "description": "Deal ID"}
                },
                "required": ["deal_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_contact_get",
            "description": "Get contact information by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "integer", "description": "Contact ID"}
                },
                "required": ["contact_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_chat_to_user",
            "description": "Transfer chat to a human operator",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Employee ID"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_agent_from_chat",
            "description": "Disconnect AI agent from chat (end dialog)",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_todays_date",
            "description": "Get current date and time",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_lead_update",
            "description": "Update an existing lead in CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "Lead ID to update"},
                    "name": {"type": "string", "description": "New client name"},
                    "phone": {"type": "string", "description": "New phone number"},
                    "email": {"type": "string", "description": "New email address"},
                    "status_id": {"type": "string", "description": "New status ID"},
                    "comments": {"type": "string", "description": "New comment or notes"}
                },
                "required": ["lead_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crm_deal_update",
            "description": "Update an existing deal in CRM",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_id": {"type": "integer", "description": "Deal ID to update"},
                    "title": {"type": "string", "description": "New deal title"},
                    "opportunity": {"type": "number", "description": "New deal amount"},
                    "stage_id": {"type": "string", "description": "New stage ID"},
                    "comments": {"type": "string", "description": "New comment or notes"}
                },
                "required": ["deal_id"]
            }
        }
    }
]


def execute_tool(tool_name, arguments, bitrix_client, chat_id=None, agent_timezone='UTC'):
    """
    Execute a function

    Args:
        tool_name: function name
        arguments: function arguments
        bitrix_client: BitrixClient instance
        chat_id: chat ID (for transfer/disconnect)
        agent_timezone: agent timezone

    Returns:
        dict: execution result
    """
    try:
        # CRM LEAD
        if tool_name == 'crm_lead_add':
            fields = {
                'TITLE': arguments.get('name'),
                'NAME': arguments.get('name'),
            }
            if arguments.get('phone'):
                fields['PHONE'] = [{'VALUE': arguments['phone'], 'VALUE_TYPE': 'WORK'}]
            if arguments.get('email'):
                fields['EMAIL'] = [{'VALUE': arguments['email'], 'VALUE_TYPE': 'WORK'}]
            if arguments.get('comments'):
                fields['COMMENTS'] = arguments['comments']

            result = bitrix_client.crm_lead_add(fields)
            return {'success': True, 'lead_id': result, 'message': f'Lead created (ID: {result})'}

        elif tool_name == 'crm_lead_get':
            result = bitrix_client.crm_lead_get(arguments['lead_id'])
            return {'success': True, 'data': result}

        elif tool_name == 'crm_lead_update':
            fields = {}
            if arguments.get('name'):
                fields['NAME'] = arguments['name']
                fields['TITLE'] = arguments['name']
            if arguments.get('phone'):
                fields['PHONE'] = [{'VALUE': arguments['phone'], 'VALUE_TYPE': 'WORK'}]
            if arguments.get('email'):
                fields['EMAIL'] = [{'VALUE': arguments['email'], 'VALUE_TYPE': 'WORK'}]
            if arguments.get('status_id'):
                fields['STATUS_ID'] = arguments['status_id']
            if arguments.get('comments'):
                fields['COMMENTS'] = arguments['comments']

            result = bitrix_client.crm_lead_update(arguments['lead_id'], fields)
            return {'success': True, 'message': f'Lead updated (ID: {arguments["lead_id"]})'}

        # CRM DEAL
        elif tool_name == 'crm_deal_add':
            fields = {
                'TITLE': arguments.get('title'),
            }
            if arguments.get('contact_id'):
                fields['CONTACT_ID'] = arguments['contact_id']
            if arguments.get('opportunity'):
                fields['OPPORTUNITY'] = arguments['opportunity']
            if arguments.get('comments'):
                fields['COMMENTS'] = arguments['comments']

            result = bitrix_client.crm_deal_add(fields)
            return {'success': True, 'deal_id': result, 'message': f'Deal created (ID: {result})'}

        elif tool_name == 'crm_deal_get':
            result = bitrix_client.crm_deal_get(arguments['deal_id'])
            return {'success': True, 'data': result}

        elif tool_name == 'crm_deal_update':
            fields = {}
            if arguments.get('title'):
                fields['TITLE'] = arguments['title']
            if arguments.get('opportunity'):
                fields['OPPORTUNITY'] = arguments['opportunity']
            if arguments.get('stage_id'):
                fields['STAGE_ID'] = arguments['stage_id']
            if arguments.get('comments'):
                fields['COMMENTS'] = arguments['comments']

            result = bitrix_client.crm_deal_update(arguments['deal_id'], fields)
            return {'success': True, 'message': f'Deal updated (ID: {arguments["deal_id"]})'}

        # CRM CONTACT
        elif tool_name == 'crm_contact_add':
            fields = {
                'NAME': arguments.get('name'),
            }
            if arguments.get('last_name'):
                fields['LAST_NAME'] = arguments['last_name']
            if arguments.get('phone'):
                fields['PHONE'] = [{'VALUE': arguments['phone'], 'VALUE_TYPE': 'WORK'}]
            if arguments.get('email'):
                fields['EMAIL'] = [{'VALUE': arguments['email'], 'VALUE_TYPE': 'WORK'}]

            result = bitrix_client.crm_contact_add(fields)
            return {'success': True, 'contact_id': result, 'message': f'Contact created (ID: {result})'}

        elif tool_name == 'crm_contact_get':
            result = bitrix_client.crm_contact_get(arguments['contact_id'])
            return {'success': True, 'data': result}

        # CHAT ACTIONS
        elif tool_name == 'transfer_chat_to_user':
            if not chat_id:
                return {'success': False, 'error': 'chat_id required'}

            # Extract numeric chat_id if it's in format "chatXX"
            numeric_chat_id = chat_id
            if isinstance(chat_id, str) and chat_id.startswith('chat'):
                numeric_chat_id = chat_id[4:]

            result = bitrix_client.openlines_operator_transfer(numeric_chat_id, arguments['user_id'])
            return {'success': True, 'message': 'Chat transferred to operator'}

        elif tool_name == 'disconnect_agent_from_chat':
            if not chat_id:
                return {'success': False, 'error': 'chat_id required'}

            # Extract numeric chat_id if it's in format "chatXX"
            numeric_chat_id = chat_id
            if isinstance(chat_id, str) and chat_id.startswith('chat'):
                numeric_chat_id = chat_id[4:]

            result = bitrix_client.openlines_operator_finish(numeric_chat_id)
            return {'success': True, 'message': 'Agent disconnected from chat'}

        # UTILITIES
        elif tool_name == 'get_todays_date':
            from datetime import datetime
            import pytz

            tz = pytz.timezone(agent_timezone)
            now = datetime.now(tz)

            return {
                'success': True,
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                'timezone': agent_timezone
            }

        else:
            return {'success': False, 'error': f'Unknown function: {tool_name}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_enabled_tools(tool_names):
    """
    Get descriptions of only enabled tools

    Args:
        tool_names: list of function names ['crm_lead_add', 'crm_deal_add']

    Returns:
        list: list of function descriptions for OpenAI
    """
    if not tool_names:
        return []

    enabled = []
    for tool_def in TOOLS_DEFINITIONS:
        if tool_def['function']['name'] in tool_names:
            enabled.append(tool_def)

    return enabled


def get_all_tools():
    """
    Get all available tools

    Returns:
        list: list of all tool names with descriptions
    """
    return [
        {
            'name': tool['function']['name'],
            'description': tool['function']['description']
        }
        for tool in TOOLS_DEFINITIONS
    ]
