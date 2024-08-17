import pytest
import asyncio
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from bot import start, pay, help_command

@pytest.mark.asyncio
async def test_start():
    user = User(id=1, is_bot=False, first_name="TestUser")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=None, chat=chat, text="/start", from_user=user)
    update = Update(update_id=1, message=message)
    
    context = ContextTypes.DEFAULT_TYPE()
    
    await start(update, context)
    # Assert that the correct welcome message is sent
    assert update.message.text == "Welcome to the MPESA Payment Bot. Please choose an option: \n 1. Pay  \n 2. Help"

@pytest.mark.asyncio
async def test_pay():
    user = User(id=1, is_bot=False, first_name="TestUser")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=None, chat=chat, text="/pay 254712345678 100", from_user=user)
    update = Update(update_id=1, message=message)
    
    context = ContextTypes.DEFAULT_TYPE()

    await pay(update, context)
    # Assert that a payment initiation message is sent
    assert "Payment initiated successfully" in update.message.text

@pytest.mark.asyncio
async def test_help_command():
    user = User(id=1, is_bot=False, first_name="TestUser")
    chat = Chat(id=1, type="private")
    message = Message(message_id=1, date=None, chat=chat, text="/help", from_user=user)
    update = Update(update_id=1, message=message)
    
    context = ContextTypes.DEFAULT_TYPE()
    
    await help_command(update, context)
    # Assert that the help message is sent
    assert "To initiate a payment" in update.message.text
