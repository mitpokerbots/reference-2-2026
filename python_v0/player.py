'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random

def get_card_rank(card):
    """Gets numeric rank of card (1-12)"""
    ranks = "23456789TJQKA" # order of ranks
    return ranks.index(card[0])

def get_card_suit(card):
    """Get suit of card"""
    return card[1].lower()

def eval_discard(my_cards, board_cards):
    """
    DiscardAction with the index of the card to discard
    
    my_cards: the 3 hole cards 
    board_cards: the current cards on the board
    """
    # check whether opponent already discarded
    opponent_discarded = (len(board_cards) == 3)
    my_ranks = [get_card_rank(c) for c in my_cards]

    # Pair Splitting Strategy
    counts = {r:my_ranks.count(r) for r in my_ranks}
    pair_rank = -1
    kicker_rank = -1
    for r,count in counts.items():
        if count == 2:
            pair_rank = r
        if count == 1:
            kicker_rank = r
    # if we have a pair AND a kicker
    if pair_rank != -1 and kicker_rank != -1:
        # If the kicker is much higher than the pair (e.g. 2,2,Ace)
        # better to toss one of the pairs to the board because maintain pair
        # and don't let opponent get high card
        if kicker_rank > pair_rank + 4: # THIS THRESHOLD CAN BE CHANGED
            for i, card in enumerate(my_cards):
                if get_card_rank(card) == pair_rank:
                    return DiscardAction(i)
                
    # Defensive Drop Evaluation
    scores = [0,0,0]

    for i in range(3):
        droppable_card = my_cards[i]
        # potential future board post drop
        future_board = board_cards + [droppable_card]
        f_ranks = [get_card_rank(c) for c in future_board]
        f_suits = [get_card_suit(c) for c in future_board]

        rank_val = get_card_rank(droppable_card)
        suit_val = get_card_suit(droppable_card)

        # Flush Danger
        # If the future board has 3+ of the same suit, we give everyone flush potential
        if f_suits.count(suit_val) >= 3:
            scores[i] += 100  # HIGH FLUSH POTENTIAL
        elif f_suits.count(suit_val) == 2:
            scores[i] += 20
        
        # Straight Danger
        sorted_ranks = sorted(list(set(f_ranks)))
        consecutive_count = 0
        for j in range(len(sorted_ranks)-1):
            if sorted_ranks[j+1] == sorted_ranks[j] + 1:
                consecutive_count += 1
            else:
                consecutive_count = 0
            if consecutive_count >= 2: # 3 cards in a row (e.g. 6,7,8)
                scores[i] += 50  # High chance of straight
        
        # High Card Danger
        scores[i] += rank_val * 1.5

        # Reacting to Opponent
        if opponent_discarded:
            opp_discard = board_cards[2]  # The 3rd card is theirs
            if get_card_rank(opp_discard) == rank_val:
                scores[i] += 25  # Do not add a pair
        # Randomization Factor
        scores[i] += random.uniform(0, 5)

    best_discard = scores.index(min(scores))
    return DiscardAction(best_discard)
        


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # the total number of seconds your bot has left to play this game
        game_clock = game_state.game_clock
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0,2,3,4,5,6 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        # opponent's cards or [] if not revealed
        opp_cards = previous_state.hands[1-active]
        pass

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        street = round_state.street
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.board  # the board cards
        # the number of chips you have contributed to the pot this round of betting
        my_pip = round_state.pips[active]
        # the number of chips your opponent has contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]
        # the number of chips you have remaining
        my_stack = round_state.stacks[active]
        # the number of chips your opponent has remaining
        opp_stack = round_state.stacks[1-active]
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        # the number of chips you have contributed to the pot
        my_contribution = STARTING_STACK - my_stack
        # the number of chips your opponent has contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack

        # Only use DiscardAction if it's in legal_actions (which already checks street)
        # use intelligent dropping strategy
        if DiscardAction in legal_actions:
            return eval_discard(my_cards, board_cards)
            
        strong_cards = "TJQKA"

        if RaiseAction in legal_actions:
            # the smallest and largest numbers of chips for a legal bet/raise
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise

            # if we have strong hole cards, let's raise a lot
            is_strong = True
            for card in my_cards: # Th
                if not (card[0] in strong_cards):
                    is_strong = False
                    break

            if is_strong:
                return RaiseAction(min(min_raise * 10, max_raise))
            
            else:
                if random.random() < 0.5:
                    return RaiseAction(min_raise)
                
        if CheckAction in legal_actions:  # check-call
            return CheckAction()
        if random.random() < 0.25:
            return FoldAction()
        return CallAction()


if __name__ == '__main__':
    run_bot(Player(), parse_args())
