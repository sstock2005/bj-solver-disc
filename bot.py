from dataclasses import dataclass
from enum import Enum
import threading
import discord
import logging
import asyncio
import json
import time
import re
import os

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    handlers=[ logging.FileHandler("bot.log") ]
    )

log = logging.getLogger(__name__)

# Silence discord.py-self logs
discord_client = logging.getLogger('discord.client')
discord_http = logging.getLogger('discord.http')
discord_gateway = logging.getLogger('discord.gateway')
discord_client.setLevel(logging.CRITICAL)
discord_http.setLevel(logging.CRITICAL)
discord_gateway.setLevel(logging.CRITICAL)

# Constants
DISCORD_TOKEN = "INVALID TOKEN!!!"
BJ_BOT_ID = 292953664492929025
START_PATTERN = r"`hit` - take another card"
TIMEOUT_PATTERN = r"You can play `blackjack` again in"
BLACKJACK_PATTERN = r"Result: Win"
ERROR_PATTERN = r"You are currently playing blackjack"
PUSH_PATTERN = r"Result: Push, money back"
TIME_DELAY = 0
TIME_ELAPSED = 0
game_over = True
GAMES_LOG = {}
GAME_COUNT = 0
LAST_ERROR = ""
STATUS = "IDLE"

class CardNumber(Enum):
    ACE = 'ACE'
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 10
    QUEEN = 10
    KING = 10

    @classmethod
    def from_str(self, raw: str):
        match raw:
            case 'a':
                return CardNumber.ACE
            case '2':
                return CardNumber.TWO
            case '3':
                return CardNumber.THREE
            case '4':
                return CardNumber.FOUR
            case '5':
                return CardNumber.FIVE
            case '6':
                return CardNumber.SIX
            case '7':
                return CardNumber.SEVEN
            case '8':
                return CardNumber.EIGHT
            case '9':
                return CardNumber.NINE
            case '10':
                return CardNumber.TEN
            case 'j':
                return CardNumber.JACK
            case 'q':
                return CardNumber.QUEEN
            case 'k':
                return CardNumber.KING
            case _:
                return None

class CardSuit(Enum):
    CLUB = 'CLUB'
    DIAMOND = 'DIAMOND'
    HEART = 'HEART'
    SPADES = 'SPADES'

    @classmethod
    def from_str(self, raw: str):
        match raw:
            case 'C':
                return CardSuit.CLUB
            case 'D':
                return CardSuit.DIAMOND
            case 'H':
                return CardSuit.HEART
            case 'S':
                return CardSuit.SPADES
            case _:
                return None

@dataclass
class Card:
    number: CardNumber
    suit: CardSuit

async def save_games():
    """Saves the current GAMES_LOG to file"""
    log.debug("Saved games_log.json")
    with open('games_log.json', 'w', encoding='utf-8') as f:
        json.dump(GAMES_LOG, f, indent=4, sort_keys=True, ensure_ascii=False)

class SolverClient(discord.Client):
    """The discordpy-self client class"""

    async def on_ready(self):
        """Triggers when the self bot is ready.\n- sets STATUS to ONLINE\n- starts the background task"""
        global STATUS
        log.debug(f'Online as {self.user}')
        STATUS = "ONLINE"
        self.bg_task = self.loop.create_task(self.background_task())

    async def background_task(self):
        """The main background task.\n- Waits until the discordpy-self client is ready\n- Gets bot channel\n- Loops while the client is not closed and checks if the game is over\n    - If the game is over
        the thread sleeps for 2 seconds and then sends the initial playing message\n- It then waits 2 seconds and then restarts the loop"""
        global STATUS
        try:
            await self.wait_until_ready()
            channel = self.get_channel(1315870486395359365)
            while not self.is_closed():
                global game_over
                if game_over and channel:
                    STATUS = "IDLE"
                    global TIME_DELAY
                    TIME_DELAY += 2
                    await asyncio.sleep(2)
                    await channel.send('!bj 100')
                    game_over = False
                TIME_DELAY += 2
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            log.critical("Keyboard Interrupt!")

    async def on_message(self, message):
        """This is the main function basically.\n- Checks if the current user is the blackjob bot's ID and if the message has embeds\n- Iterates through the embed description
        \n    - If BLACKJACK Pattern: Logs winning and ends game\n    - If TIMEOUT Pattern: logs timeout, waits, and starts the loop again
            \n    - If PUSH Pattern: Logs push and ends game\n    - If START Pattern: Checks if the game is over and logs the result, goes through player hand and dealer hand and makes move based on hands
            \n    - If ERROR Pattern: Extracts original game id and starts the loop again"""
        try:
            current_user = message.author

            if current_user.id == BJ_BOT_ID and len(message.embeds) != 0:
                global game_over, GAMES_LOG, GAME_COUNT, STATUS
                game_over = False
                STATUS = "PLAYING"

                embed_description = message.embeds[0].description

                if BLACKJACK_PATTERN in embed_description:
                    logging.debug("Game Over")
                    STATUS = "IDLE"
                    bj_profit = message.embeds[0].description.split("> ")[1]
                    GAMES_LOG[GAME_COUNT] = f"WIN:BJ:+{bj_profit}"
                    await save_games()
                    GAME_COUNT += 1
                    game_over = True
                    return

                if TIMEOUT_PATTERN in embed_description:
                    time_raw = embed_description.split('again in ')[1].removesuffix('.')
                    regex = re.search(r'(\d+) minute(?:s)?(?: and )?(\d+) second(?:s)?', time_raw)

                    if regex:
                        minutes = int(regex.group(1))
                        seconds = int(regex.group(2))

                        sleep_seconds = (minutes * 60) + seconds
                    else:
                        logging.error("Could not get timeout time from embed!")
                        sleep_seconds = 0

                    logging.debug(f"Timeout for {time_raw} ({sleep_seconds} seconds)!")
                    STATUS = f"TIMEOUT ({time_raw})"
                    try:
                        global TIME_DELAY
                        TIME_DELAY += sleep_seconds
                        time.sleep(sleep_seconds)
                    except KeyboardInterrupt:
                        log.critical("Keyboard Interrupt!")
                    
                    TIME_DELAY += 2
                    time.sleep(2)
                    game_over = True
                    STATUS = "IDLE"
                    return
                
                if PUSH_PATTERN in embed_description:
                    GAMES_LOG[GAME_COUNT] = f"PUSH:PUSH:0"
                    GAME_COUNT += 1
                    await save_games()
                    log.debug("Game Over")
                    STATUS = "IDLE"
                    return

                if START_PATTERN in embed_description and not ERROR_PATTERN in embed_description:
                    bj_message = message
                    log.debug(f"Found Blackjack message! ID: {bj_message.id}")

                    while not game_over:
                        STATUS = "PLAYING"
                        TIME_DELAY += 2
                        time.sleep(2) # delay
                        new_message = await self.get_channel(message.channel.id).fetch_message(message.id)
                        if "Result:" in new_message.embeds[0].description:
                            TIME_DELAY += 2
                            time.sleep(2)
                            game_over = True # end of game

                            if "Result: Win" in message.embeds[0].description:
                                RESULT = "WIN"
                                WIN_CONDITION = RESULT
                                PROFIT = message.embeds[0].description.split("> ")[1]
                            if "Result: Dealer bust" in message.embeds[0].description:
                                RESULT = "WIN"
                                WIN_CONDITION = "BUST"
                                PROFIT = message.embeds[0].description.split("> ")[1]
                            if "Result: Loss" in message.embeds[0].description:
                                RESULT = "LOSS"
                                LOSS_CONDITION = RESULT
                                LOSS = message.embeds[0].description.split("> -")[1]
                            if "Result: Bust" in message.embeds[0].description:
                                RESULT = "LOSS"
                                LOSS_CONDITION = "BUST"
                                LOSS = message.embeds[0].description.split("> -")[1]
                            if "Result: Push, money back" in message.embeds[0].description:
                                RESULT = "PUSH"

                            match RESULT:
                                case "WIN":
                                    GAMES_LOG[GAME_COUNT] = f"WIN:{WIN_CONDITION}:+{PROFIT}"
                                case "LOSS":
                                    GAMES_LOG[GAME_COUNT] = f"LOSS:{LOSS_CONDITION}:-{LOSS}"
                                case "PUSH":
                                    GAMES_LOG[GAME_COUNT] = f"PUSH:PUSH:0"
                            
                            await save_games()
                            GAME_COUNT += 1
                            log.debug("Game Over")
                            break

                        your_hand = new_message.embeds[0].fields[0].value.split()
                        player_hand = []
                        dealer_hand = []
                    
                        for item in your_hand:
                            if item.startswith('<'):
                                hand = item.split(':')

                                card = hand[1]

                                found_card = process_card(card)

                                if found_card != None:
                                    player_hand.append(found_card)
                                else:
                                    log.error("Could not find card from raw!")

                        their_hand = new_message.embeds[0].fields[1].value.split()

                        for item in their_hand:
                            if item.startswith('<'):
                                if "cardBack" in item:
                                    continue # this is the dealer's hidden card

                                hand = item.split(':')

                                card = hand[1]

                                found_card = process_card(card)

                                if found_card != None:
                                    dealer_hand.append(found_card)
                                else:
                                    log.error("Could not find card from raw!")

                        if len(player_hand) > 0 and len(dealer_hand) > 0:
                            log.info(f"Player's Hand:\n{player_hand}")
                            log.info(f"Dealer's Hand:\n{dealer_hand}")
                            second_move = calculate_move(player_hand, dealer_hand)

                            if second_move == None:
                                log.error("No Move Found")
                                return
                            
                            log.info(f"Move: {second_move}")

                            match second_move:
                                case 'HIT':
                                    await bj_message.components[0].children[0].click()
                                case 'STAND':
                                    await bj_message.components[0].children[1].click()
                                case 'DOUBLE':
                                    await bj_message.components[0].children[2].click()
                                case 'SPLIT':
                                    await bj_message.components[0].children[3].click()
                                case _:
                                    pass

                if ERROR_PATTERN in embed_description:
                    log.error("Error message found!")
                    old_game_id = re.search(r"/(\d+)$", message.embeds[0].description.split("[Jump to message](")[1]).group(1)
                    log.debug("Old Game ID:", old_game_id)
                    # TODO: Work on this
                    old_message = await self.get_channel(message.channel.id).fetch_message(old_game_id)
                    while not game_over:
                        STATUS = "PLAYING"
                        TIME_DELAY += 2
                        time.sleep(2) # delay
                        new_message = await self.get_channel(old_message.channel.id).fetch_message(old_message.id)
                        if "Result:" in new_message.embeds[0].description:

                            TIME_DELAY += 2
                            time.sleep(2)
                            game_over = True # end of game

                            if "Result: Win" in message.embeds[0].description:
                                RESULT = "WIN"
                                WIN_CONDITION = RESULT
                                PROFIT = message.embeds[0].description.split("> ")[1]
                            if "Result: Dealer bust" in message.embeds[0].description:
                                RESULT = "WIN"
                                WIN_CONDITION = "BUST"
                                PROFIT = message.embeds[0].description.split("> ")[1]
                            if "Result: Loss" in message.embeds[0].description:
                                RESULT = "LOSS"
                                LOSS_CONDITION = RESULT
                                LOSS = message.embeds[0].description.split("> -")[1]
                            if "Result: Bust" in message.embeds[0].description:
                                RESULT = "LOSS"
                                LOSS_CONDITION = "BUST"
                                LOSS = message.embeds[0].description.split("> -")[1]
                            if "Result: Push, money back" in message.embeds[0].description:
                                RESULT = "PUSH"

                            match RESULT:
                                case "WIN":
                                    GAMES_LOG[GAME_COUNT] = f"WIN:{WIN_CONDITION}:+{PROFIT}"
                                case "LOSS":
                                    GAMES_LOG[GAME_COUNT] = f"LOSS:{LOSS_CONDITION}:-{LOSS}"
                                case "PUSH":
                                    GAMES_LOG[GAME_COUNT] = f"PUSH:PUSH:0"

                            await save_games()
                            GAME_COUNT += 1
                            log.debug("Game Over")
                            break

                        your_hand = new_message.embeds[0].fields[0].value.split()
                        player_hand = []
                        dealer_hand = []
                    
                        for item in your_hand:
                            if item.startswith('<'):
                                hand = item.split(':')

                                card = hand[1]

                                found_card = process_card(card)

                                if found_card != None:
                                    player_hand.append(found_card)
                                else:
                                    log.error("Could not find card from raw!")

                        their_hand = new_message.embeds[0].fields[1].value.split()

                        for item in their_hand:
                            if item.startswith('<'):
                                if "cardBack" in item:
                                    continue # this is the dealer's hidden card

                                hand = item.split(':')

                                card = hand[1]

                                found_card = process_card(card)

                                if found_card != None:
                                    dealer_hand.append(found_card)
                                else:
                                    log.error("Could not find card from raw!")

                        if len(player_hand) > 0 and len(dealer_hand) > 0:
                            log.info(f"Player's Hand:\n{player_hand}")
                            log.info(f"Dealer's Hand:\n{dealer_hand}")
                            second_move = calculate_move(player_hand, dealer_hand)

                            if second_move == None:
                                log.error("No Move Found")
                                return
                            
                            log.info(f"Move: {second_move}")

                            match second_move:
                                case 'HIT':
                                    await bj_message.components[0].children[0].click()
                                case 'STAND':
                                    await bj_message.components[0].children[1].click()
                                case 'DOUBLE':
                                    await bj_message.components[0].children[2].click()
                                case 'SPLIT':
                                    await bj_message.components[0].children[3].click()
                                case _:
                                    pass

                    TIME_DELAY += 2
                    time.sleep(2)
                    game_over = True
                
                TIME_DELAY += 2
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            log.critical("Keyboard Interrupt!")

def calculate_move(player_hand: list[Card], dealer_hand: list[Card]):
    """Calculates next move based off of \"perfect\" blackjack"""
    try:
        dealers_upcard = dealer_hand[0].number.value
        player_first_card = player_hand[0].number.value
        player_second_card = player_hand[1].number.value
        
        player_total = 0

        # Pair Based
        if player_first_card == 2 and player_second_card == 2:
            if dealers_upcard in range(2, 4) or dealers_upcard in range(8, 11) or dealers_upcard == 'ACE':
                return 'HIT'
            if dealers_upcard in range(4, 8):
                return 'SPLIT'
        if player_first_card == 3 and player_second_card == 3:
            if dealers_upcard in range(2, 4) or dealers_upcard in range(8, 11) or dealers_upcard == 'ACE':
                return 'HIT'
            if dealers_upcard in range(4, 8):
                return 'SPLIT'
        if player_first_card == 4 and player_second_card == 4:
            return 'HIT'
        if player_first_card == 5 and player_second_card == 5:
            if dealers_upcard in range(2, 10):
                return 'DOUBLE'
            if dealers_upcard == 10 or dealers_upcard == 'ACE':
                return 'HIT'
        if player_first_card == 6 and player_second_card == 6:
            if dealers_upcard in range(2, 7):
                return 'SPLIT'
            if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                return 'HIT'
        if player_first_card == 7 and player_second_card == 7:
            if dealers_upcard in range(2, 7):
                return 'SPLIT'
            if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                return 'HIT'
        if player_first_card == 8 and player_second_card == 8:
            return 'SPLIT'
        if player_first_card == 9 and player_second_card == 9:
            if dealers_upcard in range(2, 7) or dealers_upcard in range(8, 10):
                return 'SPLIT'
            if dealers_upcard == 7 or dealers_upcard == 10 or dealers_upcard == 'ACE':
                return 'STAND'
        if player_first_card == 10 and player_second_card == 10:
            return 'STAND'

        # ACE Pair
        if player_first_card == 'ACE' and player_second_card == 'ACE':
            return 'SPLIT'

        # ACE Based
        if player_first_card == 'ACE':
            match player_second_card:
                case 2:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 3:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 4:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 5:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 6:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 7:
                    if dealers_upcard == 2 or dealers_upcard in range(7, 9):
                        return 'STAND'
                    if dealers_upcard in range(3, 7):
                        return 'DOUBLE'
                case 8:
                    return 'STAND'
                case 9:
                    return 'STAND'

        # ACE Based
        if player_second_card == 'ACE':
            match player_first_card:
                case 2:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 3:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 4:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 5:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 6:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'DOUBLE'
                case 7:
                    if dealers_upcard == 2 or dealers_upcard in range(7, 9):
                        return 'STAND'
                    if dealers_upcard in range(3, 7):
                        return 'DOUBLE'
                case 8:
                    return 'STAND'
                case 9:
                    return 'STAND'

        # Total Based
        if player_first_card != 'ACE' and player_second_card != 'ACE':
            for card in player_hand:
                player_total += card.number.value

            if player_total in range(3, 9):
                return 'HIT'
            
            match player_total:
                case 9:
                    if dealers_upcard == 2 or dealers_upcard == 'ACE' or dealers_upcard in range(7, 11):
                        return 'HIT'
                    if dealers_upcard in range(3, 7):
                        return 'DOUBLE'
                case 10:
                    if dealers_upcard in range(2, 10):
                        return 'DOUBLE'
                    if dealers_upcard == 10 or dealers_upcard == 'ACE':
                        return 'HIT'
                case 11:
                    return 'DOUBLE'
                case 12:
                    if dealers_upcard in range(2, 4) or dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                    if dealers_upcard in range(4, 7):
                        return 'STAND'
                case 13:
                    if dealers_upcard in range(2, 7):
                        return 'STAND'
                    if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                case 14:
                    if dealers_upcard in range(2, 7):
                        return 'STAND'
                    if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                case 15:
                    if dealers_upcard in range(2, 7):
                        return 'STAND'
                    if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                case 16:
                    if dealers_upcard in range(2, 7):
                        return 'STAND'
                    if dealers_upcard in range(7, 11) or dealers_upcard == 'ACE':
                        return 'HIT'
                case 17:
                    return 'STAND'
                
                # TODO: This may not be correct?
                case 18:
                    return 'STAND'
                case 19:
                    return 'STAND'
                case 20:
                    return 'STAND'

        return None
    except KeyboardInterrupt:
        log.critical("Keyboard Interrupt!")

def process_card(card: str):
    """Converts string card to card object."""

    try:
        card_raw = list(card)

        card_suit = card_raw.pop()

        card_number = ''.join(card_raw)

        found_card_number = CardNumber.from_str(card_number)

        if found_card_number == None:
            log.error("Could not find card number from raw!")
            return None

        found_card_suit = CardSuit.from_str(card_suit)

        if found_card_suit == None:
            log.error("Could not find card suit from raw!")
            return None
        
        found_card = Card(found_card_number, found_card_suit)

        return found_card
    except KeyboardInterrupt:
        log.critical("Keyboard Interrupt!")

def bot_thread():
    """Main bot thread, contains the discord client."""
    
    try:
        client = SolverClient()
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        log.critical("Keyboard Interrupt!")

i = input(f"Token: {DISCORD_TOKEN}\nAre you sure this is your token? (Y/N): ")

match i:
    case "Y":
        pass
    case "N":
        print("Please change the constant in the file!")
        exit()
    case _:
        exit()

bthread = threading.Thread(target=bot_thread)

start_time = time.time()

bthread.start()

while True:
    try:
        os.system('cls')
        TIME_ELAPSED = round((time.time() - start_time))
        print(f"Time Elapsed: {TIME_ELAPSED} seconds\nBot Status: {STATUS}\nBot Log: {GAMES_LOG}")
        TIME_DELAY += 1
        time.sleep(1)
    except KeyboardInterrupt:
        exit()
