#!/usr/bin/env python3
"""
Simple test script to verify Telegram Bot API is working correctly
Run this to test if the inline keyboard buttons work
"""

import asyncio
import aiohttp
import os
import sys

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Get credentials from environment or edit directly here
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")


async def test_telegram():
    """Test Telegram API with inline keyboard"""
    
    print("=" * 50)
    print("🧪 TELEGRAM BOT API TEST")
    print("=" * 50)
    print(f"Token: {BOT_TOKEN[:10]}..." if len(BOT_TOKEN) > 10 else f"Token: {BOT_TOKEN}")
    print(f"Chat ID: {CHAT_ID}")
    print("=" * 50)
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set TELEGRAM_TOKEN environment variable or edit this file")
        return
    
    if CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("❌ Please set TELEGRAM_CHAT_ID environment variable or edit this file")
        return
    
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get bot info
        print("\n📋 Test 1: Get Bot Info")
        async with session.get(f"{base_url}/getMe") as response:
            data = await response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ Bot Name: {bot_info.get('first_name')}")
                print(f"✅ Bot Username: @{bot_info.get('username')}")
            else:
                print(f"❌ Error: {data.get('description')}")
                return
        
        # Test 2: Send simple message
        print("\n📋 Test 2: Send Simple Message")
        async with session.post(f"{base_url}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": "🧪 Test message without keyboard",
            "parse_mode": "HTML"
        }) as response:
            data = await response.json()
            if data.get("ok"):
                print("✅ Simple message sent successfully!")
            else:
                print(f"❌ Error: {data.get('description')}")
                print(f"   Full response: {data}")
                return
        
        await asyncio.sleep(1)  # Small delay
        
        # Test 3: Send message with inline keyboard
        print("\n📋 Test 3: Send Message with Inline Keyboard")
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📊 Button 1", "callback_data": "btn1"},
                    {"text": "📅 Button 2", "callback_data": "btn2"}
                ],
                [
                    {"text": "❓ Button 3", "callback_data": "btn3"}
                ]
            ]
        }
        
        async with session.post(f"{base_url}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": "🧪 <b>Test message WITH inline keyboard</b>\n\nClick a button below:",
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }) as response:
            data = await response.json()
            if data.get("ok"):
                print("✅ Message with inline keyboard sent successfully!")
                print("📱 Check your Telegram - you should see buttons!")
            else:
                print(f"❌ Error: {data.get('description')}")
                print(f"   Full response: {data}")
                return
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        print("\nIf you see buttons in Telegram, the API is working.")
        print("If NOT, the issue might be:")
        print("  - Wrong chat_id format")
        print("  - Bot doesn't have access to the chat")
        print("  - Telegram server issues")


if __name__ == "__main__":
    asyncio.run(test_telegram())

