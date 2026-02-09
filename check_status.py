"""Quick diagnostic script"""
import time
from database import Database
from config import Config

db = Database(Config.DATABASE)

print("=== DIAGNOSTICS ===")
print(f"Domain: {Config.BITRIX_DOMAIN}")
print(f"PUBLIC_URL: {Config.PUBLIC_URL}")
print(f"CLIENT_ID: {Config.CLIENT_ID}")
print(f"CLIENT_SECRET configured: {Config.CLIENT_SECRET not in ('YOUR_CLIENT_SECRET', '')}")

app_data = db.get_app(Config.BITRIX_DOMAIN)
if app_data:
    remaining = int(app_data['expires_at']) - int(time.time())
    print(f"OAuth token: present ({remaining}s / {remaining//60}m remaining)")
    if remaining < 0:
        print("  WARNING: Token EXPIRED!")
else:
    print("OAuth token: NOT FOUND - need to install app first!")

agents = db.get_agents(Config.BITRIX_DOMAIN)
print(f"\nAgents: {len(agents)}")
for a in agents:
    print(f"  #{a['id']}: {a['name']}")
    print(f"    bot_id={a.get('bot_id')}, active={a.get('is_active')}, open_line={a.get('open_line_id')}")

# Test API call
if app_data:
    from bitrix_client import BitrixClient
    bitrix = BitrixClient(domain=Config.BITRIX_DOMAIN, db=db)
    try:
        user = bitrix.call('user.current')
        print(f"\nAPI test: OK (user={user.get('NAME')} {user.get('LAST_NAME')})")
    except Exception as e:
        print(f"\nAPI test FAILED: {e}")

    # Check bot registration
    for a in agents:
        if a.get('bot_id'):
            try:
                bots = bitrix.call('imbot.bot.list')
                bot_ids = []
                if isinstance(bots, list):
                    bot_ids = [b.get('ID') or b.get('id') for b in bots]
                print(f"\n  Registered bots in Bitrix: {bot_ids}")
                if str(a['bot_id']) in [str(b) for b in bot_ids]:
                    print(f"  Bot {a['bot_id']} EXISTS in Bitrix24")
                else:
                    print(f"  WARNING: Bot {a['bot_id']} NOT FOUND in Bitrix24!")
            except Exception as e:
                print(f"  Error checking bots: {e}")
            break
